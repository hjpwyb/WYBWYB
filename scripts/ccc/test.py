import requests
import subprocess
import platform
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URLs to download
URLS = [
    "https://weoknow.com/data/dayupdate/2/z.txt",
    "https://it.weoknow.com/data/dayupdate/1/z.txt"
]

# Function to download nodes from a URL
def download_nodes(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        nodes = [line.strip() for line in response.text.splitlines() if line.strip()]
        logger.info(f"Downloaded {len(nodes)} nodes from {url}")
        return nodes
    except requests.RequestException as e:
        logger.error(f"Failed to download from {url}: {e}")
        return []

# Function to test connectivity of a node
def test_node_connectivity(node):
    # Determine ping command based on OS
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    try:
        # Run ping with 2 attempts, timeout after 2 seconds
        result = subprocess.run(
            ['ping', param, '2', '-w', '2', node],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        success = result.returncode == 0
        status = 'reachable' if success else 'unreachable'
        logger.info(f"Node {node}: {status}")
        return node, success
    except (subprocess.SubprocessError, TimeoutError) as e:
        logger.error(f"Error pinging {node}: {e}")
        return node, False

# Main function
def main():
    # Download all nodes
    all_nodes = []
    for url in URLS:
        nodes = download_nodes(url)
        all_nodes.extend([(node, urlparse(url).netloc) for node in nodes])

    if not all_nodes:
        logger.error("No nodes downloaded. Exiting.")
        return

    # Check for duplicates
    node_counts = {}
    for node, source in all_nodes:
        node_counts[node] = node_counts.get(node, 0) + 1

    duplicates = [(node, count) for node, count in node_counts.items() if count > 1]
    if duplicates:
        logger.warning("Found duplicates:")
        for node, count in duplicates:
            logger.warning(f"Node {node} appears {count} times")
    else:
        logger.info("No duplicates found.")

    # Test connectivity using ThreadPoolExecutor for parallel execution
    unique_nodes = list(node_counts.keys())
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(test_node_connectivity, unique_nodes))

    # Summarize results
    reachable = [node for node, status in results if status]
    unreachable = [node for node, status in results if not status]

    logger.info("\nSummary:")
    logger.info(f"Total nodes: {len(unique_nodes)}")
    logger.info(f"Reachable nodes: {len(reachable)}")
    if reachable:
        logger.info("Reachable nodes: " + ", ".join(reachable))
    logger.info(f"Unreachable nodes: {len(unreachable)}")
    if unreachable:
        logger.info("Unreachable nodes: " + ", ".join(unreachable))

if __name__ == "__main__":
    main()
