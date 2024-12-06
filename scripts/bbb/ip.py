import requests
from bs4 import BeautifulSoup

def extract_ip_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # 如果请求失败，抛出异常
    
    # 解析网页
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 提取 IP 数据
    ip_data = []
    table = soup.find('table')
    rows = table.find_all('tr')
    for row in rows[1:]:
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
    ip_data = extract_ip_data(url)
    # 将数据保存到文件
    with open('scripts/bbb/port_data.txt', 'a', encoding='utf-8') as file:
        for ip in ip_data:
            ip_with_port = f"{ip}:443#优选443"
            file.write(f"{ip_with_port}\n")

print("IP data extracted and saved successfully.")
