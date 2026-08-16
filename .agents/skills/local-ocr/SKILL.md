---
name: local-ocr
description: Local image/PDF OCR using Apple Vision (macOS native) with Core Image preprocessing. Three primary tasks — (1) single image OCR, (2) full PDF to Markdown with paragraph merging and auto header/footer removal, (3) manga/comic language detection via CJK character analysis. Entirely local, free, private — no API calls. When you need to OCR an image, extract text from a PDF, convert a PDF to markdown, recognize text in screenshots, or detect language of manga/comic images, use this skill. For complex image understanding (diagram interpretation, design critique, formula→LaTeX), use image-reader (cloud VLM) instead. Triggers: OCR, extract text, PDF to text/markdown, read PDF, convert scanned PDF, image recognition, local OCR, language detection, Chinese vs Japanese.
---

# Local OCR — Image & PDF Text Recognition

Entirely local OCR pipeline. Uses a self-maintained Swift tool (`~/Applications/local-ocr/ocr_vision`) wrapping Apple Vision with Core Image preprocessing. No Shortcuts dependency. No API costs. No data leaving the machine.

## Quick Reference

| Task | Tool | Command |
|------|------|---------|
| OCR single image | `ocr_vision` | `~/Applications/local-ocr/ocr_vision <img> [en\|zh\|ja\|cjk\|auto] [--raw\|--enhance]` |
| Detect PDF type | `pdf_detect.sh` | `~/Applications/local-ocr/scripts/pdf_detect.sh <pdf>` |
| PDF → Markdown | `pdf_to_md.sh` | `~/Applications/local-ocr/scripts/pdf_to_md.sh <pdf> [outdir] [--lang=zh] [--workers=N]` |
| Clean OCR text | `txt_to_md.py` | `python3 ~/Applications/local-ocr/scripts/txt_to_md.py <in> <out> [--lang=zh] [--config cfg.yaml]` |
| Detect text language | `char_analysis.py` | `python3 ~/Applications/local-ocr/scripts/char_analysis.py <text>` |
| Batch manga lang detect | `manga-collection-manager` | Use `detect_language.py` in that skill |
| Text cleanup (zh) | `opencc` | `opencc -c t2s` |

## When to Use What

| Tool | Strengths | Use for |
|------|-----------|---------|
| **local-ocr** (this skill) | Local, free, private, fast, concurrent | Bulk text extraction: PDFs, document scans, manga batches, screenshots |
| **image-reader** (cloud VLM) | Semantic understanding, reasoning | Diagram interpretation, design critique, formula→LaTeX, error diagnosis, table extraction |

**Rule of thumb**: If you just need the text → local-ocr. If you need to *understand* the image → image-reader.

For single images that need both text and structure: OCR first with `ocr_vision`, then if the raw text needs structural interpretation, pass to image-reader `--mode extract`.

---

## Task 1: Single Image OCR

Extract text from a single image file (PNG, JPEG, etc.).

### Basic Usage

```bash
# English (default)
~/Applications/local-ocr/ocr_vision image.png

# Chinese
~/Applications/local-ocr/ocr_vision image.png zh

# Japanese
~/Applications/local-ocr/ocr_vision image.png ja

# Screenshot / digital image — skip preprocessing
~/Applications/local-ocr/ocr_vision image.png --raw
```

### Language Modes

Apple Vision's `recognitionLanguages` is a **priority hint**, not a hard filter. Choosing the right hint dramatically affects CJK accuracy.

| Mode | `recognitionLanguages` | Use Case |
|------|------------------------|----------|
| `en` | `["en-US", "zh-Hans"]` | English text with occasional Chinese (default) |
| `zh` | `["zh-Hans", "zh-Hant", "en-US"]` | Chinese (simplified + traditional) |
| `ja` | `["ja-JP", "en-US"]` | Japanese text |
| `cjk` | `["zh-Hans", "zh-Hant", "ja-JP", "en-US"]` | **Language detection** — all CJK in one pass |
| `auto` | `[]` (system preferred languages) | Vision auto-detection. **Not recommended for CJK** — tends to default to Latin script |

### Preprocessing Modes

| Mode | Pipeline | Best for |
|------|----------|----------|
| `--full` (default) | Scale → Document Enhancer → Contrast ×1.15 → Sharpen 0.3 | Scanned documents, photos |
| `--enhance` | Scale → Document Enhancer → Contrast ×1.15 | Cleaner scans |
| `--raw` | Scale only | Screenshots, digital images |

All modes scale images to ≤2400px on the larger dimension (Lanczos resampling) before OCR. `--raw` skips enhancement filters but still scales for performance.

