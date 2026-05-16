#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gemini_login.py — 登录gemini.google.com并保存session

用法: python scripts/run.py gemini_login.py
      python scripts/run.py gemini_login.py --duration 300

打开浏览器后，你有指定时间（默认5分钟）登录Google账号。
登录成功后关闭浏览器窗口即可。Session自动保存供后续使用。
"""

import sys, os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

import time
import argparse
from patchright.sync_api import sync_playwright
from browser_utils import BrowserFactory
from config import BROWSER_PROFILE_DIR

parser = argparse.ArgumentParser()
parser.add_argument(
    "--duration",
    type=int,
    default=300,
    help="Browser open duration in seconds (default: 300)",
)
args = parser.parse_args()

print("=" * 60)
print("Gemini Login Helper")
print("=" * 60)
print(f"Profile:   {BROWSER_PROFILE_DIR}")
print(f"Duration:  {args.duration}秒 ({args.duration // 60}分钟)")
print()
print("浏览器已打开，请完成以下步骤：")
print("  1. 登录你的Google账号")
print("  2. 访问 gemini.google.com")
print("  3. 确认可以正常使用（可输入一条测试prompt）")
print()
print(f"{args.duration // 60}分钟后浏览器自动关闭，或手动关闭窗口。")
print("Session会自动保存，后续headless运行无需再登录。")
print("=" * 60)

pw = sync_playwright().start()
factory = BrowserFactory()
ctx = factory.launch_persistent_context(pw, headless=False)
page = ctx.new_page()
page.goto("https://gemini.google.com", wait_until="load", timeout=60000)

# Wait for user to login, checking periodically
start = time.time()
logged_in = False
while time.time() - start < args.duration:
    time.sleep(5)
    try:
        title = page.title()
        url = page.url
        body = page.inner_text("body")[:200].lower()
        # Check if we see Gemini chat UI (not login wall)
        if "gemini" in url and (
            "sign in" not in body[:100] if len(body) > 100 else True
        ):
            elapsed = int(time.time() - start)
            if elapsed > 30:  # Give 30s for initial load
                print(f"  [{elapsed}s] Gemini会话活跃中 ✓")
                logged_in = True
        # Check if page was closed by user
        if page.is_closed():
            print("浏览器窗口已关闭")
            break
    except:
        print("浏览器已关闭")
        break

if logged_in:
    print(f"\n登录成功！Session已保存至：{BROWSER_PROFILE_DIR}")
else:
    print(f"\n{args.duration}秒超时。如需更多时间，增加 --duration 参数。")

# Cleanup
try:
    if not page.is_closed():
        page.close()
    ctx.close()
    pw.stop()
except:
    pass
print("完成。现在可以运行: python scripts/run.py gemini_analyze.py --url <URL> --save")
