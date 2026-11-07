#!/usr/bin/env python3
"""
每日头条抓取：知乎热榜 + 百度热搜 → 输出 headlines.json
热榜本质 = 当天全网点击/讨论最多的内容，作为「每日头条」数据源。
"""
import json
import urllib.request
from datetime import datetime, timezone, timedelta

BEIJING_TZ = timezone(timedelta(hours=8))
OUTPUT_FILE = "headlines.json"
REQUEST_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 每个来源取几条
TOP_PER_SOURCE = 10


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": REQUEST_UA})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_zhihu(n: int) -> list:
    """知乎热榜：有真实热度值、标题、摘要"""
    data = fetch_json("https://api.zhihu.com/topstory/hot-list?limit=50")
    items = []
    for it in data.get("data", [])[:n]:
        target = it.get("target", {})
        title = (target.get("title") or "").strip()
        url = target.get("url") or ""
        # api 链接转成人类可读链接
        url = url.replace("api.zhihu.com/questions/", "www.zhihu.com/question/")
        excerpt = (target.get("excerpt") or "").strip()
        heat = it.get("detail_text") or ""
        if not title:
            continue
        items.append({
            "rank": len(items) + 1,
            "title": title,
            "url": url,
            "heat": heat,
            "source": "知乎热榜",
            "summary": excerpt[:200],
        })
    return items


def fetch_baidu(n: int) -> list:
    """百度热搜：有排名、话题、搜索链接（热度为等级标记）"""
    data = fetch_json("https://top.baidu.com/api/board?platform=wise&tab=realtime")
    try:
        content = data["data"]["cards"][0]["content"][0]["content"]
    except (KeyError, IndexError, TypeError):
        return []
    items = []
    for it in content[:n]:
        word = (it.get("word") or "").strip()
        url = it.get("url") or ""
        hot_tag = it.get("hotTag") or ""
        if not word:
            continue
        # 热度等级 → 文本
        heat_map = {"3": "热", "2": "热", "1": "新", "0": ""}
        heat = heat_map.get(hot_tag, "")
        items.append({
            "rank": len(items) + 1,
            "title": word,
            "url": url,
            "heat": heat,
            "source": "百度热搜",
            "summary": "",
        })
    return items


def main():
    print(f"=== 每日头条抓取启动 === {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")

    headlines = []
    try:
        zhihu = fetch_zhihu(TOP_PER_SOURCE)
        headlines.extend(zhihu)
        print(f"[OK] 知乎热榜: {len(zhihu)} 条")
    except Exception as e:
        print(f"[FAIL] 知乎热榜: {e}")

    try:
        baidu = fetch_baidu(TOP_PER_SOURCE)
        headlines.extend(baidu)
        print(f"[OK] 百度热搜: {len(baidu)} 条")
    except Exception as e:
        print(f"[FAIL] 百度热搜: {e}")

    output = {
        "last_updated": datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(headlines),
        "headlines": headlines,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"=== 完成 === 共 {len(headlines)} 条，写入 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
