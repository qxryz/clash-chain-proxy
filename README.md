# Clash 链式代理 Agent Skill

> ⚠️ 正在测试中。此 skill 仅从我的真实配置流程总结而来，未做完整测试。

安装到 AI Agent 后，用户说一句话就能生成可直接导入 Clash 的链式代理配置文件。

> 本项目仅提供配置文件生成工具，不提供任何代理服务器资源，不参与任何代理服务的运营。使用者应遵守所在地区的法律法规，一切违法行为与本项目及作者无关。

## 让你的 agent 安装本 skill

将下面这句话发给你的 AI Agent（Claude Code、Codex、opencode 等）：

```
帮我根据 https://github.com/qxryz/clash-chain-proxy 安装这个 skill，安装结束后提醒我启动
```

## 使用

安装后对 agent 说：

```
帮我配置 Clash 链式代理，我有住宅IP和机场订阅
```

Agent 会：
1. 问你要出口节点（住宅IP）的 `vmess://` / `vless://` 链接或参数
2. 问你要前置机场的订阅 URL / 导出的 config.yaml
3. 问你客户端类型（Clash Verge / Clash Plus）
4. 可选问要不要按地区筛选前置节点
5. **生成完整 config.yaml**，告诉你导入步骤
6. 提示你打开任意 IP 纯度测试网站验证出口 IP

用户需要提供：

| 信息 | 必填 | 示例 |
|------|------|------|
| 出口节点链接 | ✅ | `vmess://...` 或 server/port/uuid |
| 前置机场配置 | ✅ | 订阅 URL 或导出的 config.yaml |
| 客户端类型 | ✅ | Clash Verge / Clash Plus |
| 前置节点筛选 | 可选 | "只要香港日本韩国" |

生成结果导入后，Proxies 面板选 `🚀 节点选择 → 🏭 链式代理` 即可。

## 前置 / 出口节点协议说明

前置和出口节点协议**互相独立**，各自按自己的协议配置，只要 Mihomo 内核支持即可。

| | 前置节点 | 出口节点 |
|---|---|---|
| 来源 | 机场订阅 | 用户自有（住宅IP/落地） |
| 协议 | 任意：vmess/vless/anytls/ss/trojan/hysteria2... | 通常 vmess / vless |
| 承担角色 | 出墙跳板，不做出口 | 最终出口，目标网站看到的 IP |
| dialer-proxy | ❌ 不写 | ✅ 写，指向前置节点/组 |
| 串联方式 | 放入 `⚡ 前置自动选择` url-test 组 | 单独定义，挂 `dialer-proxy` |

几个关键点：
- 前置节点协议和出口节点协议**不相关**，不同协议混搭完全没问题
- vmess 出口字段：`uuid` / `alterId`（填 0）/ `cipher`（填 auto）
- vless 出口字段：`uuid` / 可能带 `flow: xtls-rprx-vision` 和 `reality-opts`
- 前置节点从机场订阅里原样复制，不要改协议字段
- 机场订阅里有"剩余流量""套餐到期"等假节点，**必须跳过**，Agent 会自动过滤

## 两种客户端配置的区别

| | Clash Verge | Clash Plus |
|---|---|---|
| Merge 叠加 | ✅ 只写出口节点 + 引用订阅节点名 | ❌ |
| 完整配置 | ✅ 也可以 | ✅ 必须用完整配置 |
| 节点更新 | 订阅自动更新，Merge 不用改 | 需重新生成配置 |

Agent 会根据用户客户端类型自动选择对应方式。

## 文件结构

```
.
├── SKILL.md                    # Agent 指令（触发后按此执行）
├── scripts/generate-config.py # 一键生成脚本
├── templates/
│   ├── template-merge.yaml     # Clash Verge Merge 模板
│   └── template-full.yaml      # 完整配置模板（Clash Plus 等）
├── README.md
└── LICENSE
```

## 完整配置流程案例

不是我的，只讲流程和坑。

### 背景

国内买了海外静态住宅 IP（VMess 协议），想让目标网站看到的是住宅 IP 而不是机场 IP。手头有普通机场订阅做出墙跳板。

### 客户端

用 Clash Plus。内核 Mihomo（Clash.Meta），支持 `dialer-proxy`，但不吃 Merge 文件，必须把前置节点定义也写进同一份 config.yaml。

### 步骤

1. **解码住宅 IP 链接**
   住宅 IP 商家给了 `vmess://...` 链接，base64 编码。用 python 解：
   ```bash
   python3 -c "import base64; s='<base64部分>'; s += '=' * ((4 - len(s) % 4) % 4); print(base64.b64decode(s).decode())"
   ```
   得到 `auto:<uuid>@<server>:<port>`。手动抄容易错，始终用脚本。

2. **导入机场订阅到客户端**
   Clash Plus 里直接粘贴订阅 URL，下载完整配置。导出得到一份完整的 YAML，里面有所有节点定义。

3. **找前置节点名**
   在客户端节点列表里看中一个想用作前置的节点，复制它的完整名字。注意：
   - 机场起的节点名带方括号前缀，比如 `[Hong Kong] 香港2-极速`
   - 之前自己写成 `香港2:极速`，报 not found 才发现要连方括号一起

4. **判断客户端是否支持 Merge**
   - Clash Verge 支持 Merge 叠加：新建 Merge 文件，只写出口节点和 `dialer-proxy`，套在机场订阅上
   - Clash Plus 不支持 Merge：必须把前置节点的完整定义也抄进同一个 config.yaml
   代价：机场改节点参数后，Clash Plus 版配置要手动同步

5. **写配置文件**
   把前置节点定义从机场导出的 YAML 里整段复制进来，加一个出口节点：
   ```yaml
   - name: "🏠 出口节点"
     type: vmess
     server: <住宅IP服务器>
     port: <端口>
     uuid: <uuid>
     alterId: 0
     cipher: auto
     dialer-proxy: "⚡ 前置自动选择"   # ← 关键
   ```
   再建一个 `url-test` 组把前置节点全塞进去，复制节点名时一个个核对，不能手敲。

6. **导入并选节点**
   Clash Plus → 新建配置 → 粘贴 → 启用 → Proxies 面板选 `🚀 节点选择 → 🏭 链式代理`

7. **验证出口**
   浏览器开任意一个测试 IP 纯度的网站都行。看到住宅 IP 对应的 ISP 就说明链式生效，看到机场的 IP 就是只走了一跳。

### 踩过的坑

- **UUID 抄错一位就连不上**。一度把 `ea3e` 抄成了 `ee3e`，排查半天。始终用脚本解码。
- **节点名必须字符完全匹配**，方括号、空格、连字符、emoji 前缀都不能漏。
- **Clash Plus 不吃 Merge 文件**。报 not found 的根因，解法是把前置节点也写进同一份配置。
- **机场订阅里有假节点**：剩余流量、套餐到期、官网信息这类，它们不是真代理节点，塞进 url-test 组测速时会全失败，必须跳过。

### 想要自动选最快前置

把想要的前置节点丢进一个 `url-test` 组让它自动测速：
```yaml
proxy-groups:
  - name: "⚡ 前置自动选择"
    type: url-test
    proxies: [节点A, 节点B, 节点C]
    url: http://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
    lazy: true
```
出口节点的 `dialer-proxy` 指向这个组名就行。每 300 秒自动测速切换最快的。

### 后续维护

- 机场改了节点服务器/端口/REALITY 公钥，配置里写死的那些要手动同步
- 想换前置节点，改 `dialer-proxy` 的值或调整 url-test 组里的列表
- 定期开任意 IP 纯度测试网站确认出口还是住宅 IP

## License

MIT
