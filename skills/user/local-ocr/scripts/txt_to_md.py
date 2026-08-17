#!/usr/bin/env python3
"""
Convert raw OCR text to clean markdown.

Post-processes OCR output with a configurable pipeline:
  1. Remove page numbers and running headers
  2. Merge broken lines into proper paragraphs (short-last-line heuristic)
  3. Strip repeating section headers (first-occurrence-keep)
  4. Apply markdown formatting (## headings, etc.)

Usage:
  python3 txt_to_md.py <input.txt> <output.md>
  python3 txt_to_md.py <input.txt> <output.md> --lang zh
  python3 txt_to_md.py <input.txt> <output.md> --config book.yaml
  python3 txt_to_md.py <input.txt> <output.md> --no-auto-detect-headers
"""

import re
import sys
import argparse
from typing import List, Set, Optional


# ── Page number detection ─────────────────────────────────────────────────

def is_page_number(line: str) -> bool:
    """Detect standalone page numbers like '57', '128', 'vi', 'xiv'."""
    stripped = line.strip()
    if not stripped:
        return False
    if re.match(r'^\d{1,4}$', stripped):
        return True
    if re.match(r'^[ivxlcdmIVXLCDM]{1,6}$', stripped):
        return True
    return False


# ── Chapter/section detection ─────────────────────────────────────────────

def is_chapter_heading(line: str) -> bool:
    """Detect clear chapter/section headings (CJK and Latin scripts)."""
    line = line.strip()
    if not line:
        return False
    if re.match(
        r'^(Chapter|CHAPTER|Part|PART|Section|SECTION|第[一二三四五六七八九十百千\d]+[章节部篇])',
        line,
    ):
        return True
    if re.match(r'^\d+\.\d*\s+\w{3,}', line):
        return True
    return False


# ── Line classification heuristics ────────────────────────────────────────

def _compute_median_line_length(lines: List[str]) -> float:
    """Compute the median length of content lines (excluding headers, page numbers)."""
    lengths = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^\d{1,4}$', stripped):
            continue
        if len(stripped) <= 3:
            continue
        lengths.append(len(stripped))

    if not lengths:
        return 30.0  # sensible default

    sorted_lens = sorted(lengths)
    return sorted_lens[len(sorted_lens) // 2]


def _is_short_line(line: str, median_len: float, threshold: float = 0.75) -> bool:
    """Check if a line is significantly shorter than the median — likely a paragraph-end line."""
    stripped = line.strip()
    if not stripped:
        return False
    return len(stripped) < median_len * threshold


_SENTENCE_END_CJK = r'[。！？，、；：》」』）\)]$'
_SENTENCE_END_LATIN = r'[.!?:;"\'»\)]$'


def _is_header_line(line: str, lang: str = "zh") -> bool:
    """Detect lines that are likely section/chapter headers (short, not page numbers)."""
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) > 20:
        return False
    if re.match(r'^\d{1,4}$', stripped):
        return False

    # Very short lines (<=6 chars) ending with sentence-ending punctuation
    # are likely paragraph ends, not headers (e.g., "有用。" in Chinese, "End." in English)
    punct_pattern = _SENTENCE_END_CJK if lang in ("zh", "ja", "cjk") else _SENTENCE_END_LATIN
    if len(stripped) <= 6 and re.search(punct_pattern, stripped):
        return False

    # Lines <=12 chars that aren't page numbers/para-ends are likely headers
    if len(stripped) <= 12:
        return True
    return False


def _is_footnote_line(line: str) -> bool:
    """Detect if a line starts a footnote/reference (circled numbers, digit + CJK)."""
    stripped = line.strip()
    if not stripped:
        return False
    # Circled numbers (Unicode ranges)
    if re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳⓵⓶⓷⓸⓹]', stripped):
        return True
    # Plain digit followed by space and CJK text (OCR-dropped circles)
    # e.g., "1 除了省志..." or "2 国务院知青办..."
    if re.match(r'^\d{1,2}\s+[一-鿿]', stripped):
        return True
    return False


# ── Paragraph merging (short-last-line heuristic) ─────────────────────────

