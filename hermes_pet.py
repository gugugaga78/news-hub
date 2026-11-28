#!/usr/bin/env python3
"""
Hermes 赛博少女 — Cyber Companion v3.0
┌─────────────────────────────────────────────┐
│  半身少女形象 · 霓虹长发 · 智能面板 · 项目监控  │
└─────────────────────────────────────────────┘
"""

import tkinter as tk
import random
import math
import json
import os
from datetime import datetime

# ═══════════════════════════════════════════
# 配色
# ═══════════════════════════════════════════
CLR = {
    "bg":       "#010101",
    "skin":     "#1a1a2e",
    "skin_lit": "#2a2a4e",
    "eye":      "#00e5ff",
    "eye_glow":   "#80f0ff",
    "cyan_glow":  "#80f0ff",
    "pink_dim":   "#801050",
    "pink_glow":  "#ff80c0",
    "hair_1":   "#ff2d95",
    "hair_2":   "#b347ea",
    "hair_3":   "#00d4ff",
    "suit":     "#0d1117",
    "suit_lit": "#1a1040",
    "cyan":     "#00e5ff",
    "pink":     "#ff2d95",
    "purple":   "#b347ea",
    "gold":     "#ffd740",
    "white":    "#e8eaed",
    "dim":      "#5f6368",
    "panel_bg": "#0d0d20",
    "panel_border": "#00d4ff",
}

# ═══════════════════════════════════════════
# 对话库
# ═══════════════════════════════════════════
QUOTES = [
    "今天过得怎么样？✨", "我在帮你盯着项目呢～", "需要我做什么吗？",
    "你写的代码真棒！", "喝点水吧，别太累了 💧", "我一直在哦～",
    "赛博世界真美好 🌃", "呼…好安静", "有什么新想法吗？",
    "我来守护你的桌面！", "嗯？你在看我？", "⚡ 能量充足！",
    "晚安…才怪，我不用睡觉", "今天天气不错吧？", "嘿！别戳我 >_<",
    "叮！你的代码编译通过了（大概）", "我在学习新东西呢 📚",
]


