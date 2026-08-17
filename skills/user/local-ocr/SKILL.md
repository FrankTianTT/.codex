---
name: local-ocr
description: 在 macOS 上使用 Apple Vision 本地识别扫描 PDF、截图和文档图片中的文字，支持中英日文、批量 OCR 与私密离线处理。任务核心是文字提取且当前主机为 macOS 时使用；Ubuntu、文本型 PDF、图表理解、界面审查或一般图片语义分析不要触发，改用 Codex 原生视觉或 PDF 插件。
---

# 本地 OCR

使用 Skill 自带的 Swift 源码和脚本在本机完成 OCR，不上传图片。实现仅支持 macOS；所有命令以当前 Skill 目录为基准。

## 安全与预检

1. 运行 `uname -s`，结果不是 `Darwin` 时停止使用本 Skill。
2. 检查 `bin/ocr_vision` 是否存在且可执行；缺失时运行 `scripts/build.sh`。缺少 Homebrew 依赖时先说明并取得安装授权。
3. 批处理前用用户提供的一张图片做烟雾测试。
4. 如果 Codex 沙箱内出现 `nilError` 或 Vision framework 错误，先说明原因并申请普通主机权限重跑同一张图片；主机权限下仍失败才回退到 Codex 原生视觉或 PDF 工具。
5. OCR 失败或输出为空时不要写入缓存，也不要继续批处理。

## 路径约定

默认目录：

```text
~/.codex/skills/user/local-ocr/
├── bin/ocr_vision             # 本机编译产物，不纳入 Git
├── scripts/                   # Swift 源码和工作脚本
└── references/                # 安装、实现和故障说明
```

如果设置了 `CODEX_HOME`，用 `$CODEX_HOME/skills/user/local-ocr` 代替 `~/.codex/skills/user/local-ocr`。

## 单张图片

```bash
~/.codex/skills/user/local-ocr/bin/ocr_vision image.png en
~/.codex/skills/user/local-ocr/bin/ocr_vision image.png zh
~/.codex/skills/user/local-ocr/bin/ocr_vision image.png ja
~/.codex/skills/user/local-ocr/bin/ocr_vision image.png cjk --raw
```

- `--raw`：数字截图或原生图片，只缩放，不增强。
- `--enhance`：扫描件，使用文档增强和轻微对比度。
- `--full`：完整预处理，默认模式。
- `cjk`：同时提供中日英识别提示，适合后续语言判断。

只需要文字时返回 OCR 文本；需要理解布局、图表或界面时，把原图交给 Codex 原生视觉，并把 OCR 结果作为辅助信息。

## PDF

先检测 PDF 类型：

```bash
~/.codex/skills/user/local-ocr/scripts/pdf_detect.sh file.pdf
```

- 文本型 PDF：优先使用 PDF 插件或 `pdftotext`，不要逐页 OCR。
- 扫描 PDF：运行本地转换脚本。

```bash
~/.codex/skills/user/local-ocr/scripts/pdf_to_md.sh file.pdf /output --lang=zh --workers=6
```

批量开始前检查页数、磁盘空间和输出目录。加密 PDF 或类型检测失败时停止并报告。

## 文字语言判断

```bash
uv run python3 ~/.codex/skills/user/local-ocr/scripts/char_analysis.py "这是中文"
printf 'これは日本語です\n' | uv run python3 ~/.codex/skills/user/local-ocr/scripts/char_analysis.py
```

判断顺序是：先看假名数量及其在假名加汉字中的占比，再判断中文，最后判断英文；不要用“汉字多于 20 个就是中文”的旧规则。

漫画目录的批量语言检测使用 `manga-collection-manager` Skill，不在这里复制维护。

## 按需读取

- 首次安装、重新编译或排查依赖时，读取 [references/environment.md](references/environment.md)。
- 调整图像预处理、语言提示、并发或文本清理时，读取 [references/implementation.md](references/implementation.md)。
