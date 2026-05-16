#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Fix Windows console encoding
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

"""
gemini_analyze.py — Direct PDF URL analysis via gemini.google.com

Submits a URL (or text query) to gemini.google.com, lets Gemini fetch and
analyze the content directly, and saves the structured response.

First run: Opens browser in visible mode — user logs in to Gemini manually.
Subsequent runs: Uses saved session cookie for headless automation.

Usage:
  python scripts/run.py gemini_analyze.py --url <PDF_URL>
  python scripts/run.py gemini_analyze.py --url <PDF_URL> --save
  python scripts/run.py gemini_analyze.py --url <PDF_URL> --save --debug
  python scripts/run.py gemini_analyze.py --query "分析这个公告" --url <PDF_URL> --save
"""

import sys
import os
import time
import json
import argparse
import re
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from patchright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from browser_utils import BrowserFactory
from config import RESULTS_DIR, PAGE_LOAD_TIMEOUT, BROWSER_PROFILE_DIR
from logger import get_logger

# ── Gemini UI Selectors (may need updating if Google changes UI) ──────────
PROMPT_INPUT_SELECTORS = [
    '[contenteditable="true"][role="textbox"]',
    '[contenteditable="true"]',
    'textarea[aria-label*="prompt" i]',
    'textarea[aria-label*="message" i]',
    'textarea:not([aria-hidden="true"])',
    'div[role="textbox"]',
]

SEND_BUTTON_SELECTORS = [
    'button[aria-label*="send" i]',
    'button[data-test-id="send-button"]',
    'button:has(svg[viewBox*="arrow" i])',
    'button:has(svg[viewBox*="send" i])',
]

STOP_BUTTON_SELECTORS = [
    'button[aria-label*="stop" i]',
    'button:has(svg[viewBox*="square" i])',
]

RESPONSE_ARTICLES_SELECTOR = "article[data-message-id]"
RESPONSE_CONTAINER_SELECTOR = ".response-content, .markdown, .prose"

LOGIN_INDICATORS = [
    "Sign in with Google",
    "Sign in",
    "signin",
    "login",
]

# ── Utilities ────────────────────────────────────────────────────────────


def clean_markdown(text: str) -> str:
    """Post-process: remove Gemini UI noise, empty lines, etc."""
    # Remove "Copy" / "Share" / "Edit" / "Delete" toolbars
    text = re.sub(r"\bCopy\b\s*(?:\n|$)", "", text)
    text = re.sub(r"\bShare\b\s*(?:\n|$)", "", text)
    text = re.sub(r"\bpublic link\b.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bFacebook\b", "", text)
    text = re.sub(r"\bX\b", "", text)
    text = re.sub(r"\bGmail\b", "", text)
    text = re.sub(r"\bReddit\b", "", text)
    text = re.sub(r"\bWhatsApp\b", "", text)
    text = re.sub(r"\bGood response\b", "", text)
    text = re.sub(r"\bBad response\b", "", text)
    text = re.sub(r"\bHelpful\b", "", text)
    text = re.sub(r"\bComprehensive\b", "", text)
    text = re.sub(r"\bOther\b", "", text)
    text = re.sub(r"\bIncorrect\b", "", text)
    text = re.sub(r"\bInappropriate\b", "", text)
    text = re.sub(r"\bNot working\b", "", text)
    text = re.sub(r"\bUnhelpful\b", "", text)
    text = re.sub(r"\bSubmit\b", "", text)
    text = re.sub(r"\bThanks for letting us know\b", "", text)
    # Privacy text
    text = re.sub(r"Google may use account.*", "", text, flags=re.DOTALL)
    # Gemini UI boilerplate: "PDF file ready", "Tools", "Fast", etc.
    text = re.sub(
        r"您的 PDF 文件已准备就绪[：:].*?(?=\n\n|\n#|\Z)", "", text, flags=re.DOTALL
    )
    text = re.sub(r"PDF\s*\n", "", text)
    text = re.sub(r"\nTools\s*\nFast\s*$", "", text)
    text = re.sub(r"\nTools\s*\nFast\s*\n", "\n", text)
    text = re.sub(r"Gemini is AI and can make mistakes\.?", "", text)
    text = re.sub(
        r"Google Search\s*\nQuery successful\s*(?:\nTry again without apps)?", "", text
    )
    # Reduce multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def find_visible(page, selectors: list, timeout: int = 5000) -> Optional[Any]:
    """Find first visible element matching any selector."""
    deadline = time.time() + timeout / 1000
    while time.time() < deadline:
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    return el
            except:
                continue
        time.sleep(0.2)
    return None


