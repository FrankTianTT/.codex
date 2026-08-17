#!/bin/bash
# Convert a PDF to markdown — auto-detects type, handles both text and image PDFs
# Usage: pdf_to_md.sh <pdf_path> [output_dir] [--lang=en|zh|ja|cjk|auto] [--workers=N]
#
# For image-based PDFs: extracts pages → OCR with N concurrent workers
# Default: zh language, 10 workers

set -euo pipefail

OCR_LANG="zh"     # default language (Chinese)
CONCURRENT=10     # default workers
POS_ARGS=()

# ── Argument parsing ───────────────────────────────────────────────────────

for arg in "$@"; do
    case "$arg" in
        --workers=*)  CONCURRENT="${arg#*=}" ;;
        --lang=*)     OCR_LANG="${arg#*=}" ;;
        --*)          echo "WARNING: Unknown flag: $arg" >&2 ;;
        *)            POS_ARGS+=("$arg") ;;
    esac
done

if [ "${#POS_ARGS[@]}" -lt 1 ]; then
    echo "Usage: pdf_to_md.sh <pdf_path> [output_dir] [--lang=...] [--workers=N]" >&2
    exit 2
fi

PDF="${POS_ARGS[0]}"
OUTDIR="${POS_ARGS[1]:-/tmp/Codex-ocr-output}"

if [ ! -f "$PDF" ]; then
    echo "ERROR: PDF not found: $PDF" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OCR_BIN="$SCRIPT_DIR/../bin/ocr_vision"
PDF_NAME=$(basename "$PDF" .pdf)

case "$CONCURRENT" in
    ''|*[!0-9]*|0) echo "ERROR: --workers must be a positive integer" >&2; exit 2 ;;
esac

# ── Temp directory (subfolder under /tmp, not polluting /tmp root) ──────────

TMPDIR=$(mktemp -d /tmp/Codex-ocr-XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

mkdir -p "$OUTDIR/$PDF_NAME"

echo "=== Processing: $PDF_NAME ==="
echo "  Temp:   $TMPDIR"
echo "  Output: $OUTDIR/$PDF_NAME"
echo "  Lang:   $OCR_LANG"

# ── Step 1: Detect PDF type ─────────────────────────────────────────────────

DETECT_RESULT=$("$SCRIPT_DIR/pdf_detect.sh" "$PDF" 2>&1) || true
PDF_TYPE=$(echo "$DETECT_RESULT" | head -1)

echo "  Type:   $PDF_TYPE"

# ── Step 2: Extract text ────────────────────────────────────────────────────

if [ "$PDF_TYPE" = "text" ]; then
    # ── TEXT-BASED: use pdftotext directly ───────────────────────────────────
    echo "  Extracting text with pdftotext -layout..."
    pdftotext -layout "$PDF" "$OUTDIR/$PDF_NAME/full_text.txt"
    IN_FILE="$OUTDIR/$PDF_NAME/full_text.txt"

elif [ "$PDF_TYPE" = "image" ]; then
    # ── IMAGE-BASED: extract pages and OCR concurrently ──────────────────────
    if [ ! -x "$OCR_BIN" ]; then
        echo "ERROR: OCR binary not found: $OCR_BIN. Run scripts/build.sh first." >&2
        exit 2
    fi
    PAGES=$(pdfinfo "$PDF" 2>/dev/null | grep "Pages:" | awk '{print $2}')
    echo "  Pages:  $PAGES"
    echo "  Workers: $CONCURRENT concurrent"

    IMG_DIR="$TMPDIR/pages"
    mkdir -p "$IMG_DIR"

    # Extract all pages at 200 DPI
    echo "  Extracting page images (200 DPI)..."
    pdftoppm -r 200 -png "$PDF" "$IMG_DIR/page"

    IMG_FILES=("$IMG_DIR"/page-*.png)
    TOTAL=${#IMG_FILES[@]}
    echo "  OCR $TOTAL images with $CONCURRENT workers..."

    COMBINED="$OUTDIR/$PDF_NAME/full_text.txt"
    > "$COMBINED"

    # Concurrent OCR using xargs-style job batching
    # Process all images in parallel, N at a time
    OCR_RESULTS_DIR="$TMPDIR/ocr_results"
    mkdir -p "$OCR_RESULTS_DIR"

    active=0
    for img in "${IMG_FILES[@]}"; do
        PAGE_NUM=$(basename "$img" | sed 's/page-0*//;s/\.png//')
        OUT="$OCR_RESULTS_DIR/page-$(printf '%04d' "$PAGE_NUM").txt"

        (
            TEXT=$("$OCR_BIN" "$img" "$OCR_LANG" 2>/dev/null) || {
                : > "$OUT"
                echo "  ✗ page $PAGE_NUM (OCR failed)"
                exit 0
            }
            if [ -n "$TEXT" ]; then
                echo "$TEXT" > "$OUT"
                echo "  ✓ page $PAGE_NUM ($(echo "$TEXT" | wc -l | tr -d ' ') lines)"
            else
                echo "" > "$OUT"
                echo "  ✗ page $PAGE_NUM (no text)"
            fi
        ) &

        active=$((active + 1))

        # macOS 自带 Bash 3.2 没有 wait -n；按批次等待以限制并发。
        if [ "$active" -ge "$CONCURRENT" ]; then
            wait
            active=0
        fi
    done
    wait  # wait for remaining jobs

    # Assemble results in page order
    echo "  Assembling OCR results..."
    for f in "$OCR_RESULTS_DIR"/page-*.txt; do
        [ -f "$f" ] && cat "$f" >> "$COMBINED" && echo "" >> "$COMBINED"
    done

    IN_FILE="$COMBINED"
else
    echo "ERROR: 无法判断 PDF 类型: $DETECT_RESULT" >&2
    exit 2
fi

# ── Step 3: Convert to Markdown ─────────────────────────────────────────────

echo "  Converting to Markdown..."
UV_CACHE_DIR="$TMPDIR/uv-cache" uv run python3 "$SCRIPT_DIR/txt_to_md.py" \
    "$IN_FILE" \
    "$OUTDIR/$PDF_NAME/$PDF_NAME.md" \
    --lang "$OCR_LANG" 2>/dev/null || {
    echo '```text' > "$OUTDIR/$PDF_NAME/$PDF_NAME.md"
    cat "$IN_FILE" >> "$OUTDIR/$PDF_NAME/$PDF_NAME.md"
    echo '```' >> "$OUTDIR/$PDF_NAME/$PDF_NAME.md"
}

echo "  Output: $OUTDIR/$PDF_NAME/$PDF_NAME.md"
wc -l "$OUTDIR/$PDF_NAME/$PDF_NAME.md"

echo "=== Done ==="
