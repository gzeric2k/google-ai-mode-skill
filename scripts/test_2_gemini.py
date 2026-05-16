#!/usr/bin/env python3
"""Test gemini_analyze.py with 2 URLs"""

import sys, os, json, subprocess, time, random, re

sys.stdout.reconfigure(encoding="utf-8")

ANALYZE_SCRIPT = (
    r"C:\Users\jeche\.config\opencode\skills\google-ai-mode-skill\scripts\run.py"
)
BASE_DIR = r"G:\MoonReader_Sync\粤海投资"
OUTPUT_DIR = os.path.join(BASE_DIR, "gemini")
MATCHED_FILE = os.path.join(OUTPUT_DIR, "matched_urls.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(MATCHED_FILE, "r", encoding="utf-8") as f:
    items = json.load(f)

# Pick 2 test URLs
test_items = [items[0], items[4]]  # First and 5th (different years)
for item in test_items:
    print(f"  {item['date']} | {item['title'][:50]} | {item['url']}")

for idx, item in enumerate(test_items):
    url = item["url"]
    date = item["date"]
    title = item["title"]

    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)[:60]
    safe_date = date.replace("-", "")
    out_file = os.path.join(OUTPUT_DIR, f"TEST_GEMINI_{safe_date}_{safe_title}.md")

    print(f"\n[{idx + 1}/2] {date} {title[:50]}")

    query = (
        f"请分析这份香港交易所公告。公告来自粤海投资(股票代码00270)。"
        f"根据公告内容提取关键信息：交易类型、交易对手、交易金额、核心条款、"
        f"对公司的战略意义。结构化格式，包含具体数字。只依据文件内容。"
    )

    cmd = [
        sys.executable,
        ANALYZE_SCRIPT,
        "gemini_analyze.py",
        "--url",
        url,
        "--query",
        query,
        "--output",
        out_file,
    ]

    print(f"  Running gemini_analyze.py...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=os.path.dirname(ANALYZE_SCRIPT),
    )

    print(f"  Return code: {result.returncode}")
    if result.stdout:
        # Print last few lines of stdout
        lines = result.stdout.strip().split("\n")
        print(
            f"  stdout ({len(lines)} lines): ...{lines[-3] if len(lines) > 3 else lines[0]}"
        )
    if result.stderr:
        print(f"  stderr: {result.stderr[:200]}")

    if os.path.exists(out_file):
        size = os.path.getsize(out_file)
        print(f"  Output file: {os.path.basename(out_file)} ({size} bytes)")
        # Show first 300 chars
        with open(out_file, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"  Content preview: {content[:300]}")
    else:
        print(f"  ERROR: Output file not created!")

    if idx < len(test_items) - 1:
        delay = random.uniform(15, 30)
        print(f"  Waiting {delay:.0f}s...")
        time.sleep(delay)

print(f"\nDone!")
