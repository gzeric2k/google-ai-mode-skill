import sys, json

sys.stdout.reconfigure(encoding="utf-8")
with open(
    "G:/MoonReader_Sync/粤海投资/HKEX/00270_announcement_urls.json",
    "r",
    encoding="utf-8",
) as f:
    data = json.load(f)
anns = data["announcements"]
# Find profit warning and 2023 results
for i, a in enumerate(anns):
    if "盈利警告" in a["title"] or "profit" in a["title"].lower():
        print(f"IDX {i}: {a['date']} | {a['title'][:60]}")
        print(f"  URL: {a['url']}")
    if "2023年度" in a["title"]:
        print(f"IDX {i}: {a['date']} | {a['title'][:60]}")
        print(f"  URL: {a['url']}")
