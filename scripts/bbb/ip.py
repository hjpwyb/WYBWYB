import requests
from bs4 import BeautifulSoup

def extract_ip_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    response = requests.get(url, headers=headers)
    
    # 确保请求成功
    response.raise_for_status()  
    
    # 解析网页
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 调试：打印网页内容（可以帮助检查是否有表格）
    # print(soup.prettify()) 
    
    # 尝试找到表格
    table = soup.find('table')
    if not table:
        print(f"Table not found on {url}")
        return []
    
    # 提取 IP 数据
    ip_data = []
    rows = table.find_all('tr')
    
    for row in rows[1:]:  # 跳过表头
        columns = row.find_all('td')
        if len(columns) == 5:  # 确保该行有 5 列
            ip = columns[1].text.strip()  # 获取第二列（IP列）
            ip_data.append(ip)
    
    return ip_data

# 使用这个函数抓取 IP 数据
urls = [
    "https://ipdb.030101.xyz/bestcf/",
    "https://stock.hostmonit.com/CloudFlareYes"
]

for url in urls:
    print(f"Extracting IP data from {url}...")
    try:
        ip_data = extract_ip_data(url)
        if ip_data:
            # 将数据保存到文件
            with open('scripts/bbb/port_data.txt', 'a', encoding='utf-8') as file:
                for ip in ip_data:
                    ip_with_port = f"{ip}:443#优选443"
                    file.write(f"{ip_with_port}\n")
            print(f"Data from {url} saved successfully.")
        else:
            print(f"No IP data found for {url}")
    except requests.exceptions.RequestException as e:
        print(f"Error extracting data from {url}: {e}")
