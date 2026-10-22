"""给全站页面注入 canonical / og:* / 图标链接。

幂等：已存在 canonical 的页面会跳过重复注入（图标行始终按规范重写）。
不处理 reports/latest.html —— 那份由 n8n 每天覆盖，模板在 n8n 侧。

用法：
  python scripts/inject_meta.py          # 写入
  python scripts/inject_meta.py --dry    # 只看会改什么
"""

import os
import re
import sys

ORIGIN = "https://wao777.top"

# (文件, 规范地址, 相对根前缀)。规范地址为 None → 只处理图标（404 页）
PAGES = [
    ("index.html", f"{ORIGIN}/", "./"),
    ("404.html", None, "./"),
    ("works/content-hub/index.html", f"{ORIGIN}/works/content-hub/", "../../"),
    ("works/daily-pipeline/index.html", f"{ORIGIN}/works/daily-pipeline/", "../../"),
    ("works/display-doctor/index.html", f"{ORIGIN}/works/display-doctor/", "../../"),
    ("works/eye-care/index.html", f"{ORIGIN}/works/eye-care/", "../../"),
    ("works/net-doctor/index.html", f"{ORIGIN}/works/net-doctor/", "../../"),
    ("works/qingcheng/index.html", f"{ORIGIN}/works/qingcheng/", "../../"),
    ("works/zt-popup/index.html", f"{ORIGIN}/works/zt-popup/", "../../"),
]

ICON_BLOCK = (
    '<link rel="icon" href="{p}assets/img/favicon.svg" type="image/svg+xml">\n'
    '<link rel="icon" href="{p}assets/img/favicon.ico" sizes="32x32">\n'
    '<link rel="apple-touch-icon" href="{p}assets/img/apple-touch-icon.png">'
)

DATA_URI_ICON = re.compile(r'^<link rel="icon" href="data:image/svg\+xml,[^\n]*$', re.M)


def collect(html, pattern):
    m = re.search(pattern, html)
    return m.group(1).strip() if m else None


def build_block(html, canon, nl):
    """拼出要插到 </head> 前的那几行。"""
    lines = []

    if canon:
        if "<link rel=\"canonical\"" not in html:
            lines.append(f'<link rel="canonical" href="{canon}">')
        if 'property="og:url"' not in html:
            lines.append(f'<meta property="og:url" content="{canon}">')
        if 'property="og:site_name"' not in html:
            lines.append('<meta property="og:site_name" content="Wao 的个人站点">')
        if 'property="og:locale"' not in html:
            lines.append('<meta property="og:locale" content="zh_CN">')

        title = collect(html, r"<title>(.*?)</title>")
        desc = collect(html, r'<meta name="description" content="(.*?)">')

        if 'property="og:type"' not in html:
            lines.append('<meta property="og:type" content="article">')
        if title and 'property="og:title"' not in html:
            lines.append(f'<meta property="og:title" content="{title}">')
        if desc and 'property="og:description"' not in html:
            lines.append(f'<meta property="og:description" content="{desc}">')
        if 'name="twitter:card"' not in html:
            lines.append('<meta name="twitter:card" content="summary">')

    if not lines:
        return None
    return nl.join(lines)


def process(rel, canon, prefix, dry=False):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", rel)
    path = os.path.normpath(path)

    with open(path, "r", encoding="utf-8", newline="") as f:
        html = f.read()

    nl = "\r\n" if "\r\n" in html else "\n"
    before = html

    # 1) 图标：把内联 data URI 换成独立文件（没有就补在 </head> 前）
    icons = ICON_BLOCK.format(p=prefix).replace("\n", nl)
    if DATA_URI_ICON.search(html):
        html = DATA_URI_ICON.sub(icons, html, count=1)
    elif "apple-touch-icon" not in html and "</head>" in html:
        html = html.replace("</head>", icons + nl + "</head>", 1)

    # 2) 元信息，插在 </head> 之前
    block = build_block(html, canon, nl)
    if block:
        html = html.replace("</head>", block + nl + "</head>", 1)

    changed = html != before
    if changed and not dry:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(html)
    print(f"{'[改]' if changed else '[跳过]'} {rel}")
    return changed


def main():
    dry = "--dry" in sys.argv
    n = sum(process(*p, dry=dry) for p in PAGES)
    print(f"\n共 {n} 个页面{'将' if dry else '已'}更新")


if __name__ == "__main__":
    main()