def merge_paragraphs(
    text: str,
    *,
    lang: str = "zh",
    short_threshold: float = 0.75,
    very_short_max: int = 20,
    orphan_merge_max: int = 10,
) -> str:
    """Merge broken OCR lines into proper paragraphs.

    Uses the 'short last line' heuristic — the standard approach for CJK OCR:
      1. Compute the median full-width line length for the document.
      2. Lines significantly shorter than the median are paragraph-ending lines.
      3. After a short line, the next full-width line starts a new paragraph.
      4. Empty lines always act as hard paragraph breaks.
      5. Headers and footnotes are detected and kept as separate blocks.
    """
    lines = text.split('\n')
    median_len = _compute_median_line_length(lines)

    result = []
    para_buffer: List[str] = []
    prev_line_was_short = False

    for line in lines:
        stripped = line.strip()

        # Empty line → hard paragraph break
        if not stripped:
            if para_buffer:
                result.append(''.join(para_buffer))
                para_buffer = []
                prev_line_was_short = False
            result.append('')
            continue

        # Header/section title → standalone
        if _is_header_line(stripped, lang):
            if para_buffer:
                result.append(''.join(para_buffer))
                para_buffer = []
            result.append(stripped)
            prev_line_was_short = True
            continue

        # Footnote start → new paragraph
        if _is_footnote_line(stripped):
            if para_buffer:
                result.append(''.join(para_buffer))
                para_buffer = []
            para_buffer.append(stripped)
            prev_line_was_short = False
            continue

        # Short line analysis
        is_short = _is_short_line(stripped, median_len, short_threshold)
        is_very_short = len(stripped) <= very_short_max

        if prev_line_was_short and not is_short:
            # Previous short line ended a paragraph. Full-width line starts new para.
            if para_buffer:
                result.append(''.join(para_buffer))
                para_buffer = []
        elif is_very_short and para_buffer:
            # Very short lines (subtitles, headers) always start fresh.
            # But if buffer has only one very short line, merge them
            # (handles header+subtitle pairs like "引言" + "上山下乡...")
            if len(para_buffer) == 1 and len(para_buffer[0]) <= very_short_max:
                pass  # two consecutive short lines → likely header + subtitle → merge
            else:
                result.append(''.join(para_buffer))
                para_buffer = []

        para_buffer.append(stripped)
        prev_line_was_short = is_short

    # Don't forget the last paragraph
    if para_buffer:
        result.append(''.join(para_buffer))

    # Post-merge cleanup: merge orphaned short fragments
    # (e.g., single short footnote fragments like "1984 年。" = 7 chars)
    lines2 = '\n'.join(result).split('\n')
    final = []
    i = 0
    while i < len(lines2):
        stripped = lines2[i].strip()
        if stripped and len(stripped) < orphan_merge_max and final and final[-1].strip():
            final[-1] = final[-1] + stripped
            i += 1
            continue
        final.append(lines2[i])
        i += 1

    return '\n'.join(final)


def remove_page_numbers(text: str) -> str:
    """Remove standalone page numbers (lines that are purely a page number)."""
    lines = text.split('\n')
    return '\n'.join(
        line for line in lines if not is_page_number(line)
    )


# ── Running header detection ──────────────────────────────────────────────

def detect_repeating_headers(
    lines: List[str],
    *,
    window: int = 3,
    min_occurrences: int = 5,
    page_ratio: float = 0.3,
) -> Set[str]:
    """Auto-detect lines that repeat across page boundaries (running headers).

    Algorithm:
      1. Find page number candidates (standalone numbers on thin lines).
      2. Collect all lines within ±window of each page break.
      3. Lines appearing near >page_ratio of page breaks (min min_occurrences)
         are classified as running headers.

    Returns a set of stripped header texts to remove.
    """
    if len(lines) < min_occurrences * 2:
        return set()

    # Find page break positions (indices where page numbers appear)
    page_breaks = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if is_page_number(stripped):
            # Verify it looks like a page break: number on a thin line,
            # possibly surrounded by empty/near-empty space
            page_breaks.append(i)

    if len(page_breaks) < min_occurrences:
        return set()

    # Collect lines near page breaks
    from collections import Counter
    candidates = Counter()

    for break_idx in page_breaks:
        for offset in range(-window, window + 1):
            idx = break_idx + offset
            if offset == 0:
                continue  # skip the page number itself
            if 0 <= idx < len(lines):
                stripped = lines[idx].strip()
                if len(stripped) > 3:  # meaningful content
                    candidates[stripped] += 1

    # Lines appearing near >page_ratio of page breaks are running headers
    threshold = max(min_occurrences, int(len(page_breaks) * page_ratio))
    return {line for line, count in candidates.items() if count >= threshold}