# ── Main Scraper ─────────────────────────────────────────────────────────


class GeminiAnalyzer:
    def __init__(self, headless: bool = True, logger=None):
        self.headless = headless
        self.logger = logger or get_logger(debug=False)
        self.pw = None
        self.ctx = None
        self.page = None

    def start(self):
        self.pw = sync_playwright().start()
        factory = BrowserFactory()
        self.ctx = factory.launch_persistent_context(self.pw, headless=self.headless)
        self.page = self.ctx.new_page()
        self.logger.info("Browser started")

    def stop(self):
        try:
            if self.page:
                self.page.close()
        except:
            pass
        try:
            if self.ctx:
                self.ctx.close()
        except:
            pass
        try:
            if self.pw:
                self.pw.stop()
        except:
            pass

    def is_logged_in(self) -> bool:
        """Check if user has a Gemini session."""
        # Navigate to gemini
        self.page.goto(
            "https://gemini.google.com",
            wait_until="domcontentloaded",
            timeout=PAGE_LOAD_TIMEOUT,
        )
        time.sleep(3)

        # Look for the prompt input — if present, we're logged in
        input_el = find_visible(self.page, PROMPT_INPUT_SELECTORS, timeout=8000)
        if input_el:
            self.logger.info("Gemini session detected — already logged in")
            return True

        # Check for login wall
        body = (self.page.inner_text("body") or "").lower()
        if any(ind in body for ind in ["sign in", "login"]):
            self.logger.warning("Login required")
            return False

        # Check if we're on gemini but not logged in
        if "gemini" in self.page.url and "sign" in body:
            return False

        # Try the more robust check: wait for input
        try:
            self.page.wait_for_selector('[contenteditable="true"]', timeout=5000)
            return True
        except:
            pass

        return False

    def login_interactive(self):
        """Open browser headed so user can log in manually."""
        self.logger.info("=" * 60)
        self.logger.info("LOGIN REQUIRED")
        self.logger.info("=" * 60)
        self.logger.info(
            "Opening Gemini in visible mode. Please log in with your Google account."
        )
        self.logger.info("Press ENTER in the terminal after logging in to continue...")

        # Re-launch headed
        self.stop()
        self.headless = False
        self.pw = sync_playwright().start()
        factory = BrowserFactory()
        self.ctx = factory.launch_persistent_context(self.pw, headless=False)
        self.page = self.ctx.new_page()
        self.page.goto(
            "https://gemini.google.com", wait_until="load", timeout=PAGE_LOAD_TIMEOUT
        )
        input("Press ENTER after logging in to Gemini...")

        # Now re-launch in original headless mode
        self.stop()
        self.headless = True
        self.pw = sync_playwright().start()
        factory = BrowserFactory()
        self.ctx = factory.launch_persistent_context(self.pw, headless=self.headless)
        self.page = self.ctx.new_page()
        self.logger.info("Session saved — proceeding headless")

    def submit_query(self, query: str, url: str = "") -> str:
        """Submit a query (with optional URL) to Gemini and extract response."""
        # Construct the full prompt
        full_prompt = query
        if url:
            if query:
                full_prompt = f"{query}\n\n{url}"
            else:
                full_prompt = (
                    f"Please read and analyze the content from this URL: {url}"
                )

        self.logger.info(f"Navigating to gemini.google.com...")
        self.page.goto(
            "https://gemini.google.com",
            wait_until="domcontentloaded",
            timeout=PAGE_LOAD_TIMEOUT,
        )
        time.sleep(3)

        # Check for login
        if not self.is_logged_in():
            self.login_interactive()
            self.page.goto(
                "https://gemini.google.com",
                wait_until="domcontentloaded",
                timeout=PAGE_LOAD_TIMEOUT,
            )
            time.sleep(2)

        # Start a fresh conversation
        self.logger.info("Starting new conversation...")
        self.page.goto(
            "https://gemini.google.com",
            wait_until="domcontentloaded",
            timeout=PAGE_LOAD_TIMEOUT,
        )
        time.sleep(3)

        # Dismiss any overlays/popups (e.g., "Supercharge Gemini" banner)
        try:
            overlay = self.page.query_selector(".cdk-overlay-container")
            if overlay and overlay.is_visible():
                self.logger.info("Dismissing overlay popup...")
                # Try Escape key first
                self.page.keyboard.press("Escape")
                time.sleep(1)
                # If still there, try clicking outside
                if overlay and overlay.is_visible():
                    self.page.mouse.click(10, 10)
                    time.sleep(1)
        except:
            pass

        # Find prompt input
        input_el = find_visible(self.page, PROMPT_INPUT_SELECTORS, timeout=10000)
        if not input_el:
            self.logger.error(
                "Could not find Gemini prompt input — UI may have changed"
            )
            return "ERROR: Could not find prompt input"

        self.logger.info(f"Typing query ({len(full_prompt)} chars)...")

        # Use fill() directly (doesn't require click-ability)
        try:
            input_el.fill(full_prompt)
        except:
            # Fallback: click then type
            try:
                self.page.keyboard.press("Escape")
                time.sleep(0.5)
                input_el.click()
                input_el.fill(full_prompt)
            except:
                input_el.type(full_prompt, delay=10)

        # Wait a moment for any auto-suggestions
        time.sleep(0.5)

        # Find and click send button
        send_btn = find_visible(self.page, SEND_BUTTON_SELECTORS, timeout=5000)
        if send_btn:
            send_btn.click()
        else:
            # Try Enter key
            input_el.press("Enter")

        self.logger.info("Waiting for Gemini response...")

        # ── Wait for response to complete ──
        response_text = ""
        max_wait = 180  # max 3 minutes for long PDF analysis
        deadline = time.time() + max_wait

        # Phase 1: Wait for stop button to appear (generation started)
        generation_started = False
        while time.time() < deadline and not generation_started:
            time.sleep(0.5)
            stop_btn = find_visible(self.page, STOP_BUTTON_SELECTORS, timeout=1000)
            if stop_btn:
                generation_started = True
                self.logger.info("Generation started (stop button visible)")
            else:
                # Check if response content is already appearing
                try:
                    body = self.page.inner_text("body")
                    if len(body) > 2000 and "Gemini said" in body:
                        generation_started = True
                        self.logger.info("Response already visible (text detected)")
                        break
                except:
                    pass

        if not generation_started:
            self.logger.warning(
                "No stop button appeared — response may have already completed or failed"
            )

        # Phase 2: Wait for stop button to disappear OR stable text length
        prev_length = 0
        stable_count = 0
        while time.time() < deadline:
            time.sleep(0.5)
            stop_btn = find_visible(self.page, STOP_BUTTON_SELECTORS, timeout=1000)
            if not stop_btn:
                time.sleep(2)
                # Double-check: stop button still gone?
                stop_btn2 = find_visible(self.page, STOP_BUTTON_SELECTORS, timeout=1000)
                if not stop_btn2:
                    self.logger.info("Generation complete (stop button gone)")
                    break

            # Also detect by text stability (content stops growing)
            try:
                body = self.page.inner_text("body")
                cur_len = len(body)
                if cur_len == prev_length and prev_length > 500:
                    stable_count += 1
                    if stable_count >= 4:  # 2 seconds of stable content
                        self.logger.info("Generation complete (content stable)")
                        break
                else:
                    stable_count = 0
                prev_length = cur_len
            except:
                pass

        if not generation_started:
            self.logger.warning(
                "No stop button appeared — response may have already completed or failed"
            )

        # Phase 2: Wait for stop button to disappear (generation complete)
        while time.time() < deadline:
            time.sleep(0.5)
            stop_btn = find_visible(self.page, STOP_BUTTON_SELECTORS, timeout=1000)
            if not stop_btn:
                # No stop button: generation likely complete
                time.sleep(2)  # extra settle time
                self.logger.info("Generation complete (stop button gone)")
                break

        # ── Extract response ──
        response_text = self._extract_response()
        if not response_text:
            # Try an alternative extraction
            response_text = self._extract_response_v2()

        return response_text

    def _extract_response(self) -> str:
        """Extract ONLY the Gemini response (not sidebar/header noise)."""
        try:
            body = self.page.inner_text("body")

            # Method 1: Split on "Gemini said" — most reliable
            if "Gemini said" in body:
                parts = body.split("Gemini said")
                text = parts[-1]
                # Remove trailing UI elements
                for tag in ["Tools", "Fast", "Good response", "Bad response"]:
                    if tag in text:
                        text = text.split(tag)[0]
                cleaned = clean_markdown(text)
                if len(cleaned) > 100:
                    self.logger.info(
                        f"Extracted {len(cleaned)} chars after 'Gemini said'"
                    )
                    return cleaned

            # Method 2: JS extraction targeting conversation content
            script = """
            () => {
                const all = document.querySelectorAll('[data-message-id], article');
                if (all.length === 0) return '';
                const articles = Array.from(all);
                // Take the last response (skip user query)
                for (let i = articles.length - 1; i >= 0; i--) {
                    const text = articles[i].innerText || '';
                    if (text.length > 100 && !text.startsWith('Sign in') && !text.includes('You said')) {
                        return text;
                    }
                }
                return articles[articles.length - 1]?.innerText || '';
            }
            """
            text = self.page.evaluate(script)
            cleaned = clean_markdown(text)
            if len(cleaned) > 100:
                self.logger.info(f"Extracted {len(cleaned)} chars via JS")
                return cleaned

            # Method 3: Raw body as last resort
            cleaned = clean_markdown(body)
            self.logger.info(f"Fallback body: {len(cleaned)} chars")
            return cleaned
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            return ""

    def _extract_response_v2(self) -> str:
        """Alternative: get all article content from main area."""
        script = """
        () => {
            const main = document.querySelector('main') || document.querySelector('[role="main"]');
            if (!main) return document.body.innerText;
            return main.innerText;
        }
        """
        try:
            text = self.page.evaluate(script)
            return clean_markdown(text)
        except Exception as e:
            self.logger.error(f"V2 extraction failed: {e}")
            return ""

    def _extract_response_v2(self) -> str:
        """Alternative extraction: use JavaScript to get Gemini response."""
        script = """
        () => {
            // Try to get conversation turns
            const articles = document.querySelectorAll('article');
            if (articles.length > 0) {
                return Array.from(articles).map(a => a.innerText).filter(Boolean).join('\n\n---\n\n');
            }
            // Try message containers
            const messages = document.querySelectorAll('[data-message-id], .message-content, .conversation-turn');
            if (messages.length > 0) {
                return Array.from(messages).map(m => m.innerText).filter(Boolean).join('\n\n---\n\n');
            }
            return document.body.innerText;
        }
        """
        try:
            text = self.page.evaluate(script)
            return clean_markdown(text)
        except Exception as e:
            self.logger.error(f"V2 extraction failed: {e}")
            return ""


