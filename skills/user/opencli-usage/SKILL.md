---
name: opencli-usage
description: OpenCLI 的轻量路由说明。当用户明确指定网站或平台且当前 registry 有合适的只读 adapter、项目 Skill 依赖 OpenCLI、用户点名 OpenCLI，或需要开发和调试 adapter 时使用。普通开放网页搜索使用 Codex 网页搜索，普通网页交互使用 Codex Browser 或专用连接器。
---

# OpenCLI 路由

只保留 Codex 与当前 OpenCLI 安装之间的稳定边界。命令细节以当前 CLI 的实时帮助和安装包内置 Skill 为准，不在这里复制维护。

## 选择路径

- 普通互联网搜索、最新信息与来源核验：使用 Codex 网页搜索。
- 普通网页浏览、点击、表单和登录态交互：使用 Codex Browser 或专用连接器。
- 明确站点已有只读 adapter，且任务需要站内搜索、结构化列表、评论、指标或登录态数据：主动使用 OpenCLI。
- 用户点名 OpenCLI、项目 Skill 指定 adapter，或需要开发/修复 adapter：使用 OpenCLI。
- 发布、评论、点赞、关注、删除、上传、下单等写操作：即使 adapter 可用，也先取得用户明确授权。

## 最小发现流程

1. 用定向过滤读取实时 registry，禁止把完整 registry 灌入上下文：

   ```bash
   opencli list -f json | jq '[.[] | select(.site == "<site>")]'
   ```

   同时检查 `access` 和 `strategy`；`access: write` 必须按写操作处理，即使命令名称看起来像查询。
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
