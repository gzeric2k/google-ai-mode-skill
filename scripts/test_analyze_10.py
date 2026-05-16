"""
测试 analyze.py 处理10条HKEX公告URL
修正Big5编码问题，输出结构化投资分析
"""

import sys, os, json, re, io

sys.stdout.reconfigure(encoding="utf-8")

JSON_PATH = "G:/MoonReader_Sync/粤海投资/HKEX/00270_announcement_urls.json"
ANALYZE_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(ANALYZE_DIR, "..", "results")

# Add scripts to path
sys.path.insert(0, ANALYZE_DIR)

from analyze import download_url, extract_pdf, detect_type
from bs4 import BeautifulSoup
from datetime import datetime


def extract_html_fixed(content: bytes) -> str:
    """Extract text from HTML bytes with proper charset detection."""
    # Find charset from meta tags
    charset = "utf-8"
    meta_match = re.search(rb'charset=([^"\'\s;>]+)', content[:5000])
    if meta_match:
        detected = meta_match.group(1).decode("ascii", errors="ignore").lower()
        if detected in ("big5", "gbk", "gb2312", "gb18030", "shift_jis", "euc-kr"):
            charset = detected

    # Decode with detected charset
    text = content.decode(charset, errors="replace")

    # Parse with BeautifulSoup
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "head", "noscript"]):
        tag.decompose()

    main = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id="content")
        or soup.find(class_="content")
        or soup.body
    )

    text = (main or soup).get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class SimpleLogger:
    def debug(self, msg):
        print(f"  [DEBUG] {msg}")

    def info(self, msg):
        print(f"  [INFO] {msg}")


def extract_announcement(url: str, logger=None):
    """Download and extract text from HKEX announcement URL."""
    logger = logger or SimpleLogger()
    content_bytes, content_type = download_url(url, logger)
    file_type = detect_type(url, content_type)

    if file_type == "pdf":
        extracted = extract_pdf(content_bytes, logger or print)
    elif file_type == "html":
        extracted = extract_html_fixed(content_bytes)
    else:
        extracted = content_bytes.decode("utf-8", errors="replace")

    return extracted, file_type


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    anns = data["announcements"]

    # Pick 10 diverse, investment-significant announcements
    picks = [
        (0, "first announcement"),
        (10, "first results announcement"),
        (48, "first annual report (2002)"),
        (98, "circular - selling non-core assets (2003)"),
        (233, "annual results (2008)"),
        (478, "RC+WS acquisition (2015)"),
        (543, "annual results (2017)"),
        (753, "acquisition (2021)"),
        (850, "profit warning (2024)"),
        (975, "latest acquisition (2025)"),
    ]

    # Find actual indices by searching titles
    def find_index(keywords, start_from=0):
        for i, a in enumerate(anns):
            if i < start_from:
                continue
            if all(k in a["title"] for k in keywords):
                return i
        return -1

    actual_picks = [
        (find_index(["業績公告"], 0), "1999 results"),
        (find_index(["年報"], 45), "2007 annual report"),
        (find_index(["通函", "出售"], 90), "2003 circular - sell assets"),
        (find_index(["業績公告", "2007"], 200), "2008 annual results"),
        (find_index(["收購", "RC"], 470), "2015 RC+WS acquisition"),
        (find_index(["年度業績公告"], 540), "2017 annual results"),
        (find_index(["2020年度業績"], 700), "2021 annual results"),
        (find_index(["盈利警告"], 830), "2024 profit warning"),
        (find_index(["2023年度業績"], 870), "2024 annual results"),
        (find_index(["收購兩間"], 960), "2025 acquisition"),
    ]

    # Filter out invalid
    valid_picks = [(i, d) for i, d in actual_picks if i > 0]

    print(f"Testing {len(valid_picks)} announcements via analyze.py\n")

    results = []
    for idx, desc in valid_picks:
        ann = anns[idx]
        url = ann["url"]

        print(f"{'=' * 60}")
        print(f"[{idx + 1}] {desc}")
        print(f"    Date: {ann['date']}")
        print(f"    Title: {ann['title'][:70]}")
        print(f"    URL: {url}")

        try:
            text, file_type = extract_announcement(url)
            print(f"    Type: {file_type.upper()}, Chars: {len(text)}")

            # Save result
            safe_name = re.sub(r"[^a-zA-Z0-9]", "_", ann["date"] + "_" + desc[:30])
            out_path = os.path.join(RESULTS_DIR, f"analyze_{safe_name}.md")

            # Build structured analysis
            date_str = ann["date"]
            title = ann["title"].strip()

            # Extract key financial data
            financial_data = []
            patterns = [
                (r"營業額\s*:\s*([\d,]+)", "营业额"),
                (r"(盈利|虧損)[^:]*:\s*([\(\)\d,]+)", "利润"),
                (r"每股[^:]*:\s*([\(\)\d\.\s]*仙)", "每股"),
            ]
            for pat, label in patterns:
                m = re.search(pat, text)
                if m:
                    financial_data.append(f"{label}: {m.group(1).strip()}")

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"# 粤海投资(HK:00270) 公告分析\n\n")
                f.write(f"| 字段 | 内容 |\n")
                f.write(f"|------|------|\n")
                f.write(f"| **日期** | {date_str} |\n")
                f.write(f"| **标题** | {title} |\n")
                f.write(f"| **类型** | {desc} |\n")
                f.write(f"| **格式** | {file_type.upper()} |\n")
                f.write(f"| **提取字符** | {len(text):,} |\n")
                f.write(f"| **来源URL** | `{url}` |\n")
                if financial_data:
                    f.write(f"| **关键数据** | {'; '.join(financial_data[:3])} |\n")
                f.write(f"\n---\n\n")
                f.write(f"## 提取内容\n\n")
                f.write(text[:8000])
                if len(text) > 8000:
                    f.write(f"\n\n... [内容过长，展示前8000字符]")

            print(f"    Saved: analyze_{safe_name}.md")
            results.append(
                {
                    "idx": idx,
                    "desc": desc,
                    "title": title,
                    "type": file_type,
                    "chars": len(text),
                }
            )

        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"idx": idx, "desc": desc, "error": str(e)})

        print()

    # Summary
    print(f"\n{'=' * 60}")
    print(f"测试完成！成功: {sum(1 for r in results if 'chars' in r)}/{len(results)}")
    print(f"{'=' * 60}")
    for r in results:
        status = (
            f"OK ({r['type']}, {r['chars']} chars)"
            if "chars" in r
            else f"FAIL: {r.get('error', '')}"
        )
        print(f"  [{r['desc']}] {status}")


if __name__ == "__main__":
    main()
