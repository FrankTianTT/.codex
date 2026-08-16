---
name: image-reader
description: |-
  图片理解与结构化提取。当你需要分析图片内容、OCR 提取文字、
  从图片中提取公式/算法/表格时，优先使用此技能。
  不包含 LaTeX 渲染验证、Mermaid 渲染验证——那些在项目级 vision-tools 中。
  触发：看图、分析图片、OCR、提取图片文字、图片里有什么、识别公式、
  提取算法、提取表格、截图内容。
---

# Image Reader — 图片理解与提取

脚本内置，无需依赖其他 skill。

## 1. 七种看图模式

所有模式共用 `review.py`，用 `--mode` 切换：

```bash
cd ~/.agents/skills/image-reader
uv run --with keyring python3 scripts/review.py image.png                  # 默认=design
uv run --with keyring python3 scripts/review.py --mode describe image.png  # 通用描述
uv run --with keyring python3 scripts/review.py --mode extract image.png   # OCR 文字提取
uv run --with keyring python3 scripts/review.py --mode diagram image.png   # 技术图解析
uv run --with keyring python3 scripts/review.py --mode dataviz image.png   # 数据图表分析
uv run --with keyring python3 scripts/review.py --mode diagnose image.png  # 错误截图诊断
uv run --with keyring python3 scripts/review.py --mode diff A.png B.png    # 两张图对比
```

| 模式 | 用途 | 典型场景 |
|------|------|---------|
| `design` | 设计审查 | "看看这个界面怎么样" |
| `describe` | 通用图片描述 | "这张图里有什么" |
| `extract` | OCR 文字提取 | "提取这张截图里的文字" |
| `diagram` | 技术图解析 | "解释这个架构图" |
| `dataviz` | 数据图表分析 | "分析这个数据图" |
| `diagnose` | 错误截图诊断 | "这个报错是什么意思" |
| `diff` | 两张图视觉对比 | "修改前后有什么不同" |

## 2. 图片分类

用 `describe` 分析后，按类型选后续处理：

| 分类 | 判定 | 下一步 |
|------|------|--------|
| FORMULA | 大量数学符号 | → `extract.py --mode formula` |
| ALGORITHM | 步骤化流程 | → `extract.py --mode algorithm` |
| TABLE | 行列数据网格 | → `extract.py --mode table` |
| DIAGRAM | 带箭头的节点图 | → `review.py --mode diagram` + 手写 Mermaid |
| DATA_CHART | 柱状/折线/统计图 | → 保留图片 + 文字描述 |
| ILLUSTRATION | 照片/渲染图 | → 保留图片 + 文字描述 |
| SCREENSHOT | 网页/App 界面 | → `design` 或 `extract` |
| DELETE | 表情包/水印 | → 标记，等用户确认删除 |

## 3. 结构化提取

```bash
cd ~/.agents/skills/image-reader
uv run --with keyring python3 scripts/extract.py --mode formula  image.jpg   # 公式 → LaTeX
uv run --with keyring python3 scripts/extract.py --mode algorithm image.jpg  # 算法 → 伪代码
uv run --with keyring python3 scripts/extract.py --mode table     image.jpg  # 表格 → Markdown
```

### 伪代码语法要点（pseudocode.js）

⚠️ 命令必须 **PascalCase**：

| ✅ 正确 | ❌ 错误 |
|---------|--------|
| `\For{cond}` | `\FOR` |
| `\If{cond}` | `\IF` |
| `\While{cond}` | `\WHILE` |
| `\State ...` | `\STATE` |
| `\Require{...}` | `\REQUIRE $x$`（需要花括号） |

### 表格提取注意

- 数学符号用 `$...$` 包裹
- 简单表格（≤10×10，无合并单元格）适合提取；复杂表格保留原图
- 原图保留不删

## 4. 链路

```
用户发图 → describe 分类 → 按类型选模式 → extract/formula/algorithm/table → 输出
```

## 5. API Key 管理

所有 key 通过 macOS Keychain 加密存储，脚本通过 `_shared.py` 的 `get_api_key()` 读取。

| Key 名 | 环境变量 | 用途 |
|--------|---------|------|
| `zhipu-api-key` | `ZHIPU_API_KEY` | 智谱 glm-4.6v：看图 (review.py)、提取 (extract.py)，主力 |
| `minimax-api-key` | `MINIMAX_API_KEY` | MiniMax-M3：看图、提取，智谱不可用时的降级备选 |

**设置 key**：

```bash
uv run --with keyring python3 -c "
import keyring, getpass
key = getpass.getpass('粘贴 ZHIPU_API_KEY: ')
keyring.set_password('zhipu-api-key', '$USER', key)
print('✅ 已存入系统钥匙链')
"
```

---

需要 LaTeX 编译验证、Mermaid 渲染验证、验证闭环等重型功能时，加载项目级 `vision-tools`。