# ── CLI ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Gemini PDF URL Analyzer")
    parser.add_argument("--url", type=str, help="URL of PDF/document to analyze")
    parser.add_argument("--text-file", type=str, help="Path to pre-extracted text file (use instead of --url when Gemini cannot fetch the URL directly)")
    parser.add_argument(
        "--query",
        type=str,
        default="请仅根据你读取的这份文件的内容回复，不要使用任何外部知识或搜索其他资料。提取文件中的关键信息，结构化格式，包含具体数字。",
        help="Custom query prompt (default: file-only analysis)",
    )
    parser.add_argument("--output", type=str, help="Custom output file path")
    parser.add_argument(
        "--save", action="store_true", help="Save to skill results/ folder"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in visible mode (use for first-time login)",
    )
    args = parser.parse_args()

    if not args.url and not args.text_file:
        print("Error: --url or --text-file is required")
        sys.exit(1)

    logger = get_logger(debug=args.debug)

    # Build query: if --text-file given, embed file contents directly in prompt
    query = args.query
    url_for_submit = args.url or ""
    if args.text_file:
        text_path = Path(args.text_file)
        if not text_path.exists():
            print(f"Error: text file not found: {args.text_file}")
            sys.exit(1)
        with open(text_path, "r", encoding="utf-8") as f:
            file_text = f.read()
        # Strip the metadata header if it's a RAW_ output from analyze.py
        if "## Extracted Content" in file_text:
            file_text = file_text.split("## Extracted Content")[1].strip()
        # Truncate to avoid Gemini input limits (~30k chars safe)
        if len(file_text) > 28000:
            file_text = file_text[:28000] + "\n\n[...内容过长，已截断]"
        query = f"{args.query}\n\n以下是文件内容：\n\n{file_text}"
        url_for_submit = ""  # text already embedded, no URL needed
        logger.info(f"Gemini Analyze — text-file: {args.text_file} ({len(file_text)} chars)")
    else:
        logger.info(f"Gemini Analyze — URL: {args.url}")

    analyzer = GeminiAnalyzer(headless=not args.headed, logger=logger)

    try:
        analyzer.start()
        result = analyzer.submit_query(query=query, url=url_for_submit)

        if result.startswith("ERROR:"):
            print(f"\nFAILED: {result}")
            sys.exit(1)

        # Extract date from URL or text-file name (HKEX pattern: .../sehk/YYYY/MMDD/...)
        ann_date = ""
        url = args.url or args.text_file or ""
        m = re.search(r"/sehk/(\d{4})/(\d{2})(\d{2})/", url)
        if not m:
            m = re.search(r"(\d{4})(\d{2})(\d{2})", url)
        if m:
            ann_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

        # Extract title from Gemini response for filename
        title = ""
        for line in result.split("\n"):
            line = line.strip()
            if line and len(line) > 8:
                if not any(
                    skip in line
                    for skip in ["---", "```", "**", "##", "://", "Export to", "Tools"]
                ):
                    title = line.strip(" .,;:!?（）()《》「」")
                    break
        m = re.search(r"《([^》]+)》", result)
        if m:
            title = m.group(1)
        if not title or len(title) < 4:
            title = "Unknown"

        safe_title = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]", "_", title[:30]).strip("_")

        # ── Save result ──
        if args.output:
            out_path = Path(args.output)
        elif args.save:
            RESULTS_DIR.mkdir(exist_ok=True)
            time_str = datetime.now().strftime("%H-%M-%S")
            date_part = f"{ann_date}_" if ann_date else ""
            out_path = (
                RESULTS_DIR
                / f"GEMINI_{date_part}{time_str}_{safe_title}-Gemini-Summary.md"
            )
        else:
            out_path = Path(f"GEMINI_{safe_title}-Gemini-Summary.md")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"\nSaved: {out_path}")
        print(f"\n{'=' * 60}")
        print("GEMINI ANALYSIS RESULT")
        print(f"{'=' * 60}")
        print(result[:2000] + ("\n..." if len(result) > 2000 else ""))
        print(f"\n{'=' * 60}")
        print(f"Total: {len(result)} chars → {out_path}")

    finally:
        analyzer.stop()


if __name__ == "__main__":
    main()
