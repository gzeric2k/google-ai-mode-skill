#!/usr/bin/env python3
"""
Batch processor: Extract HKEX announcement PDFs via google-ai-mode-skill's analyze.py
Saves results to gemini/ subfolder with 15-30s random delays between calls.
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
    print(f"Already processed: {len(processed_urls)} URLs (from {processed_log})")

success = 0
failed = 0
skipped = 0

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
    out_file = os.path.join(OUTPUT_DIR, f"ANALYSIS_{safe_date}_{safe_title}.md")

    print(f"\n[{idx + 1}/{len(items)}] Processing: {date} {title[:50]}")
    print(f"  URL: {url[:80]}...")

    cmd = [
        sys.executable,
        ANALYZE_SCRIPT,
        "analyze.py",
        "--url",
        url,
        "--output",
        out_file,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(ANALYZE_SCRIPT),
        )

        if result.returncode == 0:
            # Verify file was created
            if os.path.exists(out_file) and os.path.getsize(out_file) > 100:
                with open(processed_log, "a", encoding="utf-8") as f:
                    f.write(url + "\n")
                success += 1
                print(f"  OK -> {os.path.basename(out_file)}")
            else:
                failed += 1
                print(f"  FAIL: Output file too small or missing")
        else:
            failed += 1
            print(f"  FAIL (exit code {result.returncode}): {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        failed += 1
        print(f"  FAIL: Timeout")
    except Exception as e:
        failed += 1
        print(f"  FAIL: {e}")

    # Delay between calls (15-30 seconds)
    if idx < len(items) - 1:
        delay = random.uniform(15, 30)
        print(f"  Waiting {delay:.0f}s...")
        time.sleep(delay)

print(f"\n{'=' * 60}")
print(
    f"DONE: {success} success, {failed} failed, {skipped} skipped of {len(items)} total"
)
print(f"Results in: {OUTPUT_DIR}")
