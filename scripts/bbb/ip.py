import requests

def fetch_csv_data(url):
    # 获取 CSV 文件内容
    response = requests.get(url)
    response.raise_for_status()  # 如果请求失败，抛出异常

    # 获取 CSV 内容并解析
    csv_content = response.text
    return parse_csv(csv_content)

def parse_csv(csv_content):
    # 按行分割
    lines = csv_content.split("\n")
    # 过滤空行
    lines = [line.strip() for line in lines if line.strip()]

    # 获取表头（CSV 第一行）
    headers = lines[0].split(",")

    # 提取 IP 数据（假设 IP 在第二列）
    ip_data = []
    for line in lines[1:]:
        columns = line.split(",")
        if len(columns) >= 2:  # 确保有足够的列
            ip = columns[1].strip()  # 假设 IP 在第二列
            ip_data.append(ip)

    return ip_data

# CSV 文件的 URL
csv_url = 'https://ipdb.030101.xyz/api/bestcf.csv'

try:
    ip_data = fetch_csv_data(csv_url)
    if ip_data:
        # 保存数据到文件
        with open('scripts/bbb/port_data.txt', 'a', encoding='utf-8') as file:
            for ip in ip_data:
                ip_with_port = f"{ip}:443#优选443"
                file.write(f"{ip_with_port}\n")
        print("Data saved successfully.")
    else:
        print("No IP data found.")
except Exception as e:
    print(f"Error extracting data: {e}")