---

## Task 2: Full PDF to Markdown

Convert an entire PDF to clean markdown, handling both text-based and image-based (scanned) PDFs.

### Pipeline Overview

```
PDF → pdf_detect.sh (classify)
        ├─ text-based → pdftotext -layout → raw text
        └─ image-based → pdftoppm (page images) → 10-way concurrent OCR → combined text
      → txt_to_md.py (clean: remove headers/页码 → merge paragraphs → markdown)
      → output.md
```

### Step 1: Quick PDF Check (before full conversion)

```bash
# Determine PDF type
~/Applications/local-ocr/scripts/pdf_detect.sh "file.pdf"
# exit 0 → text-based (pdftotext can extract)
# exit 1 → image-based (needs page-by-page OCR)

# For text PDFs: spot-check a page
pdftotext -f 20 -l 20 "file.pdf" - | head -20
```

### Step 2: Full Conversion

```bash
# Basic: Chinese PDF (default language = zh)
~/Applications/local-ocr/scripts/pdf_to_md.sh "file.pdf"

# Specify output directory and language
~/Applications/local-ocr/scripts/pdf_to_md.sh "file.pdf" /output/dir --lang=ja

# Adjust concurrency (default: 10 workers)
~/Applications/local-ocr/scripts/pdf_to_md.sh "file.pdf" --workers=5
```

**Note**: Default language is `zh` (Chinese). For English PDFs, always pass `--lang=en`.

### Step 3: Post-Processing with txt_to_md.py

If the PDF is already extracted to raw text, you can run the post-processor directly:

```bash
python3 ~/Applications/local-ocr/scripts/txt_to_md.py raw_text.txt output.md --lang=zh
```

**What it does**:
1. **Auto-detect repeating headers** — finds lines that repeat across page boundaries and removes duplicates beyond the first occurrence. No configuration needed for common cases.
2. **Remove standalone page numbers** — Arabic (1-9999) and Roman numerals (i, vii, xiv).
3. **Merge broken lines into paragraphs** — uses the "short last line" heuristic. Computes the median line length for the document; lines significantly shorter (<75% of median) are paragraph-ending lines.
4. **Apply markdown formatting** — chapter headings get `##`, all-caps sub-headings get `###`.

**Optional config file** for document-specific tuning:

```yaml
# config.yaml — all fields optional
lang: zh

# Known section headers (first occurrence kept as title, subsequent stripped)
section_headers:
  - "引言"
  - "参考文献"

# Adjacent-line running header pairs to detect and remove
running_header_pairs:
  - left: "Book Title"
    right_pattern: "Chapter Subtitle"

# Common OCR error corrections (applied before all matching)
ocr_corrections:
  "common_misread": "correct_text"

# Paragraph merging overrides
merge:
  short_line_threshold: 0.75
  very_short_threshold: 20
  orphan_merge_threshold: 10
```

```bash
python3 ~/Applications/local-ocr/scripts/txt_to_md.py in.txt out.md --config book.yaml
```

Disable auto header detection if it produces false positives:

```bash
python3 ~/Applications/local-ocr/scripts/txt_to_md.py in.txt out.md --no-auto-detect-headers
```

### Performance

| PDF Type | 300 pages | Bottleneck |
|----------|-----------|------------|
| Text-based | ~5 seconds | pdftotext is near-instant |
| Image with OCR layer | ~5 seconds | Same (pdftotext extracts embedded text) |
| Pure image (serial) | ~12 minutes | ~2.4s per page OCR |
| Pure image (10-workers) | ~3 minutes | 10-way concurrency, ANE-bound |

**Tested on**: Apple M5 Mac, macOS 25.5.0, 200 DPI. Your results will vary by chip generation, DPI, and print quality.

### Minimizing LLM Calls

The pipeline is entirely local. Only involve Codex for:
- Targeted OCR cleanup on specific problematic sections
- Complex structural formatting (tables, poetry)
- Translation after extraction

Use `opencc` for Chinese simplified↔traditional conversion — no LLM needed.

---

## Task 3: Manga/Comic Language Detection

Determine whether manga/doujin images contain Chinese, Japanese, or English text. Used to classify mixed-language collections.

### Approach

1. OCR images with `cjk` mode (all CJK languages in one pass, `--raw` since manga pages are digital)
2. Analyze OCR output with Unicode character statistics
3. Classify by heuristic: kana ratio vs CJK count

### Single Image Check

```bash
# OCR a manga page with CJK mode
~/Applications/local-ocr/ocr_vision page01.jpg cjk --raw

# Detect language from the OCR output
~/Applications/local-ocr/ocr_vision page01.jpg cjk --raw | python3 ~/Applications/local-ocr/scripts/char_analysis.py
```

