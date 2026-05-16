"""
测试5条不同类型公告：analyze.py提取→Gemini AI分析
"""

import sys, os, subprocess, json, re, time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

SCRIPTS_DIR = os.path.dirname(__file__)
ANALYZE_SCRIPT = os.path.join(SCRIPTS_DIR, "analyze.py")
SEARCH_SCRIPT = os.path.join(SCRIPTS_DIR, "search.py")
RESULTS_DIR = os.path.join(SCRIPTS_DIR, "..", "results")
JSON_PATH = "G:/MoonReader_Sync/粤海投资/HKEX/00270_announcement_urls.json"

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
anns = data["announcements"]


# Find 5 diverse announcements by searching titles
def find_idx(keywords):
    for i, a in enumerate(anns):
        if all(k in a["title"] for k in keywords):
            return i, a["title"].strip(), a["date"]
    return -1, "", ""


picks = [
    find_idx(["2005", "業績公告", "摘要"]),
    find_idx(["2010", "年報"]),
    find_idx(["中期業績"]),
    find_idx(["ESG"]),
    find_idx(["正面盈利預告"]),
]
# Filter and add fallbacks
valid_picks = []
for i, (idx, title, date) in enumerate(picks):
    if idx > 0:
        valid_picks.append((idx, title, date))
    else:
        # fallback
        valid_picks.append(
            (
                i * 100 + 50,
                anns[i * 100 + 50]["title"].strip(),
                anns[i * 100 + 50]["date"],
            )
        )

print(f"Testing {len(valid_picks)} announcements")
for i, (idx, title, date) in enumerate(valid_picks):
    print(f"  {i + 1}. [{date}] {title[:60]}")


def get_latest_result():
    """Get most recent result file from results dir."""
    files = [
        os.path.join(RESULTS_DIR, f)
        for f in os.listdir(RESULTS_DIR)
        if f.endswith(".md")
    ]
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def extract_text_from_url(url):
    before = get_latest_result()
    result = subprocess.run(
        [sys.executable, ANALYZE_SCRIPT, "--url", url, "--save"],
        cwd=SCRIPTS_DIR,
        capture_output=True,
        text=False,
        timeout=120,
    )
    # Find the newly created file
    files = [
        os.path.join(RESULTS_DIR, f)
        for f in os.listdir(RESULTS_DIR)
        if f.endswith(".md")
    ]
    current = max(files, key=os.path.getmtime) if files else None

    if current and current != before:
        with open(current, "r", encoding="utf-8") as f:
            content = f.read()
        if "## Extracted Content" in content:
            text = content.split("## Extracted Content")[1].strip()
        else:
            text = content
        return text, current
    return None, None


def analyze_with_gemini(text, title, date, url):
    max_chars = 3000
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[...截断至{max_chars}字符]"

    query = f"""你是我的投资分析助手。请分析下面这份粤海投资(00270.HK)公告，列出主要投资分析要点、关键数据和投资含义。

公告标题: {title}
公告日期: {date}
原文链接: {url}

公告内容:
{text}

请以结构化输出。"""

    ts_before = datetime.now()
    result = subprocess.run(
        [sys.executable, SEARCH_SCRIPT, "--query", query],
        cwd=SCRIPTS_DIR,
        capture_output=True,
        text=False,
        timeout=150,
    )

    # Find Gemini result: latest file created after ts_before, NOT starting with "analyze_"
    gemini_files = [
        os.path.join(RESULTS_DIR, f)
        for f in os.listdir(RESULTS_DIR)
        if f.endswith(".md")
        and not f.startswith("analyze_")
        and os.path.getmtime(os.path.join(RESULTS_DIR, f)) > ts_before.timestamp()
    ]
    if gemini_files:
        latest = max(gemini_files, key=os.path.getmtime)
        with open(latest, "r", encoding="utf-8") as f:
            return f.read(), latest
    # Last resort
    stdout = result.stdout.decode("utf-8", errors="replace")
    return stdout[:500], None


for i, (idx, title, date) in enumerate(valid_picks):
    ann = anns[idx]
    url = ann["url"]
    print(f"\n{'=' * 60}")
    print(f"[{i + 1}/5] {date} | {title[:50]}")
    print(f"URL: {url}")

    print("  Step 1: analyze.py 提取文本...", end=" ")
    text, out_file = extract_text_from_url(url)
    if text:
        print(f"OK ({len(text)} chars)")
        print(f"  Step 2: Gemini AI 分析...", end=" ")
        result, rfile = analyze_with_gemini(text, title, date, url)
        if rfile:
            print(f"OK -> {os.path.basename(rfile)}")
            with open(rfile, "r", encoding="utf-8") as f:
                preview = f.read()[:300]
            print(f"  分析摘要: {preview}")
        else:
            print(f"FAIL: {result[:100]}")
    else:
        print(f"FAIL")
        print(f"  Log: {log[:200]}")
    time.sleep(2)

print(f"\n\n测试完成！")
