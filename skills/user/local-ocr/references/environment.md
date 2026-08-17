# 环境与安装

仅在首次安装、重新编译或依赖故障时读取本文件。

## 平台

- 操作系统：macOS
- 架构：Apple Silicon 或 Intel Mac，由当前主机本地编译
- OCR：Apple Vision、Core Image
- PDF 工具：Poppler
- 文本转换：Python，通过 `uv run python3` 执行

Ubuntu 不提供 Apple Vision。Ubuntu 上使用 Codex 原生视觉、PDF 插件或项目已选定的跨平台 OCR 工具。

## 依赖检查

```bash
uname -s
command -v swiftc
command -v pdfinfo
command -v pdftotext
command -v pdftoppm
command -v uv
```

扫描 PDF 需要 Poppler。简繁转换才需要 OpenCC；普通图片 OCR 不依赖它。

缺少依赖时先向用户说明将修改本机环境，并取得授权后再安装：

```bash
brew install poppler opencc
```

不要使用 `pip3 install` 或 `python3 -m venv`。

## 编译

在 Skill 目录运行：

```bash
scripts/build.sh
```

脚本把 `scripts/ocr_vision.swift` 编译为 `bin/ocr_vision`。`bin/` 是当前主机的编译产物，不纳入 Git；迁移到新电脑后重新编译。

手工等价命令：

```bash
mkdir -p bin
swiftc -O -o bin/ocr_vision scripts/ocr_vision.swift
```

## 烟雾测试

先使用一张非敏感测试图片：

```bash
bin/ocr_vision sample.png en --raw
```

Codex 沙箱可能阻止 Vision framework 初始化并返回 `nilError`。此时不要重装工具；先申请普通主机权限重跑相同命令。只有主机权限下仍失败，才检查系统版本、图片有效性和重新编译。

## 版本管理

纳入 Git：

- `scripts/ocr_vision.swift`
- Shell/Python 工作脚本
- Skill 和 reference 文档

不纳入 Git：

- `bin/ocr_vision`
- OCR 缓存
- PDF 页面临时图片
- 用户输入和识别结果
