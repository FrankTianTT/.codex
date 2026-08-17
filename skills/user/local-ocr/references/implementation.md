# 实现说明

仅在调整 OCR 实现、预处理、批量转换或文字清理时读取本文件。

## 图像管线

```text
图片
  → 最长边缩放至 2400 px
  → 可选 CIDocumentEnhancer
  → 可选对比度和锐化
  → VNRecognizeTextRequest
  → 逐行文本
```

模式：

- `raw`：仅缩放，适合截图和数字图片。
- `enhance`：文档增强加对比度，适合清晰扫描件。
- `full`：再增加轻微锐化，适合低对比度扫描件。

`VNRecognizeTextRequestRevision3` 用于减少接口 revision 漂移，但 macOS 底层模型或框架行为仍可能随系统更新变化。系统升级后应重新跑烟雾样本，不能假设输出完全不变。

## 语言提示

| 模式 | Vision 语言顺序 | 用途 |
|---|---|---|
| `en` | `en-US`, `zh-Hans` | 英文优先 |
| `zh` | `zh-Hans`, `zh-Hant`, `en-US` | 中文扫描件 |
| `ja` | `ja-JP`, `en-US` | 日文扫描件 |
| `cjk` | 中、日、英 | 后续语言判断 |
| `auto` | 系统偏好 | 非 CJK 或探索性使用 |

Vision 的语言列表是优先提示，不是硬过滤器。

## PDF 管线

```text
PDF
  → pdf_detect.sh
  ├─ 文本型：pdftotext -layout
  └─ 扫描型：pdftoppm → 分批并发 OCR
  → txt_to_md.py
  → Markdown
```

`pdf_to_md.sh` 使用批次并发，兼容 macOS 自带 Bash 3.2；每批结束后等待，再启动下一批。临时目录由 `mktemp` 创建，并在退出时清理。

## 语言判断

`char_analysis.py` 统计假名、CJK 汉字和 ASCII 拉丁字母：

1. 假名至少 5 个，且假名占假名加汉字的比例不低于 12%：日文。
2. 否则汉字至少 5 个：中文。
3. 否则拉丁字母至少 10 个：英文。
4. 其他情况：未知或文字量不足。

这是面向 OCR 批量分类的启发式，不替代语言学检测。低文字量、拟声词密集或中日混排内容应标记为待人工复核。

## 文本清理

`txt_to_md.py` 负责：

- 去除独立页码和重复页眉；
- 合并 OCR 断行；
- 识别章节标题；
- 输出 Markdown。

清理规则可能误判表格、诗歌和代码。遇到这些结构时保留原始文本，并用 Codex 或专用文档工具做结构恢复。
