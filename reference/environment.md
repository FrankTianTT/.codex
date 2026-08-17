# Codex 全局环境参考

仅在安装工具、排查依赖或网络失败时读取本文件。

## 支持平台

| 系统 | 系统包管理器 | `uv` 安装 |
| --- | --- | --- |
| macOS（Apple Silicon） | Homebrew | `brew install uv` |
| Ubuntu | apt | 使用 Astral 官方安装方式 |

安装前先检测系统和命令是否已存在。优先使用系统包管理器或工具官方渠道，不使用 HomebrewCN、未知 PPA 或来历不明的安装脚本。

## Python

- 不使用 `pip3 install` 或 `python3 -m venv`。
- 一次性依赖：`uv run --with <包名> python3 <脚本>`。
- 项目依赖按项目已有的 `pyproject.toml`、`uv.lock` 和说明维护。

## 中国网络环境

### Homebrew 镜像

```bash
export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles
export HOMEBREW_API_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles/api
```

### Ubuntu 镜像

apt 软件源使用中科大 Ubuntu 镜像：`https://mirrors.ustc.edu.cn/ubuntu/`。

### 本地代理

访问 GitHub 等境外服务出现连接问题时，可按需设置：

```bash
export https_proxy=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
```

代理只在确有需要的命令或会话中启用，不写入项目源码。
