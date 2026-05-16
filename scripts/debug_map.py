#!/usr/bin/env python3
import sys, json, re

sys.stdout.reconfigure(encoding="utf-8")

base = "G:/MoonReader_Sync/粤海投资"

with open(f"{base}/Extracted/05_关连及须予披露交易.md", "r", encoding="utf-8") as f:
    content = f.read()

# Test regex
pattern = r"###\s+([\d\-/\s]+?)\s*[-–—]\s*(.+?)(?=\n|$)"
matches = re.findall(pattern, content)
print(f"Regex found {len(matches)} matches")
if matches:
    for m in matches[:5]:
        print(f"  date='{m[0]}' title='{m[1][:50]}'")
else:
    # Try simpler pattern
    pattern2 = r"###\s+(.+?)\s*[-–—]\s*(.+)"
    matches2 = re.findall(pattern2, content)
    print(f"Simple regex found {len(matches2)} matches")
    if matches2:
        for m in matches2[:5]:
            print(f"  '{m[0]}' -> '{m[1][:50]}'")
    else:
        # What's the exact bytes at line 11?
        lines = content.split("\n")
        line11 = lines[10]  # 0-indexed
        print(f"\nLine 11 repr: {repr(line11)}")
        print(f"Line 11 hex: {line11.encode('utf-8').hex()}")
