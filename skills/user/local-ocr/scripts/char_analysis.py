#!/usr/bin/env python3
"""
Unicode character analysis for language detection from OCR output.

Zero-dependency, reusable module. Shared by:
  - local-ocr/txt_to_md.py  (--lang auto)
  - soul-collection-extractor/detect_language.py  (batch manga pipeline)

Usage as script:
  echo "こんにちは" | python3 char_analysis.py
  python3 char_analysis.py "这是中文"
  python3 char_analysis.py --file ocr_output.txt
"""

from __future__ import annotations


def is_kana(ch: str) -> bool:
    """Hiragana (U+3040-309F) or Katakana (U+30A0-30FF)."""
    cp = ord(ch)
    return (0x3040 <= cp <= 0x309F) or (0x30A0 <= cp <= 0x30FF)


def is_cjk(ch: str) -> bool:
    """CJK Unified Ideographs (U+4E00-9FFF) and Extension A (U+3400-4DBF)."""
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF)


def is_latin(ch: str) -> bool:
    """ASCII alphabetic characters."""
    return ch.isascii() and ch.isalpha()


def analyze_text(text: str) -> tuple[int, int, int]:
    """Count (kana, cjk, latin) characters in text."""
    kana_count = cjk_count = latin_count = 0
    for ch in text:
        if is_kana(ch):
            kana_count += 1
        elif is_cjk(ch):
            cjk_count += 1
        elif is_latin(ch):
            latin_count += 1
    return kana_count, cjk_count, latin_count


def detect_language(
    text: str | list[str],
) -> tuple[str, float]:
    """Classify text as 'zh', 'ja', 'en', or 'unknown'.

    Accepts a single string or a list of strings (e.g., OCR results from
    multiple images that belong to the same document).

    Returns (language_code, confidence 0.0-1.0).

    先按假名数量和占比判断日文，再判断中文与英文，避免把汉字较多的
    日文误判为中文。低文字量返回 unknown，交由人工复核。
    """
    if isinstance(text, list):
        combined = " ".join(t for t in text if t.strip())
    else:
        combined = text

    if not combined.strip():
        return "unknown", 0.0

    kana_count, cjk_count, latin_count = analyze_text(combined)
    cjk_related = kana_count + cjk_count

    if cjk_related > 0:
        kana_ratio = kana_count / cjk_related

        if kana_count >= 5 and kana_ratio >= 0.12:
            confidence = round(min(0.99, 0.65 + kana_ratio), 3)
            return "ja", confidence
        if cjk_count >= 5:
            confidence = round(min(0.99, 0.65 + cjk_count / cjk_related * 0.3), 3)
            return "zh", confidence

    # Pure Latin → English
    if latin_count > 10:
        return "en", round(min(latin_count / 50, 1.0), 3)

    return "unknown", 0.0


# ── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2 and sys.argv[1] == "--file":
        print("Usage: char_analysis.py [--file] <path>", file=sys.stderr)
        print("       echo 'text' | char_analysis.py", file=sys.stderr)
        print("       char_analysis.py 'some text here'", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) >= 2 and sys.argv[1] == "--file":
        with open(sys.argv[2], "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    elif len(sys.argv) >= 2:
        text = " ".join(sys.argv[1:])
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        text = ""

    if not text.strip():
        print("unknown\t0.0")
        sys.exit(0)

    lang, conf = detect_language(text)
    kana, cjk, latin = analyze_text(text)
    print(f"{lang}\t{conf:.3f}\t(kana={kana}, cjk={cjk}, latin={latin})")
