# Codex 全局记忆

## 维护语言
本文件的后续所有更新、修改、新增内容均使用**中文**进行维护。

## 配置维护原则
- 只维护 Codex 配置，不再兼容或同步 Claude Code
- 禁止通过 CC Switch、通用中转目录或跨客户端软链接维护重复副本
- 全局规则维护在 `~/.codex/AGENTS.md`
- 全局自定义 Skill 维护在 `~/.agents/skills/`
- 全局自定义 Agent 维护在 `~/.codex/agents/`
- 项目级 Skill 与 Agent 随项目仓库维护
- Codex 会话、认证、缓存、自动记忆数据库和插件缓存均不纳入版本控制

## MCP 抓取工具
所有 URL 抓取必须使用 `mcp__fetch__fetch`，**禁止**使用原生的 `WebFetch` 工具。
**原因：** 用户明确偏好 MCP fetch 工具，它的限制可能更少。

## 运行环境
本项目运行在以下两种操作系统上，所有配置均需兼容两者：

| 系统 | 包管理器 |
|------|----------|
| **macOS**（Apple Silicon） | Homebrew |
| **Ubuntu** | apt |

## Python：始终使用 uv
1. **禁止使用系统 `pip3 install`** — 会污染全局 Python 环境，引发冲突
2. **禁止使用 `python3 -m venv`** — 所有环境管理统一使用 `uv`
3. 一次性脚本的正确用法：`uv run --with <包名> python3 <脚本>`
4. `uv` 安装方式因系统而异：
   - **macOS**：`brew install uv`，路径 `/opt/homebrew/bin/uv`
   - **Ubuntu**：通过官方脚本 `curl -LsSf https://astral.sh/uv/install.sh | sh`，路径 `~/.cargo/bin/uv`
   - 安装后 `uv` 应在 `PATH` 中，直接使用即可
5. 通过系统包管理器安装的工具可以放心使用（macOS: Homebrew 装的 cmake、ffmpeg、opencc、uv 等；Ubuntu: apt 装的 cmake、ffmpeg 等，uv 通过官方脚本安装）；系统级 pip 安装的 Python 包不安全

## 包管理器与镜像源（中国加速）
用户在中国，使用中科大镜像加速软件下载。

### macOS — Homebrew
关键环境变量：
```
HOMEBREW_BOTTLE_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles
HOMEBREW_API_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles/api
```
禁止使用 HomebrewCN 或任何第三方安装脚本（供应链风险）。

### Ubuntu — apt
使用中科大 apt 镜像源，`sources.list` 中 `deb` 行指向 `https://mirrors.ustc.edu.cn/ubuntu/`。
禁止使用未知来源的 PPA 或第三方安装脚本（供应链风险）。

## 网络代理
用户在中国，访问 GitHub 等境外网站需要代理。
- HTTP/HTTPS 代理地址：`http://127.0.0.1:7897`
- 命令行工具使用方式：`export https_proxy=http://127.0.0.1:7897`
- 当 npx/npm/git 操作遇到连接错误时，建议使用此代理

## API 密钥管理（铁律）

**🚫 绝对禁止在任何文件中硬编码 API 密钥。** 密钥写入源码 → 泄露到 git 仓库和 AI 上下文。

必须使用 Python **keyring** 库（macOS 钥匙串 / Linux gnome-keyring），通过 `uv run --with keyring` 调用。
密钥读取优先级：**keyring → 环境变量 → 报错引导设置**。

完整代码模板与交互式设置指南见：`~/.codex/reference/keyring-pattern.py`
