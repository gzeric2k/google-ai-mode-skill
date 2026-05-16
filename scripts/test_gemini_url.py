"""
测试 Google AI Mode (Gemini) 能否读取并分析指定公告URL
"""

import sys, os, subprocess, json, re

sys.stdout.reconfigure(encoding="utf-8")

SEARCH_SCRIPT = os.path.join(os.path.dirname(__file__), "search.py")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")

# 用更精确的query，让Gemini去读取这个链接
test_url = (
    "https://www1.hkexnews.hk/listedco/listconews/sehk/2024/0126/2024012600788_c.pdf"
)
query = f"请读取并分析这份港交所公告的内容（不要搜索公司概况，只分析下面这个链接的具体内容）。公告链接: {test_url}。你是我的投资分析助手，请列出主要要点、关键财务数据和投资含义。"

print(f"Querying Google AI Mode (Gemini) to read URL...")
print(f"URL: {test_url}")
print()

result = subprocess.run(
    [sys.executable, SEARCH_SCRIPT, "--query", query, "--save"],
    cwd=os.path.dirname(SEARCH_SCRIPT),
    capture_output=True,
    text=True,
    timeout=120,
)

# 查找本次生成的结果文件（用当前时间近似匹配）
import datetime

now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
print(f"Search started at: {now}")

# 列出所有结果文件
all_results = sorted(
    [f for f in os.listdir(RESULTS_DIR) if f.endswith(".md")],
    key=lambda x: os.path.getmtime(os.path.join(RESULTS_DIR, x)),
    reverse=True,
)

print(f"\n最近生成的结果文件 (前3个):")
for f in all_results[:3]:
    fpath = os.path.join(RESULTS_DIR, f)
    mtime = os.path.getmtime(fpath)
    from datetime import datetime as dt

    mt = dt.fromtimestamp(mtime).strftime("%H:%M:%S")
    size = os.path.getsize(fpath)
    print(f"  [{mt}] {f} ({size} bytes)")

# 读最新的文件
if all_results:
    latest = os.path.join(RESULTS_DIR, all_results[0])
    with open(latest, "r", encoding="utf-8") as rf:
        content = rf.read()
    print(f"\n{'=' * 60}")
    print(f"最新结果文件内容预览:")
    print(f"{'=' * 60}")
    print(content[:2000])
    print(f"\n... (共 {len(content)} 字符)")

print(f"\nSTDERR (错误输出):")
print(result.stderr[:500] if result.stderr else "(无)")
