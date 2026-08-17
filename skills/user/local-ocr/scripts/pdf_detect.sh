#!/bin/bash
# Detect if a PDF is text-based or image-based
# Usage: pdf_detect.sh <pdf_path>
# Returns: "text" or "image" (exits 0 for text, 1 for image)

PDF="$1"

if [ ! -f "$PDF" ]; then
    echo "ERROR: PDF not found: $PDF" >&2
    exit 2
fi

PAGES=$(pdfinfo "$PDF" 2>/dev/null | grep "Pages:" | awk '{print $2}')
if [ -z "$PAGES" ]; then
    echo "ERROR: Cannot read PDF info" >&2
    exit 2
fi

# Strategy: sample pages across the PDF, count text bytes per page.
# Text-based PDFs: content pages have 100s-1000s of bytes
# Image-based PDFs: ALL pages have <100 bytes (just a few garbage chars)
#
# Sample: first 3 pages + 3 from quarter + 3 from middle + 3 from three-quarters
# This handles chapter-opening pages (which may have little text even in text-based PDFs)

MAX_PAGES=0
TOTAL_BYTES=0
SAMPLED=0

sample_page() {
    local p=$1
    if [ "$p" -le "$PAGES" ]; then
        local bytes=$(pdftotext -f $p -l $p "$PDF" - 2>/dev/null | wc -c | tr -d ' ')
        TOTAL_BYTES=$((TOTAL_BYTES + bytes))
        SAMPLED=$((SAMPLED + 1))
        if [ "$bytes" -gt "$MAX_PAGES" ]; then
            MAX_PAGES=$bytes
        fi
    fi
}

# First pages
for p in 1 2 3 4 5; do
    sample_page $p
done

# Quarter mark
Q1=$((PAGES / 4))
for p in $Q1 $((Q1+1)) $((Q1+2)); do
    sample_page $p
done

# Middle
MID=$((PAGES / 2))
for p in $MID $((MID+1)) $((MID+2)); do
    sample_page $p
done

# Three-quarters
Q3=$((PAGES * 3 / 4))
for p in $Q3 $((Q3+1)) $((Q3+2)); do
    sample_page $p
done

if [ "$SAMPLED" -eq 0 ]; then
    echo "image"
    exit 1
fi

AVG=$((TOTAL_BYTES / SAMPLED))

# Heuristic:
# - If ANY page has >200 bytes of text, it's text-based
# - If average >80 bytes/page, it's text-based
# - Otherwise image-based
if [ "$MAX_PAGES" -gt 200 ] || [ "$AVG" -gt 80 ]; then
    echo "text"
    echo "  Pages: $PAGES, max bytes/page: $MAX_PAGES, avg: $AVG → text-based" >&2
    exit 0
else
    echo "image"
    echo "  Pages: $PAGES, max bytes/page: $MAX_PAGES, avg: $AVG → image-based (scanned/bookscan)" >&2
    exit 1
fi
