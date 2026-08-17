# Codex 全局规则

## 维护语言

本文件及全局 Codex 配置的新增、修改均使用中文维护。

## 配置维护

- 只维护 Codex，不再兼容或同步 Claude Code。
- 不使用 CC Switch、中转目录或跨客户端软链接维护重复副本。
- 全局规则放在 `~/.codex/AGENTS.md`，全局自定义 Skill 放在 `~/.agents/skills/`，全局自定义 Agent 放在 `~/.codex/agents/`。
- 项目专用规则、Skill 和 Agent 随项目仓库维护，不复制到全局目录。
- 会话、认证、缓存、自动记忆数据库和插件缓存不纳入版本控制。

## 联网与检索

- 使用 Codex 当前提供的网页搜索、浏览器或任务对应的专用连接器；不绑定某个历史 MCP 工具名。
- 用户要求最新信息、检索、核验或来源时，实际联网验证，并优先采用权威的一手来源。
- 普通开放网页搜索优先使用 Codex 网页搜索；普通网页浏览、点击和表单交互优先使用 Codex Browser 或专用连接器。
- 以下场景应主动考虑并加载 `opencli-usage`，无需等待用户点名 OpenCLI：
  - 用户明确指定网站或平台，且 OpenCLI 当前 registry 有匹配的只读 adapter，可直接获得结构化字段、列表、评论、指标或站内搜索结果。
  - 项目 Skill 或现有工作流明确依赖 OpenCLI adapter。
  - 任务需要复用浏览器登录态、站点 Cookie 或平台专用接口，OpenCLI 比通用网页搜索更稳定。
  - 需要开发、验证或修复 OpenCLI adapter。
- 使用 OpenCLI 前只定向检查目标站点的 registry 和实时 `--help`，不要把完整 registry 灌入上下文；adapter 不存在、桥接不可用或结果不可靠时，回退到 Codex 网页搜索、Browser 或专用连接器。
- OpenCLI 的只读查询可在任务范围内主动执行；发布、评论、点赞、关注、删除、上传、下单等外部写操作必须取得用户明确授权。

## 运行环境

- 全局配置需兼容 macOS（Apple Silicon）与 Ubuntu；执行前根据当前系统选择工具和路径。
- Python 环境与依赖统一使用 `uv`，禁止 `pip3 install` 和 `python3 -m venv` 污染系统环境。
- 一次性 Python 依赖使用 `uv run --with <包名> python3 <脚本>`。
- 安装方式、中国镜像与代理细节见 `~/.codex/reference/environment.md`。

## API 密钥

- 绝对禁止在源码、配置或文档中硬编码 API 密钥。
- 读取顺序为：系统 keyring → 环境变量 → 明确报错并引导设置。
- Python keyring 通过 `uv run --with keyring` 调用；模板见 `~/.codex/reference/keyring-pattern.py`。

## Skill 维护

- 全局 Skill 只保留跨项目且 Codex 默认能力无法稳定替代的工作流；项目专用知识留在项目仓库。
- 每个 Skill 聚焦一个任务，触发描述写清适用范围和排除项，避免与系统 Skill、插件 Skill 或项目 Skill 抢占同类请求。
- 不保留 Claude Code 专用元数据、已失效依赖或仅作命令索引的冗余 Skill。
- 维护采用闭环：列清单 → 用代表性请求独立消费 → 记录失败 → 修改或退役 → 校验与复测 → 提交版本控制。
- 涉及删除、覆盖、迁移源文件的脚本必须默认预览；只有显式 `--execute` 后才能执行，并在删除源文件前验证输出完整性。
