---
name: manga-collection-manager
description: |
  NAS 漫画/同人志馆藏维护。覆盖三个来源的获取、语言分类、去重、文件夹重组全流程。

  触发条件：
  - 维护/整理/管理 NAS 漫画或同人志馆藏
  - 来自魂+/南+/北+/ibm5100 的合集需要解压处理
  - 来自 ImoutoHeaven/AList 的下载需要爬取
  - 来自 E-hentai 的种子下载
  - 同人志语言分类、去重、重组
  - 画师文件夹整理（单行本/系列/散篇）
---

# 漫画馆藏管理

## 概述

本 skill 负责维护 NAS 上的漫画/同人志馆藏。内容来源有三个，各自的获取方式见 references：

| 来源 | 说明 | Reference |
|------|------|-----------|
| 魂+ ibm5100 | 百度网盘 → RAR 双层解压 → 文件夹 | [references/ibm5100.md](references/ibm5100.md) |
| ImoutoHeaven AList | 公开 AList API → zip 直下 | [references/imoutoheaven.md](references/imoutoheaven.md) |
| E-hentai | 种子下载 | [references/ehentai.md](references/ehentai.md) |

无论来源如何，最终输出统一为：**按画师组织的 zip 压缩包**，仅保留中文汉化、JPG/PNG 图片格式。

## 馆藏标准

### 目标目录结构

```
{画师名}/
├── [单行本标题].zip          ← 150+ 页的完整单行本
├── [系列名] Ep01.zip         ← 5+ 章的大型系列
├── [系列名] Ep02.zip
└── 散篇/                     ← 单篇作品 + 小型系列
    ├── [短篇标题].zip
    ├── [小系列] Ch01.zip     ← 2-4 章的小系列
    └── [小系列] Ch02.zip
```

### 文件格式

- **IRON RULE**: 只保留 `.jpg` / `.jpeg` / `.png`
- 删除：`.pdf` `.gif` `.webp` `.bmp` `.txt` `.url` `.html` `Thumbs.db` `._*`（Apple Double）

```bash
find /path/to/dir -name '*.pdf' -delete
find /path/to/dir -type f ! -name '*.jpg' ! -name '*.jpeg' ! -name '*.png' \
  ! -name '*.JPG' ! -name '*.JPEG' ! -name '*.PNG' -delete
find /path/to/dir -name '._*' -type f -exec rm -f {} \; 2>/dev/null
```

### 压缩约定

每个叶子目录（直接含图片）压缩为同名 `.zip`，删除原目录。exFAT 上几千个小文件的簇大小浪费严重，压缩后大幅节省空间。

```bash
uv run python3 scripts/compress.py --dryrun   # 预览
uv run python3 scripts/compress.py            # 执行
```

## 语言分类

### 目录名分类（快速，~95% 准确）

汉化作品一定有括号标签，无标签即为日文原版。

**S 级（正版/授权）** → 永远优先保留
```
[買動漫授權中文版] [未来數位] [新视界] [新視界] [官方中文]
```

**A 级（知名汉化组）**
```
[無邪気漢化組] [暴碧汉化组] [绅士仓库汉化] [脸肿汉化组] [天鵝之戀漢化]
[无毒汉化组] [禁漫漢化組] [不咕鸟汉化组] [心海汉化组] [黑锅汉化组]
[白杨汉化组] [風的工房] [篆儀通文書坊漢化] [4K掃圖組] [CE家族社]
```

**F 级（机翻）→ 立即删除**
```
[MAHIRO机翻] [iAtt机翻] [机翻] [機翻]
```

**英文** → 有中文版则删，无则保留
```
[英訳] [English]
```

**日文 → 删除**
```
[日原版] [DLsite] [FANZA] 及所有无括号标签的文件夹
```

### OCR 验证（需要时）

目录名分类覆盖 ~95% 场景。需要验证歧义时，使用 `local-ocr` skill 的 CJK 语言检测：

```bash
uv run python3 scripts/detect_language.py --dryrun   # 预览采样
uv run python3 scripts/detect_language.py --workers 16   # 全量检测
```

