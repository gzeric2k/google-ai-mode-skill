import json

with open(
    "G:/MoonReader_Sync/粤海投资/HKEX/00270_announcement_urls.json", encoding="utf-8"
) as f:
    data = json.load(f)
count = 0
for u in data.get("announcements", []):
    url = u.get("url", "")
    if url.endswith(".pdf"):
        print(f"{u.get('date', '?')} | {u.get('title', '?')[:60]} | {url}")
        count += 1
        if count >= 10:
            break
