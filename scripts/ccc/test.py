import requests
import json
import urllib.parse
import logging
import base64
import subprocess
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import time
import socket

# Set up logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scripts/ccc/results.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# URLs containing node lists
URLS = [
    "https://weoknow.com/data/dayupdate/2/z.txt",
    "https://it.weoknow.com/data/dayupdate/1/z.txt"
]

# Function to decode VMess URL
def decode_vmess(vmess_url):
    try:
        encoded_str = vmess_url.replace('vmess://', '')
        decoded_str = base64.b64decode(encoded_str + '=' * (-len(encoded_str) % 4)).decode('utf-8')
        return json.loads(decoded_str)
    except Exception as e:
        logger.error(f"无法解码 VMess URL {vmess_url}: {e}")
        return None

# Function to parse VLESS or VMess URL and extract configuration
def parse_node(node_url):
    try:
        if node_url.startswith('vless://'):
            parsed = urlparse(node_url)
            address = parsed.hostname
            port = parsed.port or 443
            query = urllib.parse.parse_qs(parsed.query)
            config = {
                'protocol': 'vless',
                'address': address,
                'port': port,
                'id': parsed.username,
                'encryption': query.get('encryption', ['none'])[0],
                'security': query.get('security', ['none'])[0],
                'sni': query.get('sni', [''])[0],
                'type': query.get('type', ['tcp'])[0],
                'host': query.get('host', [''])[0],
                'path': query.get('path', [''])[0],
                'full_config': node_url
            }
            return config
        elif node_url.startswith('vmess://'):
            vmess_data = decode_vmess(node_url)
            if vmess_data:
                config = {
                    'protocol': 'vmess',
                    'address': vmess_data.get('add'),
                    'port': int(vmess_data.get('port', 0)),
                    'id': vmess_data.get('id'),
                    'aid': int(vmess_data.get('aid', 0)),
                    'scy': vmess_data.get('scy', 'auto'),
                    'net': vmess_data.get('net', 'tcp'),
                    'type': vmess_data.get('type', 'none'),
                    'host': vmess_data.get('host', ''),
                    'path': vmess_data.get('path', ''),
                    'tls': vmess_data.get('tls', ''),
                    'sni': vmess_data.get('sni', ''),
                    'full_config': node_url
                }
                return config
        logger.warning(f"不支持的节点格式: {node_url}")
        return None
    except Exception as e:
        logger.error(f"解析节点 {node_url} 出错: {e}")
        return None

# Function to download nodes from a URL
def download_nodes(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        nodes = [line.strip() for line in response.text.splitlines() if line.strip()]
        logger.info(f"从 {url} 下载了 {len(nodes)} 个节点")
        return nodes
    except requests.RequestException as e:
        logger.error(f"无法从 {url} 下载节点: {e}")
        return []

# Function to generate Xray configuration file
def generate_xray_config(node):
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": 1080,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True}
            }
        ],
        "outbounds": [
            {
                "protocol": node['protocol'],
                "settings": {},
                "streamSettings": {}
            },
            {"protocol": "freedom", "tag": "direct"}
        ],
        "routing": {
            "rules": [
                {"type": "field", "outboundTag": "direct", "domain": ["geosite:cn"]}
            ]
        }
    }

    if node['protocol'] == 'vless':
        config['outbounds'][0]['settings'] = {
            "vnext": [{
                "address": node['address'],
                "port": node['port'],
                "users": [{
                    "id": node['id'],
                    "encryption": node['encryption'],
                    "flow": "xtls-rprx-vision" if node['security'] == 'xtls' else ""
                }]
            }]
        }
        config['outbounds'][0]['streamSettings'] = {
            "network": node['type'],
            "security": node['security'] if node['security'] in ['tls', 'xtls', 'reality'] else 'none',
            "tlsSettings": {"serverName": node['sni'], "allowInsecure": False} if node['security'] == 'tls' else {},
            "wsSettings": {"path": node['path'], "headers": {"Host": node['host']}} if node['type'] == 'ws' else {},
            "tcpSettings": {} if node['type'] == 'tcp' else {}
        }
    elif node['protocol'] == 'vmess':
        config['outbounds'][0]['settings'] = {
            "vnext": [{
                "address": node['address'],
                "port": node['port'],
                "users": [{
                    "id": node['id'],
                    "alterId": node['aid'],
                    "security": node['scy']
                }]
            }]
        }
        config['outbounds'][0]['streamSettings'] = {
            "network": node['net'],
            "security": node['tls'] if node['tls'] in ['tls', 'xtls'] else 'none',
            "tlsSettings": {"serverName": node['sni'], "allowInsecure": False} if node['tls'] == 'tls' else {},
            "wsSettings": {"path": node['path'], "headers": {"Host": node['host']}} if node['net'] == 'ws' else {},
            "tcpSettings": {} if node['net'] == 'tcp' else {}
        }

    return config

