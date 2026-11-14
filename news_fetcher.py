#!/usr/bin/env python3
"""
新闻聚合器 - RSS 抓取、过滤、翻译、归并脚本
输出 news_data.json 供前端页面使用
"""

import feedparser
import json
import re
import hashlib
import sys
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

# ──────────────────────────────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────────────────────────────
BEIJING_TZ = timezone(timedelta(hours=8))
OUTPUT_FILE = "news_data.json"

# 是否启用翻译（英 -> 中）
ENABLE_TRANSLATION = True

# 每个源最多抓取篇数
MAX_PER_SOURCE = 20

# 请求 User-Agent（部分国内站点会拦截默认爬虫 UA，模拟浏览器更稳）
REQUEST_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# RSS 源（按分类）—— 国内源（仅保留实时更新）+ 国外源
# 注：人民网/新华网的 RSS 已停更（分别冻结于 2025-06 / 2022 年底），已移除；
# 国内军事媒体暂无可用实时 RSS，军事暂用国外国防源。
RSS_SOURCES = {
    "AI": [
        # ── 国内 ──
        {"name": "量子位",       "url": "https://www.qbitai.com/feed"},
        {"name": "InfoQ中文",    "url": "https://www.infoq.cn/feed"},
        {"name": "雷锋网",       "url": "https://www.leiphone.com/feed"},
        {"name": "IT之家",       "url": "https://www.ithome.com/rss/"},
        # ── 国外 ──
        {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/"},
        {"name": "OpenAI Blog",           "url": "https://openai.com/blog/rss.xml"},
        {"name": "TechCrunch AI",         "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    ],
    "军事": [
        # 国内军事媒体无可用实时 RSS，暂用国外国防源（均为实时更新）
        {"name": "Defense News",     "url": "https://www.defensenews.com/arc/outboundfeeds/rss/category/air/?outputType=xml"},
        {"name": "Breaking Defense", "url": "https://breakingdefense.com/feed/"},
        {"name": "Defense One",      "url": "https://www.defenseone.com/rss/all/"},
    ],
    "金融": [
        # ── 国内 ──
        {"name": "中国新闻网·财经", "url": "https://www.chinanews.com.cn/rss/finance.xml"},
        # ── 国外 ──
        {"name": "CNBC Markets",     "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html"},
        {"name": "MarketWatch",      "url": "https://feeds.marketwatch.com/marketwatch/topstories"},
        {"name": "Reuters Business", "url": "https://feeds.reuters.com/reuters/businessNews"},
    ],
    "时政": [
        # ── 国内 ──
        {"name": "中国新闻网",      "url": "https://www.chinanews.com.cn/rss/scroll-news.xml"},
        {"name": "中国新闻网·国际", "url": "https://www.chinanews.com.cn/rss/world.xml"},
        # ── 国外 ──
        {"name": "BBC News",     "url": "https://feeds.bbci.co.uk/news/rss.xml"},
        {"name": "Reuters World","url": "https://feeds.reuters.com/reuters/worldNews"},
        {"name": "NPR News",     "url": "https://feeds.npr.org/1001/rss.xml"},
    ],
}

# 广告/垃圾关键词过滤列表（不区分大小写）
AD_KEYWORDS = [
    # 英文
    "sponsored", "advertisement", "promoted", "buy now", "limited offer",
    "discount", "sale", "% off", "click here", "subscribe now",
    "paid post", "partner content", "affiliate", "free trial",
    "act now", "don't miss", "exclusive deal", "best price",
    "shopping", "coupon", "deal of the day", "clearance",
    # 中文
    "广告", "推广", "赞助", "招商", "优惠券", "限时抢购", "秒杀",
]

# ──────────────────────────────────────────────────────────────────────
# 翻译模块
# ──────────────────────────────────────────────────────────────────────
_translator = None

def _get_translator():
    """延迟初始化翻译器"""
    global _translator
    if _translator is None:
        try:
            from deep_translator import GoogleTranslator
            _translator = GoogleTranslator(source="en", target="zh-CN")
            print("[翻译] GoogleTranslator 就绪")
        except ImportError:
            print("[翻译] deep-translator 未安装，跳过翻译 (pip install deep-translator)")
            _translator = False
        except Exception as e:
            print(f"[翻译] 初始化失败: {e}")
            _translator = False
    return _translator if _translator is not False else None


def translate_text(text: str) -> str:
    """翻译文本（英 -> 中），失败返回原文"""
    if not text or not text.strip():
        return text

    translator = _get_translator()
    if translator is None:
        return text

    try:
        # 分段翻译，避免过长文本超时
        if len(text) > 1500:
            result = translator.translate(text[:1500])
        else:
            result = translator.translate(text)
        # 防止返回空字符串
        return result if result and result.strip() else text
    except Exception as e:
        # 静默失败，返回原文
        return text


def contains_cjk(text: str) -> bool:
    """判断文本是否包含中文字符（用于跳过已是中文的内容，避免被误翻译）"""
    return any('\u4e00' <= c <= '\u9fff' for c in (text or ""))


def translate_articles(articles: list) -> list:
    """批量翻译文章标题和摘要（只翻译纯英文内容，中文源直接跳过）"""
    translator = _get_translator()
    if translator is None:
        return articles

    total = len(articles)
    print(f"\n[翻译] 开始翻译 {total} 篇文章...")

    for i, a in enumerate(articles):
        title = a.get("title", "")
        summary = a.get("summary", "")

        # 仅当标题不含中文时才翻译。中文源标题常混有英文词（如 "AI"、"GPT-5"），
        # 用「是否含中文」判断比「是否含 ASCII」更可靠，避免把中文句子误送英译中。
        if title and not contains_cjk(title):
            zh_title = translate_text(title)
            if zh_title and zh_title != title:
                a["title_cn"] = zh_title

        if summary and not contains_cjk(summary):
            zh_summary = translate_text(summary)
            if zh_summary and zh_summary != summary:
                a["summary_cn"] = zh_summary

        # 速率限制：避免被 Google 封 IP
        if i > 0 and i % 10 == 0:
            time.sleep(1)
            print(f"  进度: {i}/{total}")

    print(f"  完成: {total}/{total}")
    return articles


# ──────────────────────────────────────────────────────────────────────
# RSS 抓取模块
# ──────────────────────────────────────────────────────────────────────

def is_advertisement(title: str, summary: str) -> bool:
    """检查是否为广告"""
    text = f"{title} {summary}".lower()
    for kw in AD_KEYWORDS:
        if kw in text:
            return True
    return False


def parse_date(entry) -> str:
    """尝试多种方式解析发布时间，返回 ISO 格式字符串"""
    for attr in ("published_parsed", "updated_parsed"):
        tp = getattr(entry, attr, None)
        if tp:
            try:
                dt = datetime(*tp[:6], tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass

    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(raw)
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pass

    return None  # 无有效日期：返回 None，由调用方跳过，避免把停更/过期内容当成"今日新闻"


def extract_source_name(source_url: str, source_name: str) -> str:
    """提取来源名字"""
    if source_name:
        return source_name
    domain = urlparse(source_url).netloc
    domain = re.sub(r"^(www\d?|feeds?\d?)\.", "", domain)
    return domain.split(".")[0].capitalize()


def deduplicate(articles: list) -> list:
    """基于标题相似度去重"""
    seen = set()
    result = []
    for a in articles:
        sig = hashlib.md5(a["title"].strip().lower()[:80].encode()).hexdigest()
        if sig not in seen:
            seen.add(sig)
            result.append(a)
    return result


def fetch_category(category: str, sources: list) -> list:
    """抓取一个分类下所有源的文章"""
    articles = []
    for src in sources:
        name = src["name"]
        url = src["url"]
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": REQUEST_UA})
            if feed.bozo and not feed.entries:
                print(f"  [WARN] {name}: parse error, skipping")
                continue

            count = 0
            for entry in feed.entries[:MAX_PER_SOURCE]:
                title = getattr(entry, "title", "").strip()
                summary = getattr(entry, "summary", "").strip()
                summary = re.sub(r"<[^>]+>", "", summary)[:300]

                if not title:
                    continue
                if is_advertisement(title, summary):
                    continue

                link = getattr(entry, "link", "")

                published = parse_date(entry)
                if not published:
                    continue  # 跳过无日期条目，防止停更源/过期内容冒充今日新闻

                articles.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": published,
                    "source": extract_source_name(link, name),
                    "category": category,
                })
                count += 1

            print(f"  [OK] {name}: {count} articles")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")

    return articles


# ──────────────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────────────

def main():
    print(f"=== 新闻聚合器启动 === "
          f"{datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')} (Beijing)")

    all_articles = []
    for category, sources in RSS_SOURCES.items():
        print(f"\n[分类] {category}")
        articles = fetch_category(category, sources)
        all_articles.extend(articles)
        print(f"  合计: {len(articles)} 篇")

    # 去重
    before = len(all_articles)
    all_articles = deduplicate(all_articles)
    after = len(all_articles)
    print(f"\n去重: {before} -> {after} (移除 {before - after} 篇重复)")

    # 翻译（可选）
    if ENABLE_TRANSLATION:
        all_articles = translate_articles(all_articles)

    # 按发布时间倒序
    all_articles.sort(key=lambda x: x.get("published", ""), reverse=True)

    output = {
        "last_updated": datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(all_articles),
        "articles": all_articles,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n=== 完成 === 共 {len(all_articles)} 篇，写入 {OUTPUT_FILE}")
    for cat in RSS_SOURCES:
        cat_count = sum(1 for a in all_articles if a["category"] == cat)
        print(f"  {cat}: {cat_count}")


if __name__ == "__main__":
    main()