核心算法：CJK ≥ 20 字符 → 中文（日文漫画不可能有这么多汉字而没有等比例的假名）。详细算法见 `scripts/detect_language.py` docstring。

**重要更正**：目录名中的假名不是日文信号——汉化作品保留原日文标题。旧启发式 "目录名含假名 → 日文" ~100% 错误。

## 去重规则

### 多版本优先级

同名作品存在多个汉化版本时，保留优先级：

1. **S 级**（授权正版）> 其他一切
2. **A 级**（知名汉化组）> 个人汉化
3. `[無修正]`（无修正）> 有修正
4. `[第二版]` / `[v2]` > 初版
5. 页数更多 > 页数更少
6. 以上均相等 → 保留先找到的

### 常见重复模式

- `(別スキャン)` — 替代扫本 → 删除
- `[重嵌版]` — 重嵌版 → 比较后择优
- `[カラー化]` — 上色版 → 酌情保留
- `#合刊/` — 合刊文件夹，含其他画师作品 → 验证后删除非目标画师内容

批量去重使用脚本：

```bash
uv run python3 scripts/dedup_nas.py              # 预览
uv run python3 scripts/dedup_nas.py --execute    # 执行
```

## 重组规则

### 150 页规则

**单行本 (tankoubon)**：目录递归含 150+ 张图片。单行本典型 180-220 页，杂志连载 15-40 页，同人短篇 20-50 页。150 页阈值可靠地区分二者。

不要因为目录名有 `[未来數位]` 就判定为单行本——必须数图片。

### 系列检测：仅限显式编号

禁止按标题前缀相似度分组——会产生假系列（如 Hamao 的 "宙に浮いたままのX" 是不同故事，不是系列）。只在以下情况分组：

- `Title 1, Title 2, Title 3` — 数字编号
- `Title 前編 / Title 後編` — 前后篇
- `Title 第X話` — 话数编号
- `Title Case.X` — Case 编号

**规模阈值**：
- 5+ 章 → 系列放在**画师根目录**
- 2-4 章 → 系列放在**散篇/** 内
- 1 章 → 单篇 → 直接放 散篇/

### 子目录继承

子文件夹在汉化组文件夹内的 → 继承中文分类。例如 `[無邪気漢化組]/妻子视角/` → 中文。

PIXIV/FANBOX 日期子目录和 CG 集不适用语言分类。

## 执行顺序

**始终按此顺序操作：**

1. **建清单** — 扫描所有文件夹，分类语言，标记重复
2. **预览** — DRY RUN，展示删除/重组计划
3. **删除** — 非中文、非图片、机翻、重复
4. **重组** — 展平分类层级、应用 150 页规则、系列检测
5. **压缩** — leaf dir → zip
6. **清理** — 删除空目录、`._*` 文件

## 通用陷阱

1. **假名 ≠ 日文** — 汉化作品保留日文标题，目录名中的假名不说明任何问题
2. **标签不全信** — `[未来數位]` 不代表是单行本，必须数图片
3. **前缀相似 ≠ 系列** — 只用显式编号分组，禁止前缀匹配
4. **子目录继承** — `[汉化组]/子目录/` 子目录继承中文分类
5. **exFAT Apple Double** — 外置盘上的 `._*` 文件会导致 `shutil.rmtree` 失败，先清理再删除
6. **容器目录** — 有子目录的不一定是叶子节点，不要误删组织结构
7. **NAS 不可解压** — 解压到本地 SSD，不要直接在 NAS 上解压（I/O 瓶颈）

## 脚本速查

```bash
# 语言检测
uv run python3 scripts/detect_language.py --dryrun
uv run python3 scripts/detect_language.py --workers 16

# 压缩叶子目录
uv run python3 scripts/compress.py --dryrun
uv run python3 scripts/compress.py

# 去重
uv run python3 scripts/dedup_nas.py
uv run python3 scripts/dedup_nas.py --execute

# ibm5100 解压后迁移到 NAS
uv run python3 scripts/migrate_to_nas.py

# AList 下载
uv run --with requests python3 scripts/alist_download.py
uv run --with requests python3 scripts/alist_download.py --execute
```
