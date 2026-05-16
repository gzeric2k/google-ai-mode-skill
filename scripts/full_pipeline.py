"""
完整pipeline: analyze.py提取→Gemini分析
1. 用analyze.py下载URL并提取文本
2. 把提取文本作为query传给Google AI Mode (Gemini)分析
"""

import sys, os, subprocess, json

sys.stdout.reconfigure(encoding="utf-8")

SCRIPTS_DIR = os.path.dirname(__file__)
ANALYZE_SCRIPT = os.path.join(SCRIPTS_DIR, "analyze.py")
SEARCH_SCRIPT = os.path.join(SCRIPTS_DIR, "search.py")
RESULTS_DIR = os.path.join(SCRIPTS_DIR, "..", "results")
JSON_PATH = "G:/MoonReader_Sync/粤海投资/HKEX/00270_announcement_urls.json"


def extract_text_from_url(url):
    """Step 1: Use analyze.py to download and extract text."""
    # Run with --save to get result in RESULTS_DIR
    result = subprocess.run(
        [sys.executable, ANALYZE_SCRIPT, "--url", url, "--save"],
        cwd=SCRIPTS_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    stdout = result.stdout
    stderr = result.stderr
    print(f"  analyze.py stdout (last 10 lines):")
    for line in stdout.split("\n")[-10:]:
        if line.strip():
            print(f"    {line.strip()[:100]}")
    if stderr:
        print(f"  stderr: {stderr[:200]}")

    # Find Saved: line
    for line in stdout.split("\n"):
        if "Saved:" in line:
            out_file = line.replace("Saved:", "").strip()
            print(f"  Saved path: {out_file}")
            if os.path.exists(out_file):
                with open(out_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if "## Extracted Content" in content:
                    text = content.split("## Extracted Content")[1].strip()
                else:
                    text = content
                return text, out_file
            else:
                print(f"  File NOT FOUND at: {out_file}")
                print(f"  CWD: {os.getcwd()}")
    return None, None


def analyze_with_gemini(text, title, date):
    """Step 2: Send extracted text to Google AI Mode for analysis."""
    # Truncate text if too long
    max_chars = 4000
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[...内容过长，截断至{max_chars}字符]"

    query = f"""你是我的投资分析助手。请分析下面这份粤海投资(00270.HK)公告的内容，列出主要投资分析要点、关键财务数据和投资含义。

公告标题: {title}
公告日期: {date}

公告内容:
{text}

请以结构化格式输出：核心事项、关键数据、投资分析、投资含义(正面/中性/负面)。"""

    result = subprocess.run(
        [sys.executable, SEARCH_SCRIPT, "--query", query, "--save"],
        cwd=SCRIPTS_DIR,
        capture_output=True,
        text=True,
        timeout=150,
    )

    # Find latest result file
    all_results = sorted(
        [f for f in os.listdir(RESULTS_DIR) if f.endswith(".md")],
        key=lambda x: os.path.getmtime(os.path.join(RESULTS_DIR, x)),
        reverse=True,
    )

    if all_results:
        latest = os.path.join(RESULTS_DIR, all_results[0])
        with open(latest, "r", encoding="utf-8") as f:
            return f.read(), latest
    return result.stdout, None


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    anns = data["announcements"]

    # Test with 2 key announcements
    targets = [
        (943, "2024-01-26 盈利警告"),
        (952, "2024-03-25 2023年度业绩"),
    ]

    print("=" * 60)
    print("完整Pipeline测试: analyze.py提取→Gemini AI分析")
    print("=" * 60)

    for idx, desc in targets:
        ann = anns[idx]
        print(f"\n\n--- 测试: {desc} ---")
        print(f"URL: {ann['url']}")

        # Step 1: Extract
        print("\n[Step 1] analyze.py 提取文本...")
        text, out_file = extract_text_from_url(ann["url"])
        if not text:
            print(f"提取失败!")
            continue
        print(f"提取成功: {len(text)} 字符")
        print(f"文件: {out_file}")

        # Step 2: Analyze
        print(f"\n[Step 2] 发送给 Gemini AI 分析...")
        gemini_result, result_file = analyze_with_gemini(
            text, ann["title"].strip(), ann["date"]
        )
        print(f"Gemini分析完成!")
        if result_file:
            print(f"结果保存: {result_file}")
            # Show preview
            # Clean preview: remove the first line if it starts with "Copy"
            preview = gemini_result[:800].replace("\n", " ")
            print(f"预览: {preview}...")

    print(f"\n\n测试完成!")


if __name__ == "__main__":
    main()
