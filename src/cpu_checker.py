import time
import datetime
import psutil
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import json

from influxdb import InfluxDBWrapper
import util

# CPU温度を取得する関数
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000.0  # ミリ度Cを度Cに変換
        return temp
    except FileNotFoundError:
        return None  # 温度センサーが見つからない場合

config = util.get_pinode_config()

infdb = InfluxDBWrapper("influxdb_edge")
edge_id = config["device_id"]
infdb_server = InfluxDBWrapper("influxdb")

while True:
    now_time = datetime.datetime.now()
    cpu_usage = psutil.cpu_percent(interval=1)  # CPU使用率（1秒間の平均）
    cpu_temp = get_cpu_temp()  # CPU温度

    if cpu_temp is None:
        print("CPU温度が取得できませんでした。")
        continue
    try:
        infdb.write_single_point(edge_id, now_time, "cpu_usage", cpu_usage)
        infdb.write_single_point(edge_id, now_time, "cpu_temp", cpu_temp)
    except Exception as e:
        print("InfluxDB(edge) Error")
        print(e)
    try:
        infdb_server.write_single_point(edge_id, now_time, "cpu_usage", cpu_usage)
        infdb_server.write_single_point(edge_id, now_time, "cpu_temp", cpu_temp)
    except Exception as e:
        print("InfluxDB(server) Error")
        print(e)

    print(f"CPU Usage: {cpu_usage}%, CPU Temp: {cpu_temp}°C")
    time.sleep(10)