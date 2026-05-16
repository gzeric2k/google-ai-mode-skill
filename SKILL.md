---
name: google-ai-mode-skill
description: Use this skill when the user provides a file path or URL (PDF, HTML, TXT) and asks you to read, extract, summarize, or analyze its contents. Use gemini_analyze.py for AI-generated summaries and analysis; use analyze.py for raw text extraction only.
---

# Google AI Mode Skill

Extract and analyze document content from URLs or local files, with optional Gemini AI summarization.

## When to Use This Skill

Trigger this skill when the user:
- Provides a PDF/HTML/text URL and asks for a summary, analysis, or key information → use `gemini_analyze.py`
- Asks to extract raw text from a file for further manual analysis → use `analyze.py`
- Shares a HKEX announcement URL and asks about financial data → use `gemini_analyze.py`

## Script Selection Guide

| Need | Script |
|------|--------|
| AI-generated summary with insights | `gemini_analyze.py` |
| Raw text extraction only (no AI) | `analyze.py` |

---

## Gemini AI Analysis (`gemini_analyze.py`)

Submits a document URL to `gemini.google.com`. Gemini fetches the document, reads it, and returns a structured AI-generated analysis. **Requires Google account login on first use.**

### Usage

```bash
# Analyze with default prompt (structured key info extraction)
python scripts/run.py gemini_analyze.py --url "https://example.com/doc.pdf" --save

# Analyze with custom prompt
python scripts/run.py gemini_analyze.py --url "https://example.com/doc.pdf" --query "总结财务数据" --save

# First-time login (opens visible browser)
python scripts/run.py gemini_analyze.py --url "https://..." --headed --save

# With debug logging
python scripts/run.py gemini_analyze.py --url "https://..." --save --debug
```

### Flags

| Flag | Description |
|------|-------------|
| `--url <url>` | URL of document for Gemini to fetch and analyze (required) |
| `--query "..."` | Custom prompt sent to Gemini (default: extract key info, structured format, specific numbers) |
| `--save` | Save to `results/` with timestamp |
| `--output <path>` | Custom output file path |
| `--headed` | Open browser visibly — required for first-time Google login |
| `--debug` | Enable verbose logging to `logs/` |

### First-time Login

Gemini requires a Google account session. On first use:

```bash
# Option A: login helper (keeps session alive)
python scripts/run.py gemini_login.py

# Option B: run analysis directly in headed mode
python scripts/run.py gemini_analyze.py --url "https://..." --headed --save
```

After login, the session is saved in the persistent browser profile — future runs work headlessly without re-login.

### Default Query Prompt

If `--query` is omitted, Gemini is instructed to:
> 请仅根据你读取的这份文件的内容回复，不要使用任何外部知识或搜索其他资料。提取文件中的关键信息，结构化格式，包含具体数字。

### Workflow

1. Run `gemini_analyze.py --url <url> --save`
2. Gemini fetches the document, generates structured analysis
3. Result saved to `results/GEMINI_<date>_<title>-Gemini-Summary.md`
4. Claude Code reads the saved file and presents findings

### Example (HKEX announcement)

```bash
python scripts/run.py gemini_analyze.py \
  --url "https://www1.hkexnews.hk/listedco/listconews/sehk/2025/1027/2025102701067_c.pdf" \
  --save --debug
```

---

## Raw Text Extraction (`analyze.py`)

Extracts raw text from documents without AI analysis. Supports PDF, HTML, and plain text. No browser or login required.

### Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Text extraction via pdfplumber. Scanned/image PDFs not supported. |
| HTML | `.html`, `.htm` | Extracts readable text, strips scripts/nav/footer. |
| Plain text | `.txt`, `.md`, `.csv` | Direct read with encoding auto-detection. |

### Usage

```bash
# Extract from URL
python scripts/run.py analyze.py --url "https://example.com/doc.pdf" --save

# Extract local file with embedded question header
python scripts/run.py analyze.py --file report.pdf --question "Key financial metrics?" --save
```

### Flags

| Flag | Description |
|------|-------------|
| `--url <url>` | URL of document to fetch and extract |
| `--file <path>` | Local file path to extract |
| `--question "..."` | Question to embed as context header in output |
| `--save` | Save to `results/` with timestamp |
| `--output <path>` | Custom output file path |
| `--debug` | Enable verbose logging to `logs/` |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Use `run.py` wrapper, never execute scripts directly |
| Gemini not logged in | Run `gemini_login.py` or use `--headed` flag |
| Gemini session expired | Re-run `gemini_login.py` to refresh session |
| PDF text empty | File may be scanned/image-only — use `gemini_analyze.py` instead (Gemini handles OCR) |
| Need detailed logs | Use `--debug` flag — log saved to `logs/` folder |

**Exit Codes:**
- `0` - Success
- `1` - General error
- `130` - User interrupted (Ctrl+C)