# Function to test proxy connectivity using Xray
def test_node_connectivity(node):
    if not node:
        return None, False
    address = node['address']
    full_config = node['full_config']
    
    try:
        # Create temporary Xray config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
            json.dump(generate_xray_config(node), temp_file, indent=2)
            config_path = temp_file.name

        # Start Xray in the background
        xray_process = subprocess.Popen(
            ['xray', 'run', '-c', config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait briefly to ensure Xray starts
        time.sleep(2)

        # Check if Xray is running
        if xray_process.poll() is not None:
            stderr = xray_process.communicate()[1]
            logger.error(f"Xray 启动失败 for {address} ({full_config[:30]}...): {stderr}")
            os.unlink(config_path)
            return full_config, False

        # Test connectivity through the proxy
        test_url = 'https://api.github.com'  # More reliable test endpoint
        proxies = {'http': 'socks5://127.0.0.1:1080', 'https': 'socks5://127.0.0.1:1080'}
        response = requests.get(test_url, proxies=proxies, timeout=10, verify=False)
        success = response.status_code == 200
        status = '可连接' if success else '不可连接'
        logger.info(f"节点 {address} ({full_config[:30]}...): {status}")

        # Clean up
        xray_process.terminate()
        try:
            xray_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            xray_process.kill()
        os.unlink(config_path)
        
        return full_config, success
    except requests.exceptions.RequestException as e:
        logger.error(f"测试 {address} ({full_config[:30]}...) 出错: {e}")
        return full_config, False
    except Exception as e:
        logger.error(f"测试 {address} ({full_config[:30]}...) 未知错误: {e}")
        return full_config, False

# Main function
def main():
    # Download all nodes
    all_nodes = []
    for url in URLS:
        nodes = download_nodes(url)
        all_nodes.extend([(node, urlparse(url).netloc) for node in nodes])

    if not all_nodes:
        logger.error("未下载到任何节点，退出。")
        return

    # Parse nodes and check for duplicates
    parsed_nodes = []
    for node, source in all_nodes:
        parsed = parse_node(node)
        if parsed:
            parsed['source'] = source
            parsed_nodes.append(parsed)

    # Check for duplicates based on full configuration
    node_configs = [node['full_config'] for node in parsed_nodes]
    node_counts = {}
    for config in node_configs:
        node_counts[config] = node_counts.get(config, 0) + 1

    duplicates = [(config, count) for config, count in node_counts.items() if count > 1]
    if duplicates:
        logger.warning("发现重复节点：")
        for config, count in duplicates:
            logger.warning(f"节点 {config[:30]}... 出现 {count} 次")
    else:
        logger.info("未发现重复节点。")

    # Test connectivity for unique nodes
    unique_nodes = list(set(node['full_config'] for node in parsed_nodes))
    parsed_unique = [node for node in parsed_nodes if node['full_config'] in unique_nodes]
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(test_node_connectivity, parsed_unique))

    # Summarize results
    reachable = [config for config, status in results if status]
    unreachable = [config for config, status in results if not status]

    logger.info("\n总结：")
    logger.info(f"总计唯一节点数：{len(unique_nodes)}")
    logger.info(f"可连接节点数：{len(reachable)}")
    if reachable:
        logger.info("可连接节点：" + ", ".join([config[:30] + '...' for config in reachable]))
    logger.info(f"不可连接节点数：{len(unreachable)}")
    if unreachable:
        logger.info("不可连接节点：" + ", ".join([config[:30] + '...' for config in unreachable]))

if __name__ == "__main__":
    main()
