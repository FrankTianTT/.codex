# Codex 全局配置仓库

全局配置使用普通 Git 仓库管理：

- 仓库根目录：`~/.codex`
- 全局自定义 Skill 真源：`~/.codex/skills/user/`
- Codex 用户级 Skill 发现入口：`~/.agents/skills`，软链接到上述真源
- 不使用 CC Switch、中转目录或跨客户端同步，不维护重复副本

## 常用命令

```bash
git -C "$HOME/.codex" status
git -C "$HOME/.codex" add -u
git -C "$HOME/.codex" commit
```

首次关联远端仓库时：

```bash
git -C "$HOME/.codex" remote add origin <你的仓库地址>
git -C "$HOME/.codex" push -u origin main
```

当前只创建了本地仓库，没有自动创建或绑定远端仓库。

添加新的全局 Skill 或 Agent 时，应显式添加：

```bash
git -C "$HOME/.codex" add \
  skills/user/<skill-name> \
  agents/<agent-name>.toml
```

## 纳入版本控制

- `~/.codex/AGENTS.md`
- `~/.codex/CONFIG-REPO.md`
- `~/.codex/config.example.toml`
- `~/.codex/reference/`
- `~/.codex/agents/`
- `~/.codex/skills/user/`

## 不纳入版本控制

- 实际 `config.toml`、认证信息和 MCP 私有参数
- 会话、日志、任务、临时文件和 shell 快照
- 自动记忆数据库
- 插件缓存与运行时缓存
- Python 缓存和系统生成文件

## 新设备恢复

克隆仓库到 `~/.codex` 后，建立 Codex 用户级 Skill 发现链接：

```bash
mkdir -p "$HOME/.agents"
ln -s ../.codex/skills/user "$HOME/.agents/skills"
```

若目标已存在，先核对其内容和类型，不要直接覆盖。
