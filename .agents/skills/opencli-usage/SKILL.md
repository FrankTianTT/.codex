---
name: opencli-usage
description: OpenCLI 的轻量路由说明。仅当用户明确要求使用 OpenCLI，项目 Skill 明确依赖 OpenCLI，或需要开发、调试 OpenCLI adapter 时使用。普通网页搜索使用 Codex 网页搜索，普通网页交互使用 Codex Browser 或专用连接器。
---

# OpenCLI 路由

只保留 Codex 与当前 OpenCLI 安装之间的稳定边界。命令细节以当前 CLI 的实时帮助和安装包内置 Skill 为准，不在这里复制维护。

## 选择路径

- 普通互联网搜索、最新信息与来源核验：使用 Codex 网页搜索。
- 普通网页浏览、点击、表单和登录态交互：使用 Codex Browser 或专用连接器。
- 用户点名 OpenCLI、项目 Skill 指定站点 adapter，或需要开发/修复 adapter：使用 OpenCLI。

## 最小发现流程

1. 用 `opencli list -f json` 获取实时 registry，但只通过 `jq` 或其他过滤方式读取目标站点，禁止把完整 registry 灌入上下文。
2. 用 `opencli <site> --help` 和 `opencli <site> <command> --help` 确认实时参数。
3. 只有 `COOKIE`、`INTERCEPT`、`UI` 或 `opencli browser` 路径才需要先运行 `opencli doctor`；`PUBLIC` 和 `LOCAL` adapter 不需要浏览器桥接。
4. 所有浏览器命令都使用当前语法：`opencli browser <session> <command>`。
5. CLI 实时帮助与本机行为优先于任何静态说明。

## 按需读取上游说明

不要在全局目录复制 OpenCLI 自带 Skill。需要专项流程时，从当前安装包读取：

```bash
opencli skills read opencli-browser
opencli skills read opencli-adapter-author
opencli skills read opencli-autofix
opencli skills read opencli-browser-sitemap
opencli skills read opencli-sitemap-author
```

修复 adapter 后如需创建上游 issue，先确认 GitHub CLI 可用，并在产生外部写入前征得用户同意。
