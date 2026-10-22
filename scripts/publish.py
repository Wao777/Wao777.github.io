#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 n8n 生成的日报发布到 GitHub Pages。

用法:
    python scripts/publish.py "<日报 html 绝对路径>"

n8n 的 Execute Command 节点这样调:
    %USERPROFILE%\\AppData\\Local\\Programs\\Python\\Python314\\python.exe "<站点目录>\\scripts\\publish.py" "{{ $json.filePath }}"

行为:
    1. 校验源文件（存在、非空、像 HTML）—— 防止把报错页推上线
    2. 覆盖 reports/latest.html（首页那个固定地址）
    3. git add / commit，内容没变则直接跳过
    4. fetch + rebase 对齐远端后 push —— 远端若有别人的提交（网页上改过文件、
       别处推过、GitHub 自动生成的 CNAME），直接 push 会被拒，这里先对齐再推

stdout 输出一行 JSON，n8n 可直接解析:
    {"ok": true, "status": "published", "bytes": 4211, "commit": "a1b2c3d"}
退出码非 0 表示失败（11 = 与远端冲突，已回滚）。
"""

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
TARGET = SITE / "reports" / "latest.html"
LOG = SITE / "_incoming" / "publish.log"
MIN_BYTES = 512


def log(line):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write("[%s] %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), line))
    except OSError:
        pass


def finish(payload, code):
    text = json.dumps(payload, ensure_ascii=False)
    print(text)
    log(text)
    sys.exit(code)


def git(*args, timeout=180):
    return subprocess.run(
        ["git"] + list(args),
        cwd=str(SITE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


# 本地分支名。远端若换了主分支名，改这里。
BRANCH = "main"


def sync_with_remote():
    """把自己的提交叠到远端最新之上，返回 (是否可用, 错误信息)。

    远端有别人的提交时，直接 push 会被 non-fast-forward 拒绝；先 fetch 再
    rebase 就能快进推上去。

    fetch 失败（断网、SSH 不可用）不在这里下判断——返回 (True, None) 让后面
    的 push 走它原来的错误路径，保持加容错之前的行为。工作区脏由
    rebase.autoStash 兜住，冲突则 abort 回滚并如实报错。
    """
    fetch = git("fetch", "origin", BRANCH, timeout=120)
    if fetch.returncode != 0:
        return True, None

    rebase = git("-c", "rebase.autoStash=true",
                 "-c", "user.name=n8n", "-c", "user.email=n8n@local",
                 "rebase", "origin/%s" % BRANCH, timeout=180)
    if rebase.returncode == 0:
        return True, None

    git("rebase", "--abort")
    git("stash", "pop")  # autoStash 未自动恢复时兜一下，无 stash 则报错可忽略
    return False, (rebase.stderr or rebase.stdout).strip()


def main():
    if len(sys.argv) < 2:
        finish({"ok": False, "status": "bad_args",
                "error": "用法: publish.py <日报 html 路径>"}, 2)

    src = Path(sys.argv[1]).expanduser()
    if not src.is_absolute():
        src = (Path.cwd() / src).resolve()

    if not src.is_file():
        finish({"ok": False, "status": "missing_src",
                "error": "文件不存在: %s" % src}, 3)

    size = src.stat().st_size
    if size < MIN_BYTES:
        finish({"ok": False, "status": "too_small",
                "error": "文件仅 %d 字节，疑似生成失败，已中止" % size}, 4)

    head = src.read_text(encoding="utf-8", errors="replace")[:400].lower()
    if "<html" not in head and "<body" not in head:
        finish({"ok": False, "status": "not_html",
                "error": "内容不像 HTML，已中止（防止把报错页推上线）"}, 5)

    if not (SITE / ".git").exists():
        finish({"ok": False, "status": "no_repo",
                "error": "%s 还不是 git 仓库，先 git init 并关联远端" % SITE}, 6)

    if not git("remote").stdout.strip():
        finish({"ok": False, "status": "no_remote",
                "error": "仓库没有配置远端，先执行 git remote add origin ..."}, 7)

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, TARGET)

    add = git("add", "reports/latest.html")
    if add.returncode != 0:
        finish({"ok": False, "status": "git_add_failed",
                "error": (add.stderr or add.stdout).strip()}, 8)

    if git("diff", "--cached", "--quiet").returncode == 0:
        finish({"ok": True, "status": "no_change", "bytes": size,
                "message": "内容与仓库一致，跳过提交"}, 0)

    commit = git("-c", "user.name=n8n", "-c", "user.email=n8n@local",
                 "commit", "-m", "daily: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    if commit.returncode != 0:
        finish({"ok": False, "status": "commit_failed",
                "error": (commit.stderr or commit.stdout).strip()}, 9)

    ok, err = sync_with_remote()
    if not ok:
        finish({"ok": False, "status": "rebase_conflict",
                "error": "与远端提交冲突，已回滚，需人工处理: %s" % err}, 11)

    push = git("push", timeout=240)
    if push.returncode != 0:
        # 少数情况：fetch 之后远端又被推进，或 fetch 因网络失败被跳过。
        # 判断是不是「落后」导致的拒绝，是的话再对齐一次。
        text = (push.stderr or push.stdout)
        if any(k in text.lower() for k in
               ("non-fast-forward", "fetch first", "rejected")):
            ok, err = sync_with_remote()
            if not ok:
                finish({"ok": False, "status": "rebase_conflict",
                        "error": "与远端提交冲突，已回滚，需人工处理: %s" % err}, 11)
            push = git("push", timeout=240)
        if push.returncode != 0:
            finish({"ok": False, "status": "push_failed",
                    "error": (push.stderr or push.stdout).strip()}, 10)

    sha = git("rev-parse", "--short", "HEAD").stdout.strip()
    finish({"ok": True, "status": "published", "bytes": size, "commit": sha}, 0)


if __name__ == "__main__":
    main()
