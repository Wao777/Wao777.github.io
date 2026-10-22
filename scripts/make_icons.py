r"""生成站点图标：favicon.svg / favicon.ico / apple-touch-icon.png

图形复刻自导航栏 `.brand__mark`（assets/css/main.css）：
  蓝块 #1B4DFF，22x22、圆角 6
  橙块 #FF4D2E，由 box-shadow "8px 8px 0 -3px" 得来 —— 尺寸 22-2*3=16、
       相对位移 +8、圆角 6-3=3，且位于蓝块下层（只露出右下角）

画布按 32 单位网格：橙块 (12,12,16,16)，蓝块 (4,4,22,22)，整体居中。

用法（Pillow 在 default venv 里）：
  %USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe scripts\make_icons.py
"""

import os

from PIL import Image, ImageDraw

BLUE = (27, 77, 255, 255)
ORANGE = (255, 77, 46, 255)
PAPER = (246, 244, 239, 255)  # --bg，仅用于 iOS 满铺底

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "assets", "img"))

SS = 8  # 超采样倍数


def draw_mark(size, bg=None):
    """按 32 单位网格画标记；bg 为 None 时透明底。"""
    s = size * SS
    img = Image.new("RGBA", (s, s), bg if bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = s / 32.0

    # 顺序要紧：橙块在下，蓝块盖上去
    d.rounded_rectangle(
        [12 * u, 12 * u, 28 * u - 1, 28 * u - 1], radius=3 * u, fill=ORANGE
    )
    d.rounded_rectangle(
        [4 * u, 4 * u, 26 * u - 1, 26 * u - 1], radius=6 * u, fill=BLUE
    )
    return img.resize((size, size), Image.LANCZOS)


SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect x="12" y="12" width="16" height="16" rx="3" fill="#FF4D2E"/>
  <rect x="4" y="4" width="22" height="22" rx="6" fill="#1B4DFF"/>
</svg>
"""


def main():
    os.makedirs(OUT, exist_ok=True)

    with open(os.path.join(OUT, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(SVG)

    # ICO：一次塞进 16/32/48 三个尺寸，透明底
    draw_mark(48).save(
        os.path.join(OUT, "favicon.ico"),
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )

    # iOS 主屏：满铺米白底（系统自己切圆角，不能留透明）
    draw_mark(180, bg=PAPER).convert("RGB").save(
        os.path.join(OUT, "apple-touch-icon.png"), format="PNG", optimize=True
    )

    for name in ("favicon.svg", "favicon.ico", "apple-touch-icon.png"):
        p = os.path.join(OUT, name)
        print(f"{name}  {os.path.getsize(p)} bytes")


if __name__ == "__main__":
    main()
