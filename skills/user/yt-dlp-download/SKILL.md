---
name: yt-dlp-download
description: 使用 yt-dlp 检查并下载 YouTube、Bilibili 等平台的视频、音频、字幕或播放列表。用户要求下载、保存、提取媒体，或明确提到 yt-dlp、B 站下载、视频下载时使用。
---

# yt-dlp 媒体下载

使用 `yt-dlp` 保存用户有权访问的公开或自有媒体。不要绕过 DRM、付费墙、账号权限或平台访问控制。

## 工作流程

1. 确认媒体 URL、目标内容（视频、音频、字幕或播放列表）和输出目录。
2. 检查 `yt-dlp` 与 `ffmpeg` 是否可用。
3. 先模拟或查看格式，确认标题、可用流和大致体积。
4. 使用满足需求的最简单命令下载。
5. 验证输出文件存在、大小合理；报告文件路径和任何降级情况。

用户未指定目录时，使用当前工作目录下的 `downloads/`，并在执行前明确告知。单个视频默认加 `--no-playlist`，不要因 URL 属于播放列表而意外批量下载。

## 环境检查

```bash
command -v yt-dlp
yt-dlp --version
command -v ffmpeg
command -v ffprobe
```

不要硬编码可执行文件路径或版本。工具缺失时，先告知用户并按操作系统使用包管理器安装；涉及系统级安装时先取得授权。

- macOS：`brew install yt-dlp ffmpeg`
- Ubuntu：优先使用系统包管理器安装；若发行版版本过旧，再说明可选的官方安装方式。

### YouTube 的 JavaScript runtime

当前 yt-dlp 完整提取 YouTube 格式需要外部 JavaScript runtime。先检查可用 runtime：

```bash
command -v deno
command -v node
command -v bun
command -v qjs
```

- Deno 是 yt-dlp 默认启用的 runtime；可用时通常不需要额外参数。
- 本机没有 Deno、但 Node 满足当前 yt-dlp/EJS 最低版本要求时，为 YouTube 命令加入 `--js-runtimes node`。不要把该参数机械用于其他网站。
- 如果没有受支持的 runtime，说明 YouTube 格式可能缺失或提取失败；安装 runtime 属于环境变更，先取得用户授权。
- 官方 yt-dlp 可执行文件通常已包含 EJS 组件；其他安装方式仍报 EJS 缺失时，以 yt-dlp 当前官方 EJS 文档为准，不自行下载来历不明的脚本。

后文命令若用于 YouTube，应按上述检查结果加入相应的 `--js-runtimes` 参数。

## 下载前检查

只需要确认元数据时：

```bash
yt-dlp --simulate --no-playlist \
  --print "%(title)s | %(uploader)s | %(duration_string)s | %(webpage_url)s" \
  "<URL>"
```

画质、编码或文件大小会影响选择时，再列出格式：

```bash
yt-dlp -F --no-playlist "<URL>"
```

不要机械地让用户从格式代码表中选择。需求明确时自行选取合适格式；只有画质、编码兼容性或体积存在实质取舍时才询问。

## 常用下载方式

### 最佳视频与音频

```bash
yt-dlp --no-playlist \
  -f "bv*+ba/b" \
  --merge-output-format mp4 \
  -P "<OUTPUT_DIR>" \
  -o "%(uploader)s - %(title).120s.%(ext)s" \
  "<URL>"
```

该命令优先选择最佳视频流和音频流，并在必要时通过 `ffmpeg` 合并。容器或编码无法无损转为 MP4 时，说明实际输出格式，不要为得到 `.mp4` 扩展名而擅自重编码。

### 仅音频

```bash
yt-dlp --no-playlist \
  -x --audio-format m4a \
  -P "<OUTPUT_DIR>" \
  -o "%(uploader)s - %(title).120s.%(ext)s" \
  "<URL>"
```

只有用户明确要求 MP3 时才改用 `--audio-format mp3`，因为这通常需要转码。
`m4a` 也可能在源音频不是兼容编码时触发转码；用户要求无损提取或禁止转码时，先查看音频格式并保留原始编码与容器。

### 仅字幕

```bash
yt-dlp --no-playlist --skip-download \
  --write-subs --write-auto-subs \
  --sub-langs "zh-Hans,zh-Hant,zh,en" \
  --convert-subs srt \
  -P "<OUTPUT_DIR>" \
  "<URL>"
```

报告字幕是人工字幕还是自动字幕；不存在目标语言时不要伪造成功。

### 播放列表

只有用户明确要求整套播放列表时才移除 `--no-playlist`。先模拟并报告项目数；长列表可用 `--playlist-start`、`--playlist-end` 或 `--playlist-items` 限定范围。

## 登录、Cookie 与隐私

先尝试不带 Cookie 的公开访问。只有出现登录限制、地区限制或账号可见画质不足，并且用户有权访问时，才使用 Cookie。

使用浏览器 Cookie 或 Cookie 文件前必须得到用户明确授权：

```bash
yt-dlp --cookies-from-browser "<BROWSER>" "<URL>"
yt-dlp --cookies "<COOKIE_FILE>" "<URL>"
```

- 不读取、打印、复制或提交 Cookie 内容。
- 不要求用户把 Cookie 文本粘贴到对话中。
- 优先使用用户指定的浏览器或文件，不猜测账号配置。
- Bilibili、X、Instagram 等平台是否需要 Cookie 取决于内容和当前策略，不把它写成永久规则。

## 故障处理

- **音视频未合并**：检查 `ffmpeg`，保留原始流并说明原因。
- **403、412 或登录错误**：先更新 `yt-dlp` 并重试公开访问；仍失败时再请求授权使用 Cookie。不要默认伪造 User-Agent。
- **YouTube 提示缺少 JavaScript runtime**：按上文检查 Deno、Node、Bun 或 QuickJS；只有 Node 可用时显式加入 `--js-runtimes node`。
- **PyInstaller `Failed to initialize sync semaphore`**：这是受限沙箱阻止本机单文件可执行程序初始化，不代表 yt-dlp 损坏。取得授权后在普通主机权限下重跑同一只读或下载命令，不要因此重装工具。
- **多个 yt-dlp 进程启动卡住**：Codex 中顺序执行站点检查和下载，不要为提速并发启动多个 PyInstaller 单文件进程；片段并发应优先交给 yt-dlp 自身管理。
- **格式不可用**：重新执行 `-F`，放宽格式选择器，并说明画质或容器降级。
- **下载限速**：先使用 yt-dlp 自身重试；只有系统已有外部下载器时才考虑 `--downloader`。
- **大文件**：预计超过 1 GB 时，在下载前告知用户大小、剩余空间风险和预计等待时间。
- **网络问题**：yt-dlp 会继承 `HTTP_PROXY`、`HTTPS_PROXY` 等环境配置。只检查代理是否存在，不输出可能含账号信息的完整代理 URL；需要绕过或更换用户代理时先说明并取得同意。不要把代理地址固化进 Skill。

## 交付检查

下载结束后至少检查：

```bash
ls -lh "<OUTPUT_FILE>"
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "<OUTPUT_FILE>"
```

字幕或纯音频不适合上述检查时，使用对应的轻量检查。最终说明输出路径、实际格式、清晰度或音频质量，以及任何失败或降级；不要只报告命令退出码。
