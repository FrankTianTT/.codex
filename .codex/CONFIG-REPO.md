# Codex 全局配置仓库

全局配置使用 bare Git 仓库管理：

- Git 目录：`~/.codex-config.git`
- 工作树：`$HOME`
- 不使用 CC Switch、中转目录或软链接
- 文件直接保存在 Codex 官方识别路径中

## 常用命令

```bash
git --git-dir="$HOME/.codex-config.git" --work-tree="$HOME" status
git --git-dir="$HOME/.codex-config.git" --work-tree="$HOME" add -u
git --git-dir="$HOME/.codex-config.git" --work-tree="$HOME" commit
```

首次关联远端仓库时：

```bash
git --git-dir="$HOME/.codex-config.git" remote add origin <你的仓库地址>
git --git-dir="$HOME/.codex-config.git" push -u origin main
```

当前只创建了本地仓库，没有自动创建或绑定远端仓库。

添加新的全局 Skill 或 Agent 时，应显式添加：

```bash
git --git-dir="$HOME/.codex-config.git" --work-tree="$HOME" add -f \
  .agents/skills/<skill-name> \
  .codex/agents/<agent-name>.toml
```

## 纳入版本控制

- `~/.codex/AGENTS.md`
- `~/.codex/CONFIG-REPO.md`
- `~/.codex/config.example.toml`
- `~/.codex/reference/`
- `~/.codex/agents/`
- `~/.agents/skills/`

## 不纳入版本控制

- 实际 `config.toml`、认证信息和 MCP 私有参数
- 会话、日志、任务、临时文件和 shell 快照
- 自动记忆数据库
- 插件缓存与运行时缓存
- Python 缓存和系统生成文件