### The Algorithm

```
CJK >= 20              → Chinese (definitive — Japanese needs proportional kana)
kana/(kana+CJK) > 30%  → Japanese (grammar particles present)
CJK >= 5, low kana     → Chinese (lower confidence)
Latin > 10, no CJK     → English
otherwise              → unknown / low_text
```

**Why it works**: Japanese cannot be written without hiragana (grammar particles). A Chinese scanlation has dozens of CJK characters (translated dialog) with only a handful of kana (untranslated SFX like "あっ", "ドン"). Occasional "の" in Chinese scanlations won't trigger false Japanese — the threshold requires ≥3 kana AND >30% ratio.

### Batch Pipeline

For processing entire collections (hundreds of directories), use the `manga-collection-manager` skill:

```bash
cd ~/.agents/skills/manga-collection-manager
uv run python3 scripts/detect_language.py --dryrun   # preview
uv run python3 scripts/detect_language.py --workers 16  # full run
```

This script samples 5 images per directory, OCRs them concurrently, classifies language, and writes a CSV report. Uses image-level OCR caching for instant re-runs.

The language detection primitives (`is_kana`, `is_cjk`, `analyze_text`, `detect_language`) are in `~/Applications/local-ocr/scripts/char_analysis.py` — a zero-dependency module shared by both skills.

---

## ocr_vision Tool Reference

### Why Our Own Tool (not Shortcuts)

1. **Concurrency**: Shortcuts is single-task GUI app. Our Swift binary is a standalone process; 5-way concurrency gives 3.6× speedup.
2. **Preprocessing pipeline**: Shortcuts applies undocumented preprocessing. We replicate it explicitly and lock `VNRecognizeTextRequestRevision3`.
3. **Deterministic**: Behavior won't change with macOS updates.
4. **Debuggable**: Source at `Sources/ocr_vision.swift`.

### Preprocessing Pipeline

```
Raw Image
  │
  ├─→ CILanczosScaleTransform   → scale to ≤2400px (save compute)
  ├─→ CIDocumentEnhancer        → Apple's scanned-document filter
  ├─→ CIColorControls           → contrast ×1.15
  ├─→ CISharpenLuminance        → light sharpen (edges)
  │
  ▼
VNImageRequestHandler → VNRecognizeTextRequest (.accurate, Revision3)
```

Apple Vision does **no internal preprocessing** (confirmed by Apple engineer). All enhancement is explicit and controllable.

### Complete Usage

```bash
# English (default)
~/Applications/local-ocr/ocr_vision image.png

# Chinese, full preprocessing
~/Applications/local-ocr/ocr_vision image.png zh

# Japanese
~/Applications/local-ocr/ocr_vision image.png ja

# CJK combined — for language detection
~/Applications/local-ocr/ocr_vision image.png cjk --raw

# Skip preprocessing (screenshots/digital images)
~/Applications/local-ocr/ocr_vision image.png --raw

# English, no preprocessing
~/Applications/local-ocr/ocr_vision image.png en --raw
```

Position between language and option flags is flexible. Unknown arguments produce a stderr warning.

---

## Installation / Build

### Dependencies

```bash
brew install poppler ghostscript opencc
```

### Compile the OCR Tool

```bash
cd ~/Applications/local-ocr
swiftc -O -o ocr_vision Sources/ocr_vision.swift
```

### Directory Structure

```
~/Applications/local-ocr/
├── Sources/
│   └── ocr_vision.swift         # Source code (readable, modifiable)
├── ocr_vision                    # Compiled binary
└── scripts/
    ├── ocr_image.sh              # Single image OCR wrapper
    ├── pdf_detect.sh             # PDF type detection
    ├── pdf_to_md.sh              # Full PDF→Markdown pipeline
    ├── txt_to_md.py              # Text→Markdown post-processor
    └── char_analysis.py          # Language detection primitives
```

---

## Notes

- **Temp files**: Always use a subfolder under `/tmp/` — `mktemp -d /tmp/Codex-ocr-XXXXXX` with `trap "rm -rf ..." EXIT`. Never dump files directly in `/tmp/`.
- **Concurrency**: Default 10 OCR workers in `pdf_to_md.sh`. Override with `--workers=N`.
- **Encrypted PDFs** cannot be processed — check with `pdfinfo` first.
- **Revision lock**: `VNRecognizeTextRequestRevision3` is pinned; OS-upgrade behavior changes are prevented.
- **Scale always applied**: Even in `--raw` mode, images >2400px are downscaled (Lanczos). This is by design for performance.
