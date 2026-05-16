#!/usr/bin/env python3
import sys, json, re

sys.stdout.reconfigure(encoding="utf-8")

base = "G:/MoonReader_Sync/粤海投资"

with open(f"{base}/Extracted/05_关连及须予披露交易.md", "r", encoding="utf-8") as f:
    content = f.read()

# Fixed regex: dates contain digits, hyphens, slashes; no whitespace inside
pattern = r"###\s+([\d/\-]+(?:\s*/\s*[\d/\-]+)*)\s*[-–—]\s*(.+?)(?=\n|$)"
matches = re.findall(pattern, content)
print(f"Regex found {len(matches)} matches")
for m in matches[:10]:
    print(f"  date='{m[0]}' title='{m[1][:60]}'")

# Now build the full mapping
with open(f"{base}/HKEX/00270_announcement_urls.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Build lookup
url_by_date = {}
for ann in data["announcements"]:
    d = ann["date"]
    url_by_date.setdefault(d, []).append(ann)

# Match
all_dates_found = set()
output = []
seen_urls = set()

for ann_date, title in matches:
    clean_title = re.sub(r"\s*\*+\s*", "", title).strip()
    parts = [p.strip() for p in re.split(r"\s*/\s*", ann_date)]

    for p in parts:
        if re.match(r"\d{4}-\d{2}-\d{2}", p):
            all_dates_found.add(p)
            if p in url_by_date:
                for m in url_by_date[p]:
                    if m["url"] not in seen_urls:
                        seen_urls.add(m["url"])
                        output.append(
                            {
                                "date": m["date"],
                                "filename": m["filename"],
                                "url": m["url"],
                                "title": clean_title,
                            }
                        )

print(f"\nUnique dates found: {len(all_dates_found)}")
print(f"Matched entries: {len(output)}")

# Save
with open(f"{base}/gemini/matched_urls.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Saved to gemini/matched_urls.json")

# Print summary by year
by_year = {}
for item in output:
    y = item["date"][:4]
    by_year.setdefault(y, []).append(item)

for y in sorted(by_year.keys()):
    print(f"  {y}: {len(by_year[y])} announcements")
