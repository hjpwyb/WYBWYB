import requests
from bs4 import BeautifulSoup

# 网页 URL 列表
urls = [
    "https://ipdb.030101.xyz/bestcf/",
    "https://stock.hostmonit.com/CloudFlareYes"
]

# 函数：解析并提取数据
def extract_ip_data(url):
    # 获取网页内容
    response = requests.get(url)
    response.raise_for_status()  # 如果请求失败，抛出异常

    # 解析网页
    soup = BeautifulSoup(response.text, 'html.parser')

    # 找到表格
    table = soup.find('table')

    # 找到所有表格行
    rows = table.find_all('tr')

    ip_data = []

    # 遍历表格行并提取 IP 数据
    for row in rows[1:]:  # 跳过表头
        columns = row.find_all('td')
        if len(columns) >= 2:  # 确保该行至少有2列，防止索引错误
            ip = columns[1].text.strip()  # 获取第二列（通常是IP列，但根据网页结构需要调整）
            ip_with_port = f"{ip}:443#优选443"
            ip_data.append(ip_with_port)

    return ip_data

# 打开文件并写入数据
with open('scripts/bbb/port_data.txt', mode='w', encoding='utf-8') as file:
    for url in urls:
        print(f"Extracting IP data from {url}...")
        ip_data = extract_ip_data(url)
        for ip_with_port in ip_data:
            file.write(f"{ip_with_port}\n")  # 将拼接后的 IP 写入文件，每个 IP 占一行

print("IP data with ':443#优选443' fetched and saved to scripts/bbb/port_data.txt")
