#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding="utf-8")
"""
Document Analyzer for Google AI Mode Skill
Downloads and extracts text from files (PDF, HTML, TXT) via URL or local path.
Returns structured markdown so Claude Code can analyze the content directly.

Usage:
  python scripts/run.py analyze.py --url "https://example.com/doc.pdf"
  python scripts/run.py analyze.py --file /path/to/report.pdf --question "What are the key financials?"
  python scripts/run.py analyze.py --url "https://..." --save --debug
"""

import sys
import re
import argparse
import io
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

# Local imports
from config import RESULTS_DIR
from logger import get_logger


# =============================================================================
# FILE TYPE DETECTION
# =============================================================================


def detect_type(source: str, content_type: str = "") -> str:
    lower = source.lower()
    ct_lower = content_type.lower()

    if lower.endswith(".pdf") or "application/pdf" in ct_lower:
        return "pdf"
    if lower.endswith((".html", ".htm")) or "text/html" in ct_lower:
        return "html"
    if lower.endswith((".txt", ".md", ".rst", ".csv", ".log")):
        return "text"
    if "text/plain" in ct_lower:
        return "text"
    # Default to text (attempt decode)
    return "text"


# =============================================================================
# DOWNLOAD
# =============================================================================


def download_url(url: str, logger) -> Tuple[bytes, str]:
    """Download file from URL. Returns (content_bytes, content_type)."""
    logger.debug(f"Downloading: {url}")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()
            logger.debug(
                f"Downloaded {len(data):,} bytes  Content-Type: {content_type}"
            )
            return data, content_type
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} downloading {url}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error downloading {url}: {e.reason}")


# =============================================================================
# TEXT EXTRACTION
# =============================================================================


def extract_pdf(content: bytes, logger) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber not installed. Delete .venv and re-run to trigger reinstall."
        )

    parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        total = len(pdf.pages)
        logger.debug(f"PDF: {total} pages")
        for i, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text()
            if page_text and page_text.strip():
                parts.append(f"### Page {i}\n\n{page_text.strip()}")

    if not parts:
        raise RuntimeError(
            "No text extracted from PDF. "
            "Document may be scanned/image-only (OCR not supported)."
        )

    return "\n\n".join(parts)


