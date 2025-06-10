import requests
import json
import urllib.parse
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import base64
import time

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
        # Remove 'vmess://' prefix and decode base64
        encoded_str = vmess_url.replace('vmess://', '')
        decoded_str = base64.b64decode(encoded_str).decode('utf-8')
        return json.loads(decoded_str)
    except Exception as e:
        logger.error(f"无法解码 VMess URL {vmess_url}: {e}")
        return None

# Function to parse VLESS or VMess URL and extract address
def parse_node(node_url):
    try:
        if node_url.startswith('vless://'):
            parsed = urlparse(node_url)
            address = parsed.hostname
            port = parsed.port or 443
            return {'address': address, 'port': port, 'full_config': node_url}
        elif node_url.startswith('vmess://'):
            vmess_data = decode_vmess(node_url)
            if vmess_data:
                address = vmess_data.get('add')
                port = int(vmess_data.get('port', 0))
                return {'address': address, 'port': port, 'full_config': node_url}
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

# Function to test proxy connectivity
def test_node_connectivity(node_info):
    if not node_info:
        return None, False
    address = node_info['address']
    full_config = node_info['full_config']
    
    # For simplicity, test connectivity by checking if the address is reachable
    # Ideally, you'd use a proxy client library (e.g., v2ray) to test the full proxy
    test_url = 'http://www.google.com'  # Test endpoint
    proxies = None  # Placeholder: actual proxy client setup needed
    
    try:
        # Simplified check; replace with actual proxy client for real testing
        response = requests.get(f'http://{address}', timeout=5, allow_redirects=False)
        success = response.status_code in range(200, 400)
        status = '可连接' if success else '不可连接'
        logger.info(f"节点 {address} ({full_config[:30]}...): {status}")
        return full_config, success
    except requests.RequestException as e:
        logger.error(f"测试 {address} ({full_config[:30]}...) 出错: {e}")
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
    
    with ThreadPoolExecutor(max_workers=10) as executor:
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
