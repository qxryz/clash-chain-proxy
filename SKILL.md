---
name: clash-chain-proxy
description: Use when the user wants to configure Clash chain proxy (链式代理) — routing traffic through a front node (前置节点/机场) then a residential IP exit node (住宅IP出口) in Clash Verge, Clash Plus, or any Mihomo/Clash.Meta client. Also use when the user asks to set up dialer-proxy, 链式代理, 串联代理, or two-hop proxy in Clash.
---

# Clash 链式代理 Agent Skill

## 定位

这是一个 AI Agent Skill。安装后，当用户说"配置链式代理"、"dialer-proxy"、"住宅IP串联"等关键词时，agent 自动触发，通过对话收集必要信息，**一键生成可直接导入 Clash 类代理软件的完整配置文件**。

用户不需要懂 Clash 配置语法，只需要提供：
1. 出口节点（住宅IP / 落地节点）的分享链接或参数
2. 前置机场的订阅配置（导出的 YAML 文件 / 订阅 URL / 节点列表）

Agent 自动完成：解析链接 → 提取前置节点 → 生成完整 config.yaml → 用户导入客户端即可使用。

## 链式代理原理

```
本机 → [⚡ 前置自动选择（机场最快节点）] → [🏠 出口节点（住宅IP）] → 目标网站
```

- **前置节点**：机场提供，负责从用户网络环境出墙
- **出口节点**：用户的住宅IP / 落地节点，是目标网站看到的最终 IP
- **dialer-proxy**：Mihomo (Clash.Meta) 内核字段，写在出口节点上，指向前置节点/组，实现流量串联

适用于任何基于 Mihomo (Clash.Meta) 内核的客户端：
- Clash Verge / Clash Verge Rev
- Clash Plus
- Mihomo CLI
- 任何支持 `dialer-proxy` 字段的 Clash 客户端

## Agent 工作流程

### Step 1: 收集用户信息

通过对话向用户收集以下信息（询问顺序建议从上到下）：

1. **出口节点信息**（必填）：
   - 优先要 `vmess://` / `vless://` 分享链接（最方便，直接解码）
   - 或直接提供 server / port / uuid / 协议类型

2. **前置机场信息**（必填）：
   - 优先要机场订阅 URL → agent 下载或要求导出 config.yaml
   - 或用户已在 Clash 客户端导入订阅 → 让用户导出 / 复制完整配置文本
   - 或直接提供前置节点的 `vmess://` / `ss://` 等链接

3. **客户端类型**（必填）：
   - Clash Verge（支持 Merge 叠加）→ 用 `template-merge.yaml`
   - Clash Plus / 其他无 Merge 客户端 → 用 `template-full.yaml`

4. **前置节点筛选**（可选）：
   - 问用户是否要筛选特定地区（如香港/日本/韩国/台湾）
   - 不筛选则用全部节点

### Step 2: 解析出口节点链接

如果用户提供 `vmess://` 链接，解码得到 server / port / uuid：

```bash
python3 -c "import base64; s='<base64部分>'; s += '=' * ((4 - len(s) % 4) % 4); print(base64.b64decode(s).decode())"
```

输出格式：`auto:<uuid>@<server>:<port>`

如果用户提供 `vless://` 链接，格式不同（URL query 参数），按 vless 规范解析：
```
vless://<uuid>@<server>:<port>?<params>#<name>
```

### Step 3: 提取前置节点定义

从用户提供的机场配置 YAML 中提取 `proxies:` 下的节点定义。

**关键**：要跳过信息节点（剩余流量、套餐到期、官网信息等），关键词：
`剩余流量`、`距离下次`、`套餐到期`、`官网`、`客服邮箱`、`测试`

如果想按地区筛选，匹配节点名里的关键词，如：
`Hong Kong`、`Japan`、`Korea`、`TW`、`Singapore`、`China` 等

### Step 4: 生成配置文件

有两种生成方式：

**方式 A — 用脚本生成（推荐，节点多时）**：

```bash
python3 scripts/generate-config.py <airport.yaml> \
    --exit-server <server> \
    --exit-port <port> \
    --exit-uuid <uuid> \
    --exit-type vmess \
    --regions "Hong Kong,Japan,Korea" \
    --output clash-chain-config.yaml
```

脚本自动完成提取 + 生成，输出完整 config.yaml。