def remove_running_headers(
    text: str,
    *,
    config_headers: Optional[List[str]] = None,
    config_pairs: Optional[List[dict]] = None,
    auto_detect: bool = True,
    auto_detect_window: int = 3,
    auto_detect_min: int = 5,
    auto_detect_ratio: float = 0.3,
) -> str:
    """Remove page-level running headers.

    Strategy (priority order):
      1. If config_headers provided: first-occurrence-keep for exact matches
      2. If config_pairs provided: detect adjacent-line pair patterns
      3. If auto_detect=True: run statistical repeating-line detection
    """
    lines = text.split('\n')
    remove_flags = [False] * len(lines)

    # Strategy 1: Config-based exact header matching (first-occurrence-keep)
    if config_headers:
        seen: Set[str] = set()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped in config_headers:
                if stripped not in seen:
                    seen.add(stripped)  # keep first occurrence
                else:
                    remove_flags[i] = True  # remove subsequent occurrences

    # Strategy 2: Config-based paired running headers
    if config_pairs:
        for pair in config_pairs:
            left = pair.get("left", "")
            right_pat = pair.get("right_pattern", "")
            if not left or not right_pat:
                continue
            for i in range(1, len(lines)):
                prev = lines[i - 1].strip()
                curr = lines[i].strip()
                if prev == left and right_pat in curr:
                    remove_flags[i - 1] = True
                    remove_flags[i] = True
                    # Also remove page number before the header
                    if i >= 2 and is_page_number(lines[i - 2]):
                        remove_flags[i - 2] = True
                    elif i >= 3 and lines[i - 2].strip() == '' and is_page_number(lines[i - 3]):
                        remove_flags[i - 3] = True

    # Strategy 3: Auto-detect repeating headers
    if auto_detect:
        repeating = detect_repeating_headers(
            lines,
            window=auto_detect_window,
            min_occurrences=auto_detect_min,
            page_ratio=auto_detect_ratio,
        )
        if repeating:
            seen_auto: Set[str] = set()
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped in repeating:
                    if stripped not in seen_auto:
                        seen_auto.add(stripped)
                    else:
                        remove_flags[i] = True

    # Apply removals
    cleaned = [line for i, line in enumerate(lines) if not remove_flags[i]]
    return '\n'.join(cleaned)


# ── Markdown formatting ───────────────────────────────────────────────────

def apply_markdown(text: str) -> str:
    """Apply markdown formatting: chapter headings, sub-headings, whitespace cleanup."""
    lines = text.split('\n')
    result = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            result.append('')
            continue

        # Chapter/section headings → ##
        if is_chapter_heading(stripped):
            result.append(f'## {stripped}')
            result.append('')
            continue

        # All-caps short lines that look like sub-headings → ###
        if (
            len(stripped) <= 70
            and re.match(r'^[A-Z\s]{3,}$', stripped)
            and len(stripped.split()) >= 2
        ):
            result.append(f'### {stripped.title()}')
            result.append('')
            continue

        # Normal text
        result.append(stripped)

    # Collapse runs of 3+ newlines to 2
    md = '\n'.join(result)
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md


# ── Config loading ────────────────────────────────────────────────────────

