"""
Test single URL through Google AI Mode - using query with URL
"""

import sys, os, subprocess, json

sys.stdout.reconfigure(encoding="utf-8")

SEARCH_SCRIPT = os.path.join(os.path.dirname(__file__), "search.py")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")

# Test with an .htm URL (web-accessible content)
test_url = (
    "https://www1.hkexnews.hk/listedco/listconews/sehk/1999/0922/ltn19990922076_c.htm"
)
prompt = f"你是我的投资分析助手。请分析这份港交所公告的内容，列出所有投资分析要点。公告URL: {test_url}"

print(f"Querying Google AI Mode with URL...")
print(f"URL: {test_url}")
print()

result = subprocess.run(
    [sys.executable, SEARCH_SCRIPT, "--query", prompt, "--save"],
    cwd=os.path.dirname(SEARCH_SCRIPT),
    capture_output=True,
    text=True,
    timeout=120,
)

# Find latest result
result_files = sorted(
    [f for f in os.listdir(RESULTS_DIR) if f.endswith(".md") and not f.startswith(".")],
    key=lambda x: os.path.getmtime(os.path.join(RESULTS_DIR, x)),
    reverse=True,
)

if result_files:
    latest = os.path.join(RESULTS_DIR, result_files[0])
    with open(latest, "r", encoding="utf-8") as rf:
        content = rf.read()
    print(f"Result file: {result_files[0]}")
    print(f"Content length: {len(content)} chars")
    print(f"\n{'=' * 60}")
    print(content[:2000])
    print(f"{'=' * 60}")
else:
    print("STDERR:", result.stderr[:500])
