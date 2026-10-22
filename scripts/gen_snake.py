#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""整屏点阵蛇：把 W / A / O 画在 24px 网格上铺满视口，
生成「静态点阵 path + 沿字形游走的电流光点」，注入 index.html。

设计要点：
  · 网格 24px，与 body 背景点阵同密度 —— 字母看起来就是背景小点被点亮的那部分；
  · 字母用骨架折线 + Bresenham 栅格化（斜边天然是 45°／缓斜阶梯，正好是 PCB 味）；
  · 静态点合成一条 path 描边（零长度线段 + 圆线帽），305 个点只占一个节点；
  · 电流不用「逐点点亮 300 个元素」，而是每段 1 个光点 +
    offset-path + steps() 逐格跳动 —— 全页只有 5 个动画元素，不拖帧；
  · 各段独立循环、各自错开相位，所以不需要跨字母瞬移。

可重复运行：只替换 <!-- SNAKE:BEGIN --> … <!-- SNAKE:END --> 之间的内容。
"""
import math
import re
import pathlib

GRID = 24                 # 与背景点阵一致
COLS, ROWS = 120, 70      # 画布格数（2880×1680，盖住 2560×1440）
LW, LH = 25, 35           # 每个字母的格宽／格高
GAP = 2                   # 字母间距（格）
OX, OY = 14, 12           # W 左上角
STEP = 0.12               # 每跳一格的时长（秒）；0.12 ≈ 每秒 8 格，慢到不抢视线


def bres(x0, y0, x1, y1):
    """Bresenham，返回含端点的整数格点序列。"""
    pts, dx, dy = [], abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def dedupe(seq):
    out = []
    for p in seq:
        if not out or out[-1] != p:
            out.append(p)
    return out


def polyline(verts):
    """把若干顶点连成一条连续点列。"""
    pts = []
    for a, b in zip(verts, verts[1:]):
        seg = bres(*a, *b)
        pts.extend(seg if not pts else seg[1:])
    return dedupe(pts)


def ellipse_ring(cx, cy, rx, ry, spacing=1.0):
    """椭圆环：按弧长等距取样再取整 —— 间距均匀，steps() 跳格才能落在点上。"""
    n = 4000
    raw = [(cx + rx * math.cos(2 * math.pi * i / n),
            cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
    cum = [0.0]
    for a, b in zip(raw, raw[1:]):
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = cum[-1] + math.hypot(raw[0][0] - raw[-1][0], raw[0][1] - raw[-1][1])

    pts, j, d = [], 0, 0.0
    while d < total and j + 1 < len(cum):
        while j + 1 < len(cum) and cum[j + 1] < d:
            j += 1
        span = cum[j + 1] - cum[j]
        t = 0 if span <= 1e-9 else (d - cum[j]) / span
        pts.append((round(raw[j][0] + (raw[j + 1][0] - raw[j][0]) * t),
                    round(raw[j][1] + (raw[j + 1][1] - raw[j][1]) * t)))
        d += spacing
    return dedupe(pts)


def shift(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def build():
    # --- 三段字形，局部坐标 0..LW-1 / 0..LH-1 ---
    w = polyline([(1, 0), (6, LH - 1), (12, 10), (18, LH - 1), (23, 0)])

    a_segs = [
        bres(1, LH - 1, 12, 1),      # 左斜：底 → 顶
        bres(12, 1, 23, LH - 1),     # 右斜：顶 → 底
        bres(4, 24, 20, 24),         # 横杠：两端都落在斜线上
    ]

    o = ellipse_ring(12, LH / 2, 11, 16)

    # --- 平移到整屏坐标 ---
    segs = []
    segs.append(("W", shift(w, OX, OY)))
    ax = OX + LW + GAP
    for s in a_segs:
        segs.append(("A", shift(s, ax, OY)))
    ox = ax + LW + GAP
    segs.append(("O", shift(o, ox, OY)))

    # --- 静态点：合并去重，一条 path 画完（M + h0 零长度线段 + 圆帽 = 圆点）---
    seen, cells = set(), []
    for _, seg in segs:
        for p in seg:
            if p not in seen:
                seen.add(p)
                cells.append(p)
    d = "M" + "M".join(f"{x} {y}h0" for x, y in cells)

    # --- 电流光点：每段一条路径，坐标换成视口 px（点阵原点在 12,12）---
    sparks = []
    for i, (_, seg) in enumerate(segs):
        if len(seg) < 3:
            continue
        px = [(x * GRID + GRID / 2, y * GRID + GRID / 2) for x, y in seg]
        path = "M" + "L".join(f"{x:g} {y:g}" for x, y in px)
        n = len(seg) - 1
        dur = n * STEP
        delay = -(i % 5) * STEP * 7      # 段间错开相位，像多股电流各走各的
        sparks.append(
            f'<i class="snake__spark" style="offset-path:path(\'{path}\');'
            f'animation:snake-walk {dur:.2f}s steps({n},end) {delay:.2f}s infinite">'
            f"</i>"
        )

    html = (
        '<div class="snake" aria-hidden="true">'
        f'<svg class="snake__grid" viewBox="0 0 {COLS} {ROWS}">'
        f'<path class="snake__dots" d="{d}"/></svg>'
        + "".join(sparks)
        + "</div>"
    )
    return html, len(cells), len(sparks), sum(len(s) for _, s in segs)


def main():
    block, n_dots, n_spark, n_steps = build()
    path = pathlib.Path(__file__).resolve().parent.parent / "index.html"
    html = path.read_text(encoding="utf-8")

    pat = re.compile(r"<!-- SNAKE:BEGIN.*?<!-- SNAKE:END -->", re.S)
    if not pat.search(html):
        raise SystemExit("index.html 里找不到 <!-- SNAKE:BEGIN --> 标记")

    html = pat.sub(
        "<!-- SNAKE:BEGIN 由 scripts/gen_snake.py 生成，勿手改 -->\n"
        + block
        + "\n<!-- SNAKE:END -->",
        html,
    )
    path.write_text(html, encoding="utf-8")
    print(f"静态点 {n_dots} 个（合并后）｜游走步 {n_steps} ｜光点 {n_spark} 个")


if __name__ == "__main__":
    main()
