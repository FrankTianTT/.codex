# Clash Verge Rev CLI 诊断参考

## 目录

1. [目标与边界](#目标与边界)
2. [先发现，不硬编码](#先发现不硬编码)
3. [Unix socket 只读查询](#unix-socket-只读查询)
4. [判断当前节点](#判断当前节点)
5. [连接、流量与网络失败](#连接流量与网络失败)
6. [全部节点延迟测试](#全部节点延迟测试)
7. [已验证的失败模式](#已验证的失败模式)

本文以 macOS Apple Silicon 上的 Clash Verge Rev 2.5.x 与 Mihomo 1.19.x 为已验证样本。版本、路径和控制端点都必须现场发现；Ubuntu 或其他客户端只复用原则，不照搬 macOS 路径。

## 目标与边界

- GUI 版 Clash Verge Rev 自带 Mihomo CLI，也可以通过运行中核心的 Unix socket 使用标准 REST API。
- 只读查询优先走 Unix socket，不为控制额外开放 TCP controller。
- 如果用户只需要完成一个下载或访问任务，优先对该命令临时指定代理；不要永久修改 shell、Git、npm、系统代理或项目配置。
- 切换节点或 mode、修改 TUN/系统代理、关闭连接或重载核心前，必须有用户明确授权。
- 不输出订阅 URL、TOKEN、代理 `password`、Reality 密钥、`secret`、账号邮箱或用户公网 IP。

## 先发现，不硬编码

### macOS 已验证候选位置

```text
/Applications/Clash Verge.app/Contents/MacOS/clash-verge
/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo
~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/
```

```bash
clash_core='/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo'
clash_data_dir="$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"
clash_runtime="$clash_data_dir/clash-verge.yaml"
"$clash_core" -v
"$clash_core" -h
```

这些变量只是初始候选值。执行任何写操作前，必须用实际进程参数校正：

```bash
ps -ax -o pid=,ppid=,user=,command= | rg -i 'clash|mihomo|verge'
launchctl print system/io.github.clash-verge-rev.clash-verge-rev.service
lsof -nP -iTCP -sTCP:LISTEN | rg -i 'clash|mihomo|verge'
```

已验证的服务模式启动参数形态是：

```text
verge-mihomo -d <data-dir> -f <runtime-config> -ext-ctl-unix <socket-path>
```

2026-08-17 的样本把 Mihomo API 绑定在 `/tmp/verge/verge-mihomo.sock`。应用自身监听的 `127.0.0.1:33331` 不是标准 Mihomo REST API，访问 `/version` 会得到 404。

如果进程列表、localhost 或 Unix socket 被执行沙箱拦截，应申请范围明确的只读权限；不要把沙箱拒绝误判为 Clash 未运行。

## Unix socket 只读查询

路径必须来自现场发现：

```bash
clash_socket='/tmp/verge/verge-mihomo.sock'

curl --unix-socket "$clash_socket" --noproxy '*' -sS \
  http://localhost/version | jq

curl --unix-socket "$clash_socket" --noproxy '*' -sS \
  http://localhost/configs | jq '{mode,"mixed-port":.["mixed-port"],tun}'
```

策略组：

```bash
curl --unix-socket "$clash_socket" --noproxy '*' -sS \
  http://localhost/proxies |
jq '.proxies | to_entries |
    map(select(.value.type == "Selector") |
        {group:.key,current:.value.now})'
```

活动连接的真实出口：

```bash
curl --unix-socket "$clash_socket" --noproxy '*' -sS \
  http://localhost/connections |
jq '{active:(.connections|length),
     by_actual_outbound:(.connections |
       map(.chains[0] // "UNKNOWN") | group_by(.) |
       map({outbound:.[0],connections:length}) |
       sort_by(-.connections))}'
```

## 判断当前节点

Rule 模式下不存在一个代表全部流量的“当前节点”：

- `GLOBAL` 的选择主要用于 Global 模式，不能代表 Rule 模式的实际出口。
- 同时报告关键规则组，例如“国外流量”、Telegram、Netflix、YouTube、Apple 与哔哩哔哩。
- 从活动连接的 `chains[0]` 汇总真实出口，区分代理节点与 `DIRECT`。
- 已建立的连接可能继续使用切换前的出口；策略选择与活动连接需要分开报告。

## 连接、流量与网络失败

- `/connections` 的 `downloadTotal`、`uploadTotal` 是核心运行期统计，不等于套餐结算流量。
- `/providers/proxies` 只有真正的 Provider 才可能提供 `subscriptionInfo`；内联配置常显示 `vehicleType: Compatible` 且 `subscriptionInfo: null`。
- `profiles.yaml` 当前 Remote Profile 的 `extra.upload/download/total/expire` 可能是旧缓存，必须同时报告更新时间。
- 服务商用户中心的剩余百分比、剩余容量和到期时间通常更权威；“最近 30 天汇总”可能采用不同口径。

诊断下载失败时：

1. 保存原始错误类型：DNS、连接超时、TLS、HTTP 状态、认证、限流或应用配置。
2. 检查 Clash 核心、mixed-port 与 TUN 是否正在运行，但不主动启停。
3. 在不写入持久配置的前提下，用单条命令的 `--proxy http://127.0.0.1:<mixed-port>` 或等效参数重试。
4. 如果代理路径成功而当前路径失败，说明本机代理可作为任务级回退；如果两者都失败，继续检查目标服务、DNS、证书或项目配置。
5. `--noproxy` 只能忽略 HTTP 代理环境变量，不能绕过已经启用的 TUN；不要把它误称为完全直连测试。

## 全部节点延迟测试

延迟测试不是吞吐带宽测试。报告测试 URL、单节点超时、测试时间和成功/失败数。

```bash
node_name='待测试节点名称'
node_encoded=$(printf '%s' "$node_name" | jq -sRr @uri)

curl --unix-socket "$clash_socket" --noproxy '*' -sS --max-time 12 \
  "http://localhost/proxies/${node_encoded}/delay?timeout=8000&url=https%3A%2F%2Fwww.gstatic.com%2Fgenerate_204" |
jq
```

批量测试规则：

- 从 `/proxies` 过滤实际协议节点，例如 Shadowsocks、Vless、Vmess；不要把 Selector、Direct、Reject 当物理节点。
- 使用 8–10 个有界并发，并为每个节点设置超时。
- 区分成功延迟、Timeout 与其他错误，汇总延迟区间、最快和最慢节点。
- `PUT /providers/proxies/<name>/healthcheck` 对 `Compatible` Provider 可能返回 404；此时改用逐节点 `/delay`。
- 测速会更新 Mihomo 延迟历史并产生少量真实测试流量，但不应切换策略组。

## 已验证的失败模式

- 把 Clash Verge 自身的 localhost 端口当 Mihomo API：标准路由返回 404。
- 只看 `GLOBAL` 就回答“当前节点”：Rule 模式下结论错误。
- 把核心累计流量或旧 Profile 缓存当实时余额：口径或时间错误。
- 对 Compatible Provider 调用批量 healthcheck：返回 404，应逐节点 `/delay`。
- 网络命令在沙箱中失败后直接归因于 Clash：应先做窄范围权限验证。
- 为解决一次下载而永久写入系统、Git、npm 或 shell 代理：超出必要范围。
