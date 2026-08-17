#!/bin/bash
# OCR a single image using our Swift Vision tool
# Usage: ocr_image.sh <image_path> [lang: en|zh|ja|cjk|auto] [options: --raw|--enhance|--full]
# Transparent wrapper — all arguments passed directly to ocr_vision

if [ ! -f "$1" ]; then
    echo "ERROR: Image not found: $1" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/../bin/ocr_vision" "$@"
