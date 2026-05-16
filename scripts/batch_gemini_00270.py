#!/usr/bin/env python3
"""
Batch processor: Extract HKEX announcement PDFs via gemini_analyze.py
Uses Gemini AI to analyze PDF content. Saves to gemini/ subfolder.
15-30s random delays between calls. Retries on errors.
"""

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

print(f"Total items to process: {len(items)}")

# Track already processed URLs
processed_log = os.path.join(OUTPUT_DIR, "PROCESSED.log")
processed_urls = set()
if os.path.exists(processed_log):
    with open(processed_log, "r", encoding="utf-8") as f:
        for line in f:
            processed_urls.add(line.strip())
    print(f"Already processed: {len(processed_urls)} URLs (skipping)")

success = 0
failed = 0
skipped = 0
max_retries = 3

for idx, item in enumerate(items):
    url = item["url"]
    date = item["date"]
    title = item["title"]

    if url in processed_urls:
        skipped += 1
        print(f"[{idx + 1}/{len(items)}] SKIP (already done): {date} {title[:40]}")
        continue

    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)[:60]
    safe_date = date.replace("-", "")
    out_file = os.path.join(OUTPUT_DIR, f"GEMINI_{safe_date}_{safe_title}.md")

    print(f"\n[{idx + 1}/{len(items)}] Processing: {date} {title[:50]}")
    print(f"  URL: {url[:80]}...")

    query = (
        f"请分析这份香港交易所公告。公告来自粤海投资(股票代码00270)。"
        f"请根据公告内容提取关键信息，包括：交易类型、交易对手、交易金额、核心条款、"
        f"对公司的战略意义。请用结构化格式输出，包含具体数字。"
        f"只依据文件内容，不要使用外部知识。"
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

    # Retry loop
    for attempt in range(1, max_retries + 1):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=os.path.dirname(ANALYZE_SCRIPT),
            )

            if result.returncode == 0:
                if os.path.exists(out_file) and os.path.getsize(out_file) > 100:
                    with open(processed_log, "a", encoding="utf-8") as f:
                        f.write(url + "\n")
                    success += 1
                    print(f"  OK -> {os.path.basename(out_file)}")
                    break
                else:
                    raise Exception("Output file too small or missing")
            else:
                err_msg = result.stderr[:300] if result.stderr else "Unknown error"
                if "ERROR:" in result.stdout:
                    err_msg = result.stdout[:300]
                raise Exception(f"Exit code {result.returncode}: {err_msg}")

        except Exception as e:
            if attempt < max_retries:
                retry_delay = random.uniform(30, 60)
                print(f"  Attempt {attempt}/{max_retries} failed: {str(e)[:80]}")
                print(f"  Retrying in {retry_delay:.0f}s...")
                time.sleep(retry_delay)
            else:
                failed += 1
                print(f"  FAIL after {max_retries} attempts: {str(e)[:100]}")

    # Delay between calls (15-30 seconds)
    if idx < len(items) - 1:
        delay = random.uniform(15, 30)
        print(f"  Waiting {delay:.0f}s before next...")
        time.sleep(delay)

print(f"\n{'=' * 60}")
print(
    f"DONE: {success} success, {failed} failed, {skipped} skipped of {len(items)} total"
)
print(f"Results in: {OUTPUT_DIR}")