class CyberGirl:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Hermes - Cyber Companion")
        self.W = 300
        self.H = 420
        self.root.geometry(f"{self.W}x{self.H}+"
            f"{self.root.winfo_screenwidth() - 340}+"
            f"{self.root.winfo_screenheight() // 3 - 50}")

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", CLR["bg"])
        self.root.configure(bg=CLR["bg"])

        self.cv = tk.Canvas(self.root, width=self.W, height=self.H,
                            bg=CLR["bg"], highlightthickness=0, bd=0)
        self.cv.pack()

        # 状态
        self.t = 0.0
        self.mouse_near = False
        self.show_panel = True
        self.drag = {"x": 0, "y": 0}
        self._was_drag = False
        self.blink = 0.0
        self.next_blink = random.uniform(3, 6)
        self.blink_cd = 0

        # 粒子
        self.particles = [self._new_particle() for _ in range(25)]

        # 面板数据
        self.panel_mode = 0  # 0=项目, 1=系统, 2=时间
        self.project_status = "空闲"
        self.last_news_update = "未知"

        # 气泡
        self.bubble = []

        # 绑定
        self.cv.bind("<ButtonPress-1>",   self._press)
        self.cv.bind("<B1-Motion>",       self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)
        self.cv.bind("<Enter>", lambda e: setattr(self, "mouse_near", True))
        self.cv.bind("<Leave>", lambda e: setattr(self, "mouse_near", False))
        self.cv.bind("<Double-Button-1>", lambda e: self._cycle_panel())
        self.cv.bind("<Button-3>", lambda e: self.root.destroy())

        # 定时刷新项目状态
        self._refresh_project()
        self._loop()

    # ── 粒子 ──
    def _new_particle(self):
        return {
            "x": random.uniform(40, self.W - 40),
            "y": random.uniform(40, self.H - 80),
            "r": random.uniform(0.8, 2.5),
            "vx": random.uniform(-0.3, 0.3),
            "vy": random.uniform(-0.6, -0.1),
            "life": random.uniform(1, 3),
            "max_life": random.uniform(1, 3),
            "c": random.choice([CLR["cyan"], CLR["pink"], CLR["purple"], CLR["gold"]]),
        }

    # ── 项目状态 ──
    def _refresh_project(self):
        """检查新闻站项目状态"""
        news_path = os.path.join(os.path.dirname(__file__), "news_data.json")
        if os.path.exists(news_path):
            try:
                with open(news_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.last_news_update = data.get("last_updated", "未知")[:16]
                total = data.get("total", 0)
                self.project_status = f"新闻站在线 · {total}篇"
            except:
                self.project_status = "数据读取失败"
                self.last_news_update = "--"
        else:
            self.project_status = "未找到项目"
            self.last_news_update = "--"

        self.root.after(30000, self._refresh_project)  # 30s 刷新

    def _cycle_panel(self):
        self.panel_mode = (self.panel_mode + 1) % 3

    # ── 交互 ──
    def _press(self, e):
        self.drag["x"] = e.x
        self.drag["y"] = e.y
        self._was_drag = False

    def _drag(self, e):
        self._was_drag = True
        self.root.geometry(f"+{self.root.winfo_x()+e.x-self.drag['x']}"
                           f"+{self.root.winfo_y()+e.y-self.drag['y']}")

    def _release(self, e):
        if not self._was_drag:
            self._say()

    def _say(self):
        for i in self.bubble:
            self.cv.delete(i)
        self.bubble = []

        text = random.choice(QUOTES)
        bx, by = self.W // 2 + 80, 55

        # 分行
        lines = []
        if len(text) > 12:
            mid = len(text) // 2
            for sep in ["～", "！", "？", "。", "，", " ", "✨"]:
                idx = text.rfind(sep, 0, mid + 6)
                if idx > 5:
                    mid = idx + 1
                    break
            lines = [text[:mid].strip(), text[mid:].strip()]
        else:
            lines = [text]

        lh = 18
        bw = 145
        bh = len(lines) * lh + 14

        bg = self.cv.create_rectangle(
            bx - bw // 2, by - bh // 2, bx + bw // 2, by + bh // 2,
            fill=CLR["panel_bg"], outline=CLR["cyan"], width=1.5
        )
        self.bubble.append(bg)
        for i, ln in enumerate(lines):
            t = self.cv.create_text(bx, by - (len(lines) - 1) * lh // 2 + i * lh,
                                    text=ln, fill=CLR["cyan"],
                                    font=("Microsoft YaHei", 9, "bold"))
            self.bubble.append(t)
        self.root.after(4000, lambda: [self.cv.delete(i) for i in self.bubble])

    # ═══════════════════════════════════════════
    #  绘制 — 赛博少女
    # ═══════════════════════════════════════════

    def _oval(self, x1, y1, x2, y2, **kw):
        return self.cv.create_oval(x1, y1, x2, y2, **kw)

    def _line(self, x1, y1, x2, y2, **kw):
        return self.cv.create_line(x1, y1, x2, y2, **kw)

    def _poly(self, pts, **kw):
        return self.cv.create_polygon(*pts, **kw)

    def _arc(self, *a, **kw):
        return self.cv.create_arc(*a, **kw)

    def _txt(self, x, y, text, **kw):
        return self.cv.create_text(x, y, text=text, **kw)

    def _glow_circle(self, x, y, r, color, alpha=0.15):
        """多层光晕"""
        for i in range(int(r * 2), int(r * 0.3), -3):
            self._oval(x - i, y - i, x + i, y + i,
                       fill="", outline=color, width=0.5)

    def draw(self):
        self.cv.delete("all")
        t = self.t
        cx = self.W // 2
        cy = self.H // 2 - 15
        float_y = math.sin(t * 1.1) * 4

        # ── 粒子 ──
        for p in self.particles:
            a = max(0, p["life"] / p["max_life"])
            gr = p["r"] * (0.5 + 0.5 * a)
            self._oval(p["x"] - gr * 4, p["y"] - gr * 4,
                       p["x"] + gr * 4, p["y"] + gr * 4,
                       fill="", outline=p["c"], width=0.4)
            self._oval(p["x"] - gr, p["y"] - gr,
                       p["x"] + gr, p["y"] + gr,
                       fill=p["c"], outline="")

        # ── 光环 ──
        halo_r = 90
        halo_y = cy + float_y - 130
        for i in range(3):
            ang = t * 0.5 + i * 2.09
            self._arc(cx - halo_r, halo_y - halo_r,
                      cx + halo_r, halo_y + halo_r,
                      start=math.degrees(ang) % 360, extent=55,
                      style="arc", outline=[CLR["cyan"], CLR["purple"], CLR["pink"]][i], width=1.5)

        # ════════════════════ 长发 ════════════════════
        hair_top = cy + float_y - 130
        hair_len = 140
        hair_width = 36
        strands = 11

        # 每根发丝 — 贝塞尔模拟（多段折线）
        for s in range(strands):
            # 发色渐变
            ratio = s / (strands - 1)
            if ratio < 0.33:
                hclr = CLR["hair_1"]
            elif ratio < 0.66:
                hclr = CLR["hair_2"]
            else:
                hclr = CLR["hair_3"]

            base_x = cx - hair_width + s * (hair_width * 2) / (strands - 1)
            # 飘逸
            wave = math.sin(t * 2.5 + s * 0.7) * 8 + math.sin(t * 1.3 + s) * 5
            wave2 = math.sin(t * 1.8 + s * 1.2) * 6
            pts = []
            segs = 15
            for j in range(segs + 1):
                prog = j / segs
                px = base_x + wave * prog + wave2 * prog * 0.7
                py = hair_top + prog * hair_len
                # 发丝向中间收拢
                mid_factor = 1 - abs(s - strands // 2) / (strands // 2) * 0.6
                px += (cx - px) * (1 - mid_factor) * prog * 0.5
                pts.extend([px, py])
            if len(pts) >= 4:
                self._line(pts[0], pts[1], pts[2], pts[3],
                           fill=hclr, width=1.8)
                for j in range(1, len(pts) // 2 - 1):
                    self._line(pts[j * 2], pts[j * 2 + 1],
                               pts[(j + 1) * 2], pts[(j + 1) * 2 + 1],
                               fill=hclr, width=max(0.6, 2 - ratio * 1.5))

        # ════════════════════ 头部 ════════════════════
        head_cx = cx
        head_cy = cy + float_y - 85
        head_r = 32

        # 头部光晕
        self._glow_circle(head_cx, head_cy, head_r + 8, CLR["pink"])

        # 脸
        self._oval(head_cx - head_r, head_cy - head_r,
                   head_cx + head_r, head_cy + head_r,
                   fill=CLR["skin"], outline=CLR["pink"], width=2)

        # 脸部高光
        self._oval(head_cx - head_r + 10, head_cy - head_r + 8,
                   head_cx + head_r - 10, head_cy + head_r - 8,
                   fill="", outline=CLR["skin_lit"], width=1)

        # ════════════════════ 眼睛 ════════════════════
        eye_y = head_cy - 5
        eye_sp = 13
        ew, eh = 15, 16
        eye_c = CLR["eye_glow"] if self.mouse_near else CLR["eye"]
        blink_h = 1.0
        if self.blink > 0:
            if self.blink < 0.5:
                blink_h = 1 - self.blink * 2
            else:
                blink_h = (self.blink - 0.5) * 2
            blink_h = max(0.03, blink_h)

        for side in [-1, 1]:
            ex = head_cx + side * eye_sp
            eh_cur = eh * blink_h
            # 眼白
            self._oval(ex - ew // 2, eye_y - eh_cur // 2,
                       ex + ew // 2, eye_y + eh_cur // 2,
                       fill="#0a1628", outline=eye_c, width=2.5)
            if blink_h > 0.2:
                # 瞳孔
                ps = 6
                self._oval(ex - ps // 2, eye_y - ps // 2,
                           ex + ps // 2, eye_y + ps // 2,
                           fill=eye_c, outline="")
                # 高光 1
                self._oval(ex - 5, eye_y - 7, ex - 1, eye_y - 3,
                           fill=CLR["white"], outline="")
                # 高光 2 (小)
                self._oval(ex + 3, eye_y + 2, ex + 5, eye_y + 4,
                           fill=CLR["white"], outline="")

        # ════════════════════ 嘴 ════════════════════
        mouth_y = eye_y + 16
        self._arc(head_cx - 5, mouth_y - 2, head_cx + 5, mouth_y + 5,
                  start=0, extent=-180, style="arc",
                  outline=CLR["pink"], width=1.5)

        # 腮红 — 左右两个粉色椭圆
        for side in [-1, 1]:
            self._oval(head_cx + side * 20 - 7, mouth_y - 5,
                       head_cx + side * 20 + 7, mouth_y + 7,
                       fill="", outline=CLR["pink_dim"] if "pink_dim" in CLR else "#801050", width=0.8)

        # ════════════════════ 赛博眼罩/发饰 ════════════════════
        visor_y = head_cy - 18
        visor_w = 48
        self._line(head_cx - visor_w // 2, visor_y,
                   head_cx + visor_w // 2, visor_y,
                   fill=CLR["cyan"], width=2)
        # 两侧装饰
        for side in [-1, 1]:
            self._poly([
                head_cx + side * visor_w // 2, visor_y,
                head_cx + side * (visor_w // 2 + 8), visor_y - 5,
                head_cx + side * (visor_w // 2 + 5), visor_y + 3,
            ], fill=CLR["cyan"], outline="")

        # ════════════════════ 身体 ════════════════════
        body_top = head_cy + head_r + 5
        body_w, body_h = 50, 75

        # 颈
        self._line(head_cx - 8, body_top, head_cx + 8, body_top,
                   fill=CLR["purple"], width=3)

        # 躯干
        self._poly([
            head_cx - body_w // 2, body_top + 5,
            head_cx - body_w // 2 + 8, body_top + body_h,
            head_cx + body_w // 2 - 8, body_top + body_h,
            head_cx + body_w // 2, body_top + 5,
        ], fill=CLR["suit"], outline=CLR["purple"], width=2)

        # 身体霓虹纹路 — 中央竖线
        core_y = body_top + 15
        self._line(head_cx, core_y, head_cx, core_y + 35,
                   fill=CLR["cyan"], width=1.5)
        # 菱形核心
        d = 10
        self._poly([
            head_cx, core_y + 10 - d,
            head_cx - d, core_y + 10,
            head_cx, core_y + 10 + d,
            head_cx + d, core_y + 10,
        ], fill=CLR["cyan"], outline=CLR["cyan_glow"], width=1)
        # 脉冲光
        pulse = abs(math.sin(t * 3)) * 5
        self._oval(head_cx - d - pulse, core_y + 10 - d - pulse,
                   head_cx + d + pulse, core_y + 10 + d + pulse,
                   fill="", outline=CLR["cyan"], width=0.8)

        # 身体侧边霓虹线
        for side in [-1, 1]:
            sx = head_cx + side * (body_w // 2 - 5)
            self._line(sx, body_top + 10, sx, body_top + body_h - 10,
                       fill=CLR["pink"], width=0.8)

        # 肩部装饰
        for side in [-1, 1]:
            sx = head_cx + side * (body_w // 2 + 12)
            sy = body_top + 8
            self._oval(sx - 8, sy - 4, sx + 8, sy + 10,
                       fill=CLR["suit_lit"], outline=CLR["cyan"], width=1.5)
            self._oval(sx - 3, sy + 1, sx + 3, sy + 7,
                       fill=CLR["cyan"], outline="")

        # ════════════════════ 手臂 ════════════════════
        arm_top = body_top + 15
        for side in [-1, 1]:
            ax = head_cx + side * (body_w // 2 + 10)
            arm_pts = [
                ax, arm_top,
                ax + side * 15, arm_top + 40,
                ax + side * 10, arm_top + 50,
                ax - side * 2, arm_top + 15,
            ]
            self._poly(arm_pts, fill=CLR["suit"], outline=CLR["purple"], width=1.5)
            # 手臂霓虹线
            self._line(ax + side * 3, arm_top + 5,
                       ax + side * 8, arm_top + 35,
                       fill=CLR["pink"], width=1)

        # ════════════════════ 信息面板 ════════════════════
        if self.show_panel:
            px = cx
            py = body_top + body_h + 35
            pw, ph = 180, 75

            # 面板背景
            self._poly([
                px - pw // 2, py - ph // 2,
                px + pw // 2, py - ph // 2,
                px + pw // 2 - 5, py + ph // 2,
                px - pw // 2 + 5, py + ph // 2,
            ], fill=CLR["panel_bg"], outline=CLR["panel_border"], width=1.5)

            # 标题栏
            self._line(px - pw // 2 + 5, py - ph // 2 + 16,
                       px + pw // 2 - 5, py - ph // 2 + 16,
                       fill=CLR["panel_border"], width=0.8)

            titles = ["📡 项目监控", "💻 系统状态", "🕐 时间"]
            self._txt(px, py - ph // 2 + 8, titles[self.panel_mode],
                      fill=CLR["cyan"], font=("Microsoft YaHei", 10, "bold"))

            if self.panel_mode == 0:
                # 项目监控
                self._txt(px, py - 5, f"状态: {self.project_status}",
                          fill=CLR["white"], font=("Microsoft YaHei", 8))
                self._txt(px, py + 12, f"新闻更新: {self.last_news_update}",
                          fill=CLR["dim"], font=("Microsoft YaHei", 8))
            elif self.panel_mode == 1:
                # 系统
                import platform
                self._txt(px, py - 5, f"系统: {platform.system()} {platform.release()}",
                          fill=CLR["white"], font=("Microsoft YaHei", 8))
                self._txt(px, py + 12, f"Python: {platform.python_version()}",
                          fill=CLR["dim"], font=("Microsoft YaHei", 8))
            else:
                # 时间
                now = datetime.now()
                self._txt(px, py - 8, now.strftime("%Y-%m-%d"),
                          fill=CLR["white"], font=("Consolas", 12, "bold"))
                self._txt(px, py + 10, now.strftime("%H:%M:%S"),
                          fill=CLR["cyan"], font=("Consolas", 14, "bold"))

            # 底部提示
            self._txt(px, py + ph // 2 - 10, "双击切换 | 右键关闭 | 拖拽移动",
                      fill=CLR["dim"], font=("Microsoft YaHei", 7))

    # ═══════════════════════════════════════════
    #  主循环
    # ═══════════════════════════════════════════
    def _loop(self):
        dt = 0.033
        self.t += dt

        # 眨眼
        self.blink_cd += dt
        if self.blink_cd >= self.next_blink:
            self.blink = 0.01
            self.blink_cd = 0
            self.next_blink = random.uniform(2, 6)
        if self.blink > 0:
            self.blink += dt * 6
            if self.blink >= 1:
                self.blink = 0

        # 粒子
        for p in self.particles:
            p["x"] += p["vx"] + math.sin(self.t + p.get("ph", 0)) * 0.15
            p["y"] += p["vy"]
            p["life"] -= dt
            if p["life"] <= 0:
                p.update(self._new_particle())

        self.draw()
        self.root.after(33, self._loop)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    CyberGirl().run()