def extract_html(content: bytes, logger) -> str:
    """Extract readable text from HTML using BeautifulSoup."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(content, "html.parser")

    # Remove noise tags
    for tag in soup(["script", "style", "nav", "footer", "head", "noscript"]):
        tag.decompose()

    # Try main content areas first
    main = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id="content")
        or soup.find(class_="content")
        or soup.body
    )

    text = (main or soup).get_text(separator="\n", strip=True)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    logger.debug(f"HTML: extracted {len(text):,} chars")
    return text.strip()


def extract_text(content: bytes, logger) -> str:
    """Decode plain text bytes."""
    for enc in ("utf-8", "utf-16", "gb18030", "big5", "latin-1"):
        try:
            text = content.decode(enc)
            logger.debug(f"Text decoded as {enc}, {len(text):,} chars")
            return text
        except (UnicodeDecodeError, LookupError):
            continue
    return content.decode("utf-8", errors="replace")


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================


def analyze_document(
    source: str,
    is_url: bool,
    question: Optional[str],
    logger,
) -> Dict[str, Any]:
    """Fetch/read source, extract text, return result dict."""

    # --- Fetch content ---
    if is_url:
        print(f"  Downloading: {source[:80]}...")
        content_bytes, content_type = download_url(source, logger)
        file_type = detect_type(source, content_type)
    else:
        path = Path(source)
        if not path.exists():
            return {"success": False, "error": f"File not found: {source}"}
        print(f"  Reading: {path.name}")
        content_bytes = path.read_bytes()
        file_type = detect_type(source)

    logger.debug(f"Detected type: {file_type}")

    # --- Extract text ---
    print(f"  Extracting text ({file_type.upper()})...")
    try:
        if file_type == "pdf":
            extracted = extract_pdf(content_bytes, logger)
        elif file_type == "html":
            extracted = extract_html(content_bytes, logger)
        else:
            extracted = extract_text(content_bytes, logger)
    except Exception as e:
        return {"success": False, "error": str(e)}

    char_count = len(extracted)
    logger.info(f"Extracted {char_count:,} characters")

    # --- Build markdown output ---
    source_label = (
        source if is_url else Path(source).name
    )  # URLs shown in full; local files show name only
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    header_lines = [
        "# Document Analysis",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| **Source** | `{source_label}` |",
        f"| **Type** | {file_type.upper()} |",
        f"| **Extracted** | {char_count:,} characters |",
        f"| **Date** | {now} |",
    ]

    if question:
        header_lines.append(f"| **Question** | {question} |")

    header_lines += ["", "---", "", "## Extracted Content", ""]

    if question:
        header_lines += [
            f"> **Question to answer:** {question}",
            "",
        ]

    markdown = "\n".join(header_lines) + extracted

    return {
        "success": True,
        "markdown": markdown,
        "text": extracted,
        "file_type": file_type,
        "source": source,
        "char_count": char_count,
        "question": question,
    }


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Analyze documents from URL or local file"
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--url", type=str, help="URL of document to analyze")
    source_group.add_argument("--file", type=str, help="Local file path to analyze")

    parser.add_argument(
        "--question",
        type=str,
        help="Specific question to answer about the document",
    )
    parser.add_argument("--output", type=str, help="Custom output file path")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to skill results/ folder",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging",
    )

    args = parser.parse_args()

    is_url = args.url is not None
    source = args.url if is_url else args.file

    print("=" * 60)
    print("DOCUMENT ANALYSIS")
    print(f"   Source: {source[:60]}...")
    if args.question:
        print(f"   Question: {args.question[:60]}")
    if args.debug:
        print("   Debug: Enabled")
    if args.save:
        print("   Save: Results folder")
    print("=" * 60)

    logger = get_logger(debug=args.debug)

    try:
        result = analyze_document(source, is_url, args.question, logger)

        if result["success"]:
            print("\nANALYSIS COMPLETE")
            print("-" * 60)
            print(
                f"Extracted: {result['char_count']:,} characters ({result['file_type'].upper()})"
            )

            # Determine output path
            def _stem(src: str) -> str:
                if src.startswith(("http://", "https://")):
                    url_path = urllib.parse.urlparse(src).path
                    return Path(url_path).stem or "document"
                return Path(src).stem or "document"

            if args.output:
                out_path = Path(args.output)
            elif args.save:
                RESULTS_DIR.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                safe_name = re.sub(r"[^a-zA-Z0-9]", "_", _stem(source)[:40]).strip("_")
                out_path = RESULTS_DIR / f"RAW_{timestamp}_analyze_{safe_name}.md"
            else:
                safe_name = re.sub(r"[^a-zA-Z0-9]", "_", _stem(source)[:40]).strip("_")
                out_path = Path(f"analysis_{safe_name}.md")

            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(result["markdown"], encoding="utf-8")
            print(f"Saved: {out_path}")

            # Preview (encode-safe for Windows cp1252 consoles)
            print("\n--- PREVIEW (first 500 chars) ---")
            preview_text = result["text"][:500].replace("\n", " ")
            safe_preview = preview_text.encode(
                sys.stdout.encoding or "utf-8", errors="replace"
            ).decode(sys.stdout.encoding or "utf-8")
            print(safe_preview + "...")

        else:
            print(f"\nANALYSIS FAILED")
            print(f"Error: {result.get('error')}")
            logger.error(f"Analysis failed: {result.get('error')}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        logger.exception("Unexpected error")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        if logger.debug_enabled and hasattr(logger, "log_file") and logger.log_file:
            print(f"\nDebug log: {logger.log_file}")


if __name__ == "__main__":
    main()