def _load_config(path: str) -> dict:
    """Load a YAML or JSON config file. Returns empty dict on failure."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (FileNotFoundError, OSError):
        print(f"WARNING: Config file not found: {path}", file=sys.stderr)
        return {}

    # Try YAML first, then JSON
    try:
        import yaml
        return yaml.safe_load(content) or {}
    except ImportError:
        pass
    except Exception:
        pass

    try:
        import json
        return json.loads(content)
    except Exception:
        print(f"WARNING: Could not parse config file: {path}", file=sys.stderr)
        return {}


def _apply_ocr_corrections(text: str, corrections: Optional[dict]) -> str:
    """Apply OCR error corrections from config (simple string replacements)."""
    if not corrections:
        return text
    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)
    return text


# ── Full pipeline ─────────────────────────────────────────────────────────

def convert_to_md(
    text: str,
    *,
    lang: str = "zh",
    config: Optional[dict] = None,
    auto_detect_headers: bool = True,
) -> str:
    """Full pipeline: clean → merge → strip headers → markdown.

    Args:
        text: Raw OCR text (one recognized line per line).
        lang: Language hint for paragraph merging ('zh', 'ja', 'en', 'auto').
        config: Optional parsed config dict (from YAML/JSON).
        auto_detect_headers: Whether to auto-detect repeating page headers.
    """
    if config is None:
        config = {}

    # Resolve --lang auto using character analysis
    if lang == "auto":
        try:
            import sys as _sys
            _sys.path.insert(0, __file__ and _sys.path[0] or ".")
            from char_analysis import detect_language as _dl
            detected, _ = _dl(text)
            if detected != "unknown":
                lang = detected
        except ImportError:
            pass  # fall through with "auto" → treated as "zh"

    merge_lang = lang if lang in ("zh", "ja", "en") else "zh"

    # Config values
    config_headers = config.get("section_headers")
    config_pairs = config.get("running_header_pairs")
    ocr_corrections = config.get("ocr_corrections")
    merge_params = config.get("merge", {})

    # Step 0: Apply OCR corrections (before any matching)
    text = _apply_ocr_corrections(text, ocr_corrections)

    # Step 1: Remove running headers (config + auto-detect)
    # Must run BEFORE page number removal — the detection algorithm uses
    # page numbers as anchors to locate header lines.
    text = remove_running_headers(
        text,
        config_headers=config_headers,
        config_pairs=config_pairs,
        auto_detect=auto_detect_headers,
    )

    # Step 2: Remove standalone page numbers
    text = remove_page_numbers(text)

    # Step 3: Merge broken lines into paragraphs
    text = merge_paragraphs(
        text,
        lang=merge_lang,
        short_threshold=merge_params.get("short_line_threshold", 0.75),
        very_short_max=merge_params.get("very_short_threshold", 20),
        orphan_merge_max=merge_params.get("orphan_merge_threshold", 10),
    )

    # Step 3: Apply markdown formatting
    text = apply_markdown(text)

    return text


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert raw OCR text to clean markdown",
    )
    parser.add_argument("input", help="Input raw text file")
    parser.add_argument("output", help="Output markdown file")
    parser.add_argument(
        "--lang", default="zh",
        choices=["zh", "ja", "en", "auto"],
        help="Language for paragraph merging heuristics (default: zh, auto: detect from content)",
    )
    parser.add_argument(
        "--config",
        help="Optional YAML/JSON config file with document-specific settings",
    )
    parser.add_argument(
        "--no-auto-detect-headers",
        action="store_true",
        help="Disable auto-detection of repeating page headers",
    )

    args = parser.parse_args()

    # Load config
    config = None
    if args.config:
        config = _load_config(args.config)

    # Override config language with CLI flag if explicitly set
    if config and "lang" in config and args.lang == "zh":
        args.lang = config["lang"]

    with open(args.input, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()

    md = convert_to_md(
        text,
        lang=args.lang,
        config=config,
        auto_detect_headers=not args.no_auto_detect_headers,
    )

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(md)

    # Stats
    orig_chars = len(text)
    new_chars = len(md)
    reduction = (1 - new_chars / orig_chars) * 100 if orig_chars else 0
    print(f"  Converted: {orig_chars} chars → {new_chars} chars markdown (-{reduction:.1f}%)")
    print(f"  Lines: {len(text.split(chr(10)))} → {len(md.split(chr(10)))}")


if __name__ == '__main__':
    main()
