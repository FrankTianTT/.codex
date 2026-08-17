# FIB 与阅后即焚订阅更新参考

## 目录

1. [特性与浏览器安全](#特性与浏览器安全)
2. [更新前盘点](#更新前盘点)
3. [下载与比较](#下载与比较)
4. [构建与双重校验](#构建与双重校验)
5. [备份、替换与热重载](#备份替换与热重载)
6. [验收与清理](#验收与清理)
7. [停止条件](#停止条件)

执行本流程前先完整读取 `diagnostics.md`，并用其中的方法发现当前二进制、数据目录、运行配置、Unix socket、mode、TUN、关键 Selector 与真实活动出口。

## 特性与浏览器安全

- FIB 用户中心的“Clash 订阅 → 复制 Clash 订阅”会生成一次性 URL。
- 复制到剪贴板通常不消耗链接；第一次真正下载会生成订阅记录并立即令链接失效。
- 本地保存已消耗 URL 是客户端正常状态；下一次更新必须重新从用户中心获取。
- 只有用户明确要求更新时才点击复制按钮。
- 点击复制后不要抓完整 DOM、表格或页面快照。页面可能把完整 URL 放在隐藏/只读文本框，订阅记录页还可能显示 TOKEN 与用户 IP。
- 优先从浏览器剪贴板 API 或系统剪贴板直接读到进程变量，不把值写入工具输出。
- 只验证 scheme、允许的主机后缀、路径前缀和必要查询参数；日志只记录验证结果。

## 更新前盘点

在取得一次性 URL 前完成：

1. 读取 `profiles.yaml`，动态取得 `current` UID、Remote Profile 文件名、当前选择与旧更新时间；不要硬编码 UID。
2. 对比 Remote Profile 与 `clash-verge.yaml` 的顶层键、节点数、策略组数、规则数。
3. 检查所有 merge、script、rules、proxies、groups 增强文件和选中状态。
4. 记录当前 mode、TUN、mixed-port、DNS、关键 Selector 与活动出口。
5. 准备临时目录、校验命令、备份目标与失败回滚步骤，然后才复制链接。

如果增强脚本或规则增删不是空操作，不能只替换 `proxies`、`proxy-groups`、`rules`。应使用客户端官方更新流程，或完整、可验证地重放增强流水线，否则停止。

## 下载与比较

```bash
clash_update_tmp=$(mktemp -d /tmp/fib-clash-update.XXXXXX)
chmod 700 "$clash_update_tmp"
```

- 从剪贴板把 URL 读入变量并验证，但不打印。
- 通过当前可用代理下载到 `new-profile.yaml`，同时把响应头单独保存。
- 使用 `--fail`、总超时和非交互参数；输出文件而不是正文。
- 下载后立即 `unset` URL 变量；订阅和节点凭据文件设为 `0600`。
- 验证响应不是 HTML，YAML 可解析，且包含 `proxies`、`proxy-groups`、`rules`。
- 解析 `subscription-userinfo` 时只保存 `upload`、`download`、`total`、`expire` 数值，不打印响应头原文。

比较新旧订阅时只输出：

- 文件大小、节点/组/规则数量；
- 新增与删除的节点名称；
- 同名节点发生变化的字段名；
- 顶层哪些 section 发生变化。

不要输出字段值，因为 `password`、Reality 配置和服务器信息可能是敏感凭据。

## 构建与双重校验

运行配置构建原则：

1. 以新 Remote Profile 为订阅来源。
2. 保留当前 Clash Verge 管理的本机覆盖，如 mixed-port、TUN、DNS、controller Unix socket、CORS、profile/store-selected、mode、IPv6、日志级别等。
3. 当前运行配置若用 mixed-port 替代 Remote Profile 的 `port`、`socks-port`、`redir-port`，继续保持替代关系。
4. 新订阅引入的新顶层 section 不应被无意丢弃。
5. 用“旧 Remote Profile 对比旧运行配置”推断本机覆盖，不永久硬编码某个版本的键列表。

Remote Profile 与最终运行配置都必须通过内置 Mihomo 校验：

```bash
"$clash_core" -t -d "$clash_data_dir" -f "$clash_update_tmp/new-profile.yaml"
"$clash_core" -t -d "$clash_data_dir" -f "$clash_update_tmp/new-runtime.yaml"
```

干净退出码不够；检查输出明确包含配置测试成功，并复核节点、组和规则数量。

## 备份、替换与热重载

至少备份：

```text
profiles.yaml
profiles/<current-uid>.yaml
clash-verge.yaml
clash-verge-check.yaml
```

- 备份目录放在 Clash Verge 数据目录下的独立时间戳目录，权限收紧。
- 备份完成后才覆盖；先复制到同目录临时文件，再用原子 `mv` 替换。
- `profiles.yaml` 更新当前 Remote Profile URL、`updated`、响应头 `extra` 和原有 `selected`。

热重载：

```bash
reload_body=$(jq -cn --arg path "$clash_runtime" '{path:$path}')

curl --unix-socket "$clash_socket" --noproxy '*' -sS \
  -X PUT -H 'Content-Type: application/json' \
  --data-binary "$reload_body" \
  'http://localhost/configs?force=true'
```

成功响应应为 HTTP 204。失败时立即恢复四份备份并重新加载旧运行配置，不能留下“文件已换、核心未换”的分裂状态。

## 验收与清理

至少验证：

1. `/version` 与 `/configs` 可读，mode、mixed-port、TUN device 符合更新前记录。
2. 节点数、策略组数与规则数符合新订阅。
3. 关键 Selector 保持原选择，特别是国外流量与 `GLOBAL`。
4. 通过 mixed-port 请求一个 204 测试地址成功。
5. 当前主用节点 `/delay` 成功。
6. 服务商订阅记录显示本次 Clash 更新成功；只读取状态与时间，不输出 IP 或 TOKEN。
7. 本地 `profiles.yaml` 新更新时间、余额与到期时间符合响应头。

验收完成后删除本次 `mktemp` 创建的精确临时目录，保留时间戳备份。删除前验证路径，不使用宽泛通配符或未解析变量。

## 停止条件

- 新配置不是预期格式、缺少核心 section 或 Mihomo 校验失败。
- 新旧差异异常大，且不能从服务商公告或 Profile 结构解释。
- 存在非空增强链，但无法完整重放。
- 无法创建完整备份或回滚路径。
- 热重载失败且旧配置无法恢复。
- 一次性 URL 意外进入日志或 DOM 输出且仍有效；此时先重新生成并作废旧链接。

已验证的常见错误：

- 在准备好校验和备份前复制链接，浪费一次性 URL。
- 复制后读取完整 DOM 或订阅记录表，导致隐藏 URL、TOKEN、邮箱或 IP 进入日志。
- 只替换 Remote Profile，不更新运行配置并热重载，当前核心仍使用旧节点。
- 只热重载临时文件，不保存 `clash-verge.yaml`，重启后回到旧配置。
- 未检查 merge/script 增强便手工重建，丢失规则、代理、DNS 或本机覆盖。
- 没有备份和回滚，更新失败后形成分裂状态。
