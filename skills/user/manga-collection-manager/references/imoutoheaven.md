# ImoutoHeaven AList 无修正同人志下载

## 概述

`alist-public.imoutoheaven.org` 是公开 AList 文件分享站点，提供汉化无修正同人志。SPA 应用（React/Vite），文件列表通过 JSON API 动态加载，不能直接爬 HTML。

**站点结构**：`SP后端1 → 离散分发 → 汉化 → 无修正合集`

```
无修正合集/
├── 2023 无修正合集/     (1284 files, ~87.5 GB)
└── 2024 无修正合集/     (360 files, ~24.5 GB)
```

**总计**：1,644 文件，~112 GB。全部为同人志（doujin），非单行本。

## 文件命名规范

```
(C##) [社团名 (画师名)] 作品标题 (原作系列) [汉化组][無修正].zip
```

变体：
- `(C##) [circle (author)] title (series) [translator][無修正].zip` — Comiket
- `(COMIC1☆##) [...]` — COMIC1 展会
- `(FF##) [...]` — Fancy Frontier（台湾）
- `[circle (author)] title [...]` — 无展会前缀

### 画师名提取规则

- `[社团 (画师)]` → 括号内为画师
- `[画师]` → 括号内即画师（无子括号）

## AList API

根域名：`https://alist-public.imoutoheaven.org`

所有 API 为 POST，`Content-Type: application/json`。

### 列出目录：`/api/fs/list`

```json
{
  "path": "/SP后端1/离散分发/汉化/无修正合集/2023 无修正合集",
  "password": "",
  "page": 1,
  "per_page": 0,
  "refresh": false
}
```

`per_page: 0` = 不分页。返回 `data.content[]`，每个 item：`{name, size, is_dir, path, modified}`。

### 获取下载链接：`/api/fs/get`

```json
{
  "path": "/SP后端1/离散分发/汉化/无修正合集/...",
  "password": ""
}
```

返回 `data.raw_url` — 带签名的临时下载直链（约 10 分钟过期）。

### 路径规则（重要）

API 返回的 `path` 字段是相对路径，缺少存储挂载点前缀。**必须在所有路径前加 `/SP后端1/离散分发`**。

```python
PREFIX = '/SP后端1/离散分发'

def crawl(path):
    items = api_list(path)
    for item in items:
        if item['is_dir']:
            child_path = path.rstrip('/') + '/' + item['name']
            crawl(child_path)  # ✅ 用 parent_path + name 拼接
```

直接用 API 返回的 `path` 会导致：`failed get storage: storage not found`。

## 下载限流

### 限制参数

- **429 (Too Many Requests)**：连续 ~3-5 次请求后触发
- **冷却时间**：10-30 秒，严重时 50+ 秒
- **禁止并发下载**，必须串行且带延迟
- **签名 URL 过期**：~10 分钟

### 推荐参数

```python
DELAY = 3.0                  # 每次下载间隔（最小值）
RETRY_DELAY = 10             # 429 后初始等待
MAX_RETRIES = 5              # 最多重试
BACKOFF_MULTIPLIER = 2       # 指数退避: 10s → 20s → 40s → 80s
```

### 429 策略

1. 等待退避时间
2. **重新调用 `/api/fs/get` 获取新签名 URL**（旧 URL 的签名在等待期间过期）
3. 继续下载

### 性能预期

- 理想：~15-20 文件/分钟（3s 间隔）
- 实际：~5-10 文件/分钟（含 429 重试）
- 122 文件（7.6 GB）：15-30 分钟
- **建议下载时段**：避开 UTC+8 20:00-24:00

## 下载脚本

```bash
# 预览（默认）
uv run --with requests python3 scripts/alist_download.py

# 执行下载
uv run --with requests python3 scripts/alist_download.py --execute

# 交叉比对模式：检查本地下载目录 → NAS
uv run --with requests python3 scripts/alist_download.py --crossref
uv run --with requests python3 scripts/alist_download.py --crossref --execute
```

脚本流程：
1. 从 `alist_match_results.json` 加载匹配结果
2. 对每位作者的远程文件检查 NAS 去重
3. 通过 `/api/fs/get` 获取签名下载 URL
4. 串行下载到 `{NAS}/{作者}/散篇/` 目录
5. 自动处理长文件名（截断到 200 字节）
6. 3 秒固定延迟 + 指数退避 + 5 次重试

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 2024 子目录返回 0 文件 | 路径拼接错误 | 用 `parent_path + '/' + name` |
| 429 狂刷 | 延迟太小 | 3 秒起步，429 后等 10-50 秒 |
| 下载到一半 403/401 | 签名 URL 过期 | 重新调用 `/api/fs/get` |
| 文件名过长 | macOS APFS 限制 | `safe_fname()` 截断到 200 字节 |
| 文件大小不符 | 下载中断 | `os.path.getsize()` vs `item['size']` 比较 |
| robots.txt Disallow | MCP fetch 拒绝 | 用 Python `requests` 直接调 API |
