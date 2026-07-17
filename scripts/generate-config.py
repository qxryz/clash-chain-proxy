#!/usr/bin/env python3
"""
Clash 链式代理配置生成脚本

从机场订阅导出的 config.yaml 中批量提取节点，生成链式代理配置文件。

用法：
    python3 generate-config.py <airport-config.yaml> [options]

选项：
    --exit-server SERVER     出口节点地址 (必填)
    --exit-port PORT         出口节点端口 (必填)
    --exit-uuid UUID         出口节点 UUID (必填)
    --exit-type TYPE         出口节点协议: vmess/vless (默认: vmess)
    --regions REGIONS        筛选地区，逗号分隔 (默认: 全部)
                               例: "Hong Kong,Japan,Korea,TW,Singapore"
    --skip-info              跳过信息节点 (剩余流量/套餐到期等，默认开启)
    --output FILE           输出文件路径 (默认: chain-proxy-config.yaml)
    --group-name NAME       前置自动选择组名称 (默认: ⚡ 前置自动选择)

示例：
    # 提取所有港日韩台新节点
    python3 generate-config.py airport.yaml \\
        --exit-server sp-hk1.kookeey.info \\
        --exit-port 10621 \\
        --exit-uuid 9e1c607a-xxxx-xxxx-xxxx-xxxxxxxxxxxx \\
        --regions "Hong Kong,Japan,Korea,TW,Singapore" \\
        --output clash-chain-config.yaml
"""

import sys
import os
import argparse

try:
    import yaml
except ImportError:
    print("Error: PyYAML not installed. Run: pip3 install pyyaml")
    sys.exit(1)


# 默认跳过的信息节点关键词
SKIP_KEYWORDS = [
    '剩余流量', '距离下次', '套餐到期', '官网', '客服邮箱',
    '剩余流量', '到期', '刷新', '官网', '客服',
]


def parse_args():
    parser = argparse.ArgumentParser(
        description='Clash 链式代理配置生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('airport_config', help='机场订阅导出的 config.yaml 路径')
    parser.add_argument('--exit-server', required=True, help='出口节点服务器地址')
    parser.add_argument('--exit-port', required=True, type=int, help='出口节点端口')
    parser.add_argument('--exit-uuid', required=True, help='出口节点 UUID')
    parser.add_argument('--exit-type', default='vmess', choices=['vmess', 'vless'],
                        help='出口节点协议类型 (默认: vmess)')
    parser.add_argument('--regions', default='', help='筛选地区，逗号分隔')
    parser.add_argument('--skip-info', action='store_true', default=True,
                        help='跳过信息节点 (默认开启)')
    parser.add_argument('--output', default='chain-proxy-config.yaml',
                        help='输出文件路径 (默认: chain-proxy-config.yaml)')
    parser.add_argument('--group-name', default='⚡ 前置自动选择',
                        help='前置自动选择组名称')
    parser.add_argument('--no-skip-info', dest='skip_info', action='store_false',
                        help='不跳过信息节点')
    return parser.parse_args()


def load_airport_config(path):
    """Load a YAML file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def filter_nodes(proxies, regions=None, skip_info=True):
    """Filter proxy nodes by region and skip info nodes."""
    region_list = [r.strip() for r in regions.split(',')] if regions else []

    filtered = []
    for p in proxies:
        name = p.get('name', '')

        # Skip info nodes
        if skip_info and any(kw in name for kw in SKIP_KEYWORDS):
            continue

        # Filter by region
        if region_list:
            if not any(r.lower() in name.lower() for r in region_list):
                continue

        filtered.append(p)

    return filtered


def build_config(front_nodes, exit_node, group_name):
    """Build the complete chain proxy config."""
    front_names = [n['name'] for n in front_nodes]

    # Exit node with dialer-proxy
    exit_config = {
        'name': '🏠 出口节点',
        'type': exit_node['type'],
        'server': exit_node['server'],
        'port': exit_node['port'],
        'uuid': exit_node['uuid'],
        'udp': True,
    }

    if exit_node['type'] == 'vmess':
        exit_config['alterId'] = 0
        exit_config['cipher'] = 'auto'

    exit_config['dialer-proxy'] = group_name

    all_proxies = front_nodes + [exit_config]

    config = {
        'mixed-port': 7890,
        'allow-lan': False,
        'mode': 'rule',
        'log-level': 'info',
        'ipv6': False,
        'unified-delay': True,
        'dns': {
            'enable': True,
            'enhanced-mode': 'fake-ip',
            'fake-ip-range': '198.18.0.1/16',
            'nameserver': ['223.5.5.5', '119.29.29.29'],
            'fallback': ['tls://8.8.8.8:853', 'tls://1.1.1.1:853'],
            'fallback-filter': {'geoip': True, 'geoip-code': 'CN'},
        },
        'proxies': all_proxies,
        'proxy-groups': [
            {
                'name': group_name,
                'type': 'url-test',
                'proxies': front_names,
                'url': 'http://www.gstatic.com/generate_204',
                'interval': 300,
                'tolerance': 50,
                'lazy': True,
            },
            {
                'name': '🏭 链式代理',
                'type': 'select',
                'proxies': ['🏠 出口节点', group_name, 'DIRECT'],
            },
            {
                'name': '🚀 节点选择',
                'type': 'select',
                'proxies': ['🏭 链式代理', group_name, 'DIRECT'],
            },
        ],
        'rules': [
            'IP-CIDR,127.0.0.0/8,DIRECT',
            'IP-CIDR,192.168.0.0/16,DIRECT',
            'IP-CIDR,10.0.0.0/8,DIRECT',
            'GEOIP,CN,DIRECT',
            'MATCH,🚀 节点选择',
        ],
    }
    return config


def main():
    args = parse_args()

    # Load airport config
    if not os.path.exists(args.airport_config):
        print(f"Error: file not found: {args.airport_config}")
        sys.exit(1)

    print(f"Loading airport config: {args.airport_config}")
    data = load_airport_config(args.airport_config)
    proxies = data.get('proxies', [])
    print(f"Total proxies in airport config: {len(proxies)}")

    # Filter nodes
    front_nodes = filter_nodes(
        proxies,
        regions=args.regions if args.regions else None,
        skip_info=args.skip_info
    )
    print(f"Front nodes after filtering: {len(front_nodes)}")

    if not front_nodes:
        print("Error: no front nodes found after filtering!")
        sys.exit(1)

    # Show filtered nodes
    if args.regions:
        print(f"Region filter: {args.regions}")
    for n in front_nodes:
        print(f"  - {n['name']}")

    # Build exit node
    exit_node = {
        'type': args.exit_type,
        'server': args.exit_server,
        'port': args.exit_port,
        'uuid': args.exit_uuid,
    }

    # Build config
    config = build_config(front_nodes, exit_node, args.group_name)

    # Write output
    output_path = args.output
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False,
                  sort_keys=False, width=1000)

    print(f"\n✅ Config written to: {output_path}")
    print(f"   Front nodes: {len(front_nodes)}")
    print(f"   Exit node: 🏠 出口节点 ({args.exit_type})")
    print(f"   Group: {args.group_name}")
    print(f"\nImport this file into your Clash client and select '🏭 链式代理'")


if __name__ == '__main__':
    main()