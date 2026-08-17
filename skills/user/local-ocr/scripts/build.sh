#!/bin/bash
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
    echo "ERROR: local-ocr 只能在 macOS 上编译。" >&2
    exit 2
fi

if ! command -v swiftc >/dev/null 2>&1; then
    echo "ERROR: 未找到 swiftc，请先安装 Xcode Command Line Tools。" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
mkdir -p "$SKILL_DIR/bin"
swiftc -module-cache-path "$SKILL_DIR/bin/module-cache" \
    -O -o "$SKILL_DIR/bin/ocr_vision" "$SCRIPT_DIR/ocr_vision.swift"
echo "已生成: $SKILL_DIR/bin/ocr_vision"
