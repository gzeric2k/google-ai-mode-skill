"""
从JSON抽取5条URL: analyze.py提取→Gemini分析
"""

import sys, os, subprocess, json, re

sys.stdout.reconfigure(encoding="utf-8")
from datetime import datetime

SCRIPTS_DIR = os.path.dirname(__file__)
ANALYZE = os.path.join(SCRIPTS_DIR, "analyze.py")
SEARCH = os.path.join(SCRIPTS_DIR, "search.py")
RESULTS = os.path.join(SCRIPTS_DIR, "..", "results")
JSON_PATH = "G:/MoonReader_Sync/粤海投资/HKEX/00270_announcement_urls.json"

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
anns = data["announcements"]

# Find 5 diverse announcements by title keywords
targets = []
for kw, label in [
    (["環境、社會及管治"], "ESG report 2021"),
    (["可換股債券", "發行"], "Convertible bond 2011"),
    (["2025年度業績"], "Annual results 2025"),
    (["中期報告"], "Interim report 2018"),
    (["收購", "目標公司"], "Acquisition 2018"),
]:
    for i, a in enumerate(anns):
        if all(k in a["title"] for k in kw):
            targets.append((i, a["title"].strip(), a["date"], a["url"], label))
            break

print(f"Found {len(targets)} targets\n")
for i, (idx, title, date, url, label) in enumerate(targets):
    print(f"  {i + 1}. [{date}] {label}: {title[:50]}")


def get_latest_result():
    files = [os.path.join(RESULTS, f) for f in os.listdir(RESULTS) if f.endswith(".md")]
    return max(files, key=os.path.getmtime) if files else None


for i, (idx, title, date, url, label) in enumerate(targets):
    ann = anns[idx]
    print(f"\n{'=' * 60}")
    print(f"[{i + 1}/5] {ann['date']} | {label}")
    print(f"  Title: {ann['title'][:60]}")

    # Step 1: analyze.py extract
    print(f"  Step 1: analyze.py extract...", end=" ")
    ts_before = datetime.now().timestamp()
    subprocess.run(
        [sys.executable, ANALYZE, "--url", ann["url"], "--save"],
        cwd=SCRIPTS_DIR,
        timeout=120,
    )

    raw_files = [
        os.path.join(RESULTS, f)
        for f in os.listdir(RESULTS)
        if f.endswith(".md") and os.path.getmtime(os.path.join(RESULTS, f)) >= ts_before
    ]

    if not raw_files:
        print("FAIL (no new file)")
        continue
    raw_file = max(raw_files, key=os.path.getmtime)

    with open(raw_file, "r", encoding="utf-8") as f:
        content = f.read()
    text = (
        content.split("## Extracted Content")[1].strip()
        if "## Extracted Content" in content
        else content
    )
    print(f"OK ({len(text)} chars)")

    # Step 2: Gemini analysis
    max_chars = 3000
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[...截断至{max_chars}字符]"

    query = f"""你是投资分析助手，分析这份粤海投资公告，列出核心事项、关键数据、投资分析、投资含义。

标题: {ann["title"].strip()}
日期: {ann["date"]}

内容:
{text}"""

    print(f"  Step 2: Gemini AI分析...", end=" ")
    ts = datetime.now()
    subprocess.run(
        [sys.executable, SEARCH, "--query", query], cwd=SCRIPTS_DIR, timeout=150
    )

    gemini_files = [
        os.path.join(RESULTS, f)
        for f in os.listdir(RESULTS)
        if f.endswith(".md")
        and f.startswith("GEMINI")
        and os.path.getmtime(os.path.join(RESULTS, f)) >= ts.timestamp()
    ]

    if gemini_files:
        gf = max(gemini_files, key=os.path.getmtime)
        with open(gf, "r", encoding="utf-8") as f:
            analysis = f.read()
        print(f"OK -> {os.path.basename(gf)}")
        print(f"  Preview: {analysis[:200].replace(chr(10), ' ')}...")
    else:
        print("FAIL (no Gemini output)")

print(f"\n{'=' * 60}")
print("Done!")
