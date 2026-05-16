"""
Test 10 HKEX announcement URLs through Google AI Mode
"""

import sys, json, os, subprocess, time

sys.stdout.reconfigure(encoding="utf-8")

JSON_PATH = "G:/MoonReader_Sync/粤海投资/HKEX/00270_announcement_urls.json"
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
SEARCH_SCRIPT = os.path.join(os.path.dirname(__file__), "search.py")

# Pick 10 diverse, investment-significant announcements
TARGET_INDICES = {
    0: "first announcement",
    5: "joint announcement suspension",
    15: "warrants withdrawal",
    50: "annual report",
    100: "circular - selling assets",
    238: "annual results 2008",
    478: "RC+WS acquisition 2015",
    543: "annual results 2017",
    850: "profit warning 2024",
    975: "latest acquisition 2025",
}

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

anns = data["announcements"]
print(f"Total in JSON: {data['total']}")
print(f"Testing {len(TARGET_INDICES)} announcements\n")

for idx, desc in TARGET_INDICES.items():
    ann = anns[idx]
    prompt = f"你是我的投资分析助手，分析这份港交所公告内容，列出主要的投资分析要点。公告标题: {ann['title']}。公告日期: {ann['date']}。公告链接: {ann['url']}"

    print(f"\n{'=' * 60}")
    print(f"[{idx + 1}] {desc}")
    print(f"    Date: {ann['date']}")
    print(f"    Title: {ann['title'][:60]}")
    print(f"    URL: {ann['url']}")
    print(f"{'=' * 60}")

    # Run google-ai-mode search
    result = subprocess.run(
        [sys.executable, SEARCH_SCRIPT, "--query", prompt, "--save"],
        cwd=os.path.dirname(SEARCH_SCRIPT),
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Find the result file
    result_files = sorted(
        [f for f in os.listdir(RESULTS_DIR) if f.endswith(".md")],
        key=lambda x: os.path.getmtime(os.path.join(RESULTS_DIR, x)),
        reverse=True,
    )

    if result_files:
        latest = os.path.join(RESULTS_DIR, result_files[0])
        with open(latest, "r", encoding="utf-8") as rf:
            content = rf.read()
        print(f"    Result saved: {result_files[0]} ({len(content)} chars)")
        print(f"    Preview: {content[:200]}...")
    else:
        print(f"    Error: {result.stderr[:200]}")

    time.sleep(2)

print("\n\nAll 10 tests completed!")
