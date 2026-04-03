import requests
import csv
import os
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# ========== 配置 ==========
# 怀柔镇坐标
HUAIROU_LAT = 40.407872
HUAIROU_LON = 116.674036

# 搜索半径（公里）
RADIUS_KM = 30

# OpenSky 认证（从环境变量读取）
USERNAME = os.environ.get("OPENSKY_USERNAME")
PASSWORD = os.environ.get("OPENSKY_PASSWORD")
AUTH = (USERNAME, PASSWORD) if USERNAME and PASSWORD else None

def get_flights():
    """获取怀柔上空的飞机数据"""
    # 边界框：以怀柔为中心，扩展约0.5度
    bounds = {
        "lamin": HUAIROU_LAT - 0.5,
        "lomax": HUAIROU_LON + 0.5,
        "lamax": HUAIROU_LAT + 0.5,
        "lomin": HUAIROU_LON - 0.5
    }
    
    url = "https://opensky-network.org/api/states/all"
    
    try:
        response = requests.get(url, params=bounds, auth=AUTH, timeout=15)
        
        # 验证请求状态和账户额度相关响应
        if response.status_code == 401:
            print("错误: 认证失败！.env文件中提供的 OpenSky 账号或密码不正确。")
            return []
        elif response.status_code == 429:
            print(f"错误: 请求过于频繁或已达到 OpenSky API { '登录账户' if AUTH else '匿名访客' }的速率限制（额度耗尽）。")
            return []
        
        response.raise_for_status()
        data = response.json()
        
        if not data.get("states"):
            return []
        
        flights = []
        for state in data["states"]:
            # 解析数据
            icao24 = state[0]
            callsign = state[1].strip() if state[1] else "未知"
            lon = state[5]      # 经度
            lat = state[6]      # 纬度
            altitude = state[7] if state[7] is not None else 0      # 高度（米）
            velocity = state[9] if state[9] is not None else 0      # 速度（米/秒）
            heading = state[10] if state[10] is not None else 0     # 航向（度）
            on_ground = state[8] if len(state) > 8 else True        # 是否在地面
            
            # 跳过无效坐标
            if lat is None or lon is None:
                continue
            
            # 可选：筛选半径范围内的飞机（后续可用于过滤）
            # from math import radians, sin, cos, sqrt, atan2
            # if calculate_distance(lat, lon) > RADIUS_KM:
            #     continue
            
            flights.append({
                "航班号": callsign,
                "高度(米)": altitude,
                "速度(米/秒)": velocity,
                "航向(度)": heading,
                "经度": lon,
                "纬度": lat,
                "是否地面": on_ground,
                "ICAO24": icao24
            })
        
        return flights
    except Exception as e:
        print(f"请求失败: {e}")
        return []

def save_to_csv(flights, timestamp):
    """保存数据到 CSV"""
    if not flights:
        print("无数据可保存")
        return
    
    # 文件路径：data/flight_huairou_YYYYMMDD.csv
    date_str = timestamp[:10].replace('-', '')
    year_month = date_str[:6]
    folder_path = os.path.join("data", year_month)
    os.makedirs(folder_path, exist_ok=True)
    
    filename = f"flight_huairou_{date_str}.csv"
    file_path = os.path.join(folder_path, filename)
    
    file_exists = os.path.isfile(file_path)
    
    with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=["采集时间", "航班号", "高度(米)", "速度(米/秒)", "航向(度)", "经度", "纬度", "是否地面", "ICAO24"])
        if not file_exists:
            writer.writeheader()
        
        for flight in flights:
            writer.writerow({
                "采集时间": timestamp,
                **flight
            })
    
    print(f"✓ 已保存 {len(flights)} 条记录")

def main():
    if AUTH:
        print(f"[*] 当前已配置 OpenSky 账户 ({USERNAME})，将使用登录账户对应的高级请求额度...")
    else:
        print("[!] 警告: 未配置 OpenSky 账户。正作为匿名访客访问（将会受到更严格的访问频率及额度限制）...")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 开始采集...")
    
    flights = get_flights()
    
    if flights:
        print(f"  发现 {len(flights)} 架飞机")
        for f in flights[:5]:  # 打印前5架
            print(f"    {f['航班号']} | 高度:{f['高度(米)']}m | 速度:{f['速度(米/秒)']}m/s | 航向:{f['航向(度)']}°")
        save_to_csv(flights, timestamp)
    else:
        print("  未发现飞机")

if __name__ == "__main__":
    main()