**方式 B — 手动填充模板（节点少时）**：

根据客户端类型选模板，手动填入参数：
- Clash Verge → `templates/template-merge.yaml`
- Clash Plus → `templates/template-full.yaml`

### Step 5: 交付配置文件

把生成的配置文件路径告诉用户，并说明导入步骤：

1. 打开 Clash 客户端
2. 导入生成的 config.yaml 文件
3. Proxies 面板选 `🚀 节点选择 → 🏭 链式代理`
4. 打开任意 IP 纯度测试网站验证出口 IP

## 关键字段说明

### `dialer-proxy`

链式代理核心字段，写在**出口节点**上，值为**前置节点名或代理组名**：

```yaml
proxies:
  - name: "🏠 出口节点"
    type: vmess
    server: exit-server.com
    port: 443
    uuid: your-uuid
    alterId: 0
    cipher: auto
    dialer-proxy: "⚡ 前置自动选择"  # ← 出口连接先穿过这个前置组
```

### `url-test` 前置自动选择组

把多个前置节点放进 url-test 组，每 300 秒自动测速选最快的：

```yaml
proxy-groups:
  - name: "⚡ 前置自动选择"
    type: url-test
    proxies:
      - "节点A"
      - "节点B"
      - "节点C"
    url: http://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
    lazy: true
```

### 配置架构

```
┌──────────┐     ┌───────────────────┐     ┌──────────────┐     ┌──────────┐
│  本机     │ →  │ ⚡ 前置自动选择     │ →  │ 🏠 出口节点   │ →  │ 目标网站 │
│ Clash客户端│     │ (url-test 自动    │     │ (住宅IP/落地) │     │          │
└──────────┘     │  选最快前置节点)   │     │ dialer-proxy │     └──────────┘
                 │                   │     │  指向前置组   │
                 └───────────────────┘     └──────────────┘
```

## 常见坑（Agent 必须注意）

### 1. 节点名必须完全匹配

`dialer-proxy` 引用的节点名必须和 `proxies` 里定义的或订阅里的**完全一致**，包括：
- 方括号 `[Hong Kong]`
- 空格
- 连字符 `-` vs 冒号 `:`
- emoji 前缀

如果报 "not found" 错误，99% 是节点名不匹配。让用户在客户端复制完整节点名，或从导出的 YAML 里直接取。

### 2. Clash Plus 不支持 Merge 叠加

Clash Plus 会把 Merge 文件当独立配置加载，找不到订阅里的节点。必须用完整配置模板（`template-full.yaml`），把前置节点完整定义也写进同一个文件。

代价：机场改了节点参数后需要手动同步更新配置文件。

### 3. 跳过信息节点

机场订阅里通常有"剩余流量""套餐到期"等假节点用于显示账户信息，这些必须跳过，不能放进 url-test 组（它们不是真实节点）。

### 4. UUID 解码注意 padding

base64 解码时可能缺 `=` padding 字符，用脚本补全：

```python
s += '=' * ((4 - len(s) % 4) % 4)
```

手动抄 UUID 容易出错，始终用脚本解码。

### 5. vless 和 vmess 出口节点字段不同

| 字段 | vmess | vless |
|------|-------|-------|
| uuid | ✅ | ✅ |
| alterId | ✅ (填 0) | ❌ |
| cipher | ✅ (填 auto) | ❌ |
| flow | ❌ | 可能 (xtls-rprx-vision) |
| reality-opts | ❌ | 可能 |

生成出口节点配置时按协议类型区分字段。

## 验证链式是否生效

启用代理后，浏览器打开任意一个 IP 纯度测试网站查看 IP：
- 显示出口节点的 IP 和 ISP → 链式生效
- 显示前置节点的 IP → 只走了一跳，`dialer-proxy` 没正确串联

## 相关文件

| 文件 | 说明 |
|------|------|
| `scripts/generate-config.py` | 一键生成脚本，从机场配置提取节点生成完整链式配置 |
| `templates/template-merge.yaml` | Clash Verge Merge 配置模板 |
| `templates/template-full.yaml` | 完整独立配置模板（Clash Plus / 其他客户端） |

## 安装

把整个 `clash-chain-proxy/` 目录复制到 agent 的 skills 路径下：

```
~/.agents/skills/clash-chain-proxy/
```

或参考你所使用的 agent 框架文档配置 skill 路径。