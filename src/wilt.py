import util
from image_processor import image_processor
from influxdb import InfluxDBWrapper

import os
import time
from datetime import datetime
import json

def cal_wilt():
    # 設定読み込み
    setting = util.get_pinode_config()
    edge_id = setting["device_id"]
    wilt_flag = setting["wilt"]["wilt_flag"]
    source_dir = setting["wilt"]["image_dir"]
    if wilt_flag == False:
        print("wilt_flag is 0")
        return

    # 撮影前準備
    now_time = datetime.now().replace(second=0, microsecond=0)
    start_time = datetime.strptime(setting["wilt"]["start_time"], "%H%M").time()
    end_time = datetime.strptime(setting["wilt"]["end_time"], "%H%M").time()
    start_datetime = datetime.combine(datetime.today().date(), start_time)
    end_datetime = datetime.combine(datetime.today().date(), end_time)
    
    date = now_time.strftime('%Y%m%d')
    image_dir = os.path.join(source_dir, date)
    os.makedirs(image_dir, exist_ok=True)
    csv_path = os.path.join(image_dir, "result.csv")

    if start_datetime <= now_time <= end_datetime:    
        # ベンチマーク用の時刻取得
        start_time = time.time()

        # csv読込
        df = util.read_csv(csv_path)

        # その日の初回画像であったり，再検出フラグ列が1だったら初回処理
        img_pro = image_processor(df, image_dir, now_time)

        if df.empty:
            print("df is empty")
            df = img_pro.first_detection()
        elif 're_detection' not in df.columns:
            print("re_detection is not in df.columns")
            df = img_pro.first_detection()
        elif df['re_detection'].iloc[-1] == 1:
            print("re_detection is 1")
            df = img_pro.first_detection()
        else:
            print("tracking")
            df = img_pro.tracking()

        # csv保存・更新
        util.save_csv(df, csv_path)

        # 時刻を取得
        end_time = time.time()
        inference_time = end_time - start_time

        try:
            infdb = InfluxDBWrapper("influxdb_edge")
            infdb.write_single_point(edge_id, now_time, "wilt", float(df['final_wilt'].iloc[-1]))
            infdb.write_single_point(edge_id, now_time, "inference_time", inference_time)
        except Exception as e:
            print("InfluxDB(edge) Error")
            print(e)
        try:
            infdb_server = InfluxDBWrapper("influxdb")
            infdb_server.write_single_point(edge_id, now_time, "wilt", float(df['final_wilt'].iloc[-1]))
            infdb_server.write_single_point(edge_id, now_time, "inference_time", inference_time)
        except Exception as e:
            print("InfluxDB(server) Error")
            print(e)
    else:
        print("動作時間外：",now_time)
if __name__ == "__main__":
    cal_wilt()