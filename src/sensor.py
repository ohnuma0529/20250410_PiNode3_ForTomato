import json
import subprocess
import time
# import spidev
import os
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import read_sensor

import util
from db import InfluxDB

class SensorResult(Enum):
    """
    数字を定数として扱うためにconstantsを作成

    Notes:
        SUCCESS             = 0  : 正常
        
        EMPTY_STRING_ERROR  = 1  : 空文字エラー
        
        NAN_ERROR           = 2  : nanエラー
        
        INF_ERROR           = 3  : infエラー
        
        MIN_VALUE_ERROR     = 4  : 最小値エラー
        
        MAX_VALUE_ERROR     = 5  : 最大値エラー

    """
    SUCCESS             = 0  
    EMPTY_STRING_ERROR  = 1  
    NAN_ERROR           = 2  
    INF_ERROR           = 3  
    MIN_VALUE_ERROR     = 4  
    MAX_VALUE_ERROR     = 5  

class MCP3204:
    """
    MPC3204 ADC(アナログデジタルコンバータ)を使用するためのクラス
    
    Args:
        spi: SPIインターフェースオブジェクト
        vref: 参照電圧(今回の場合は5.0V)
    """
    def __init__(self, spi, vref=5.0):
        self.spi = spi
        self.vref = vref

class Sensor:
    """
    センサからの情報取得を行う        
    """
    def __init__(self):
        """
        センサクラスの初期化を行うメソッド
        
        Notes:
            センサデータ読み込みのためにGPIOの初期化, pigpioデーモンとの接続を作成(グローバル変数 pi)

            前回取得したセンサデータがprevious_sensor_data.jsonに記録されている.このデータをself.previous_sensor_data.jsonに格納        
            
            [previous_sensor_data.json] https://github.com/MinenoLab/PiNode3/blob/815bc1191299f1e08c01693903b32b1550b43e7c/src/previous_sensor_data.json

        """
        read_sensor.init_pigpio()
        self.config = util.get_pinode_config()

        self.previous_data_path = self.config['sensor']['previous_data_path']
        with open(self.previous_data_path, "r") as f:
            self.previous_sensor_data = json.load(f)

        self.i2c_sensor_list = list(self.config['sensor']['i2c_command'].keys())
        self.spi_sensor_list = list(self.config['sensor']['spi_channel'].keys())
    
    def get(self, sensor:str):
        """
        各種センサデータを取得するためのメソッド
        
        Args:
            sensor(str): センサ名
        
        Returns: 
            result(int): センサ名
            data(float): センサデータ
        
        Attributes:
            data = read_sensor.get(sensor): センサデータを取得 
            result = self._is_valid(data, sensor):センサデータ状態を取得
        
        Notes:
            センサごとに指定回数だけデータ取得を試みる(デフォルトではすべてのセンサで3回試行)
            
            センサデータが正常に取得できていた場合previous_sensor_dataを書き換えてdata,resultを返却
            
            センサデータを正常に取得できなかった場合は前回値を返却
        
        """
        result = SensorResult.EMPTY_STRING_ERROR
        for _ in range(self.config['sensor']['max_retry_count'][sensor]):
            try:
                data = read_sensor.get(sensor)
                time.sleep(self.config['sensor']['sleep_time'][sensor])
                result = self._is_valid(data, sensor)
                if result == SensorResult.SUCCESS:
                    with open(self.previous_data_path, 'w') as f:
                        self.previous_sensor_data[sensor] = float(data)
                        json.dump(self.previous_sensor_data, f, indent=4)
                    return result, float(data)
            except Exception as e:
                print(e)
            finally:
                time.sleep(self.config['sensor']['retry_interval'][sensor])
        
        return result, self.previous_sensor_data[sensor]

    def upload_csv(self, upload_sensor_list=[]):
        """
        センサから値を取得しデータセットを作成.その後送信
        
        Args:
            upload_sensor_list: アップロードしたいセンサのリスト. パラメータ指定しない場合,センサすべてが指定される
        
        Attributes:
            upload_sensor_list: 取得可能なセンサすべてのリスト
        
        Notes:
            カラムに設定された要素についてセンサデータを取得してdfに保存. このとき,インデックスとして時刻データを設定
            
            データが正常であればinfluxDBでデータセットを送信.データが正常でない場合,csvファイルに保存
        """
        upload_sensor_list = ["temperature", "humidity", "i_v_light", "u_v_light", "temperature_hq", "humidity_hq", "stem", "fruit_diagram"] if len(upload_sensor_list) == 0 else upload_sensor_list
        sensor = Sensor()

        df = pd.DataFrame(
            data  = {sensor_name: [sensor.get(sensor_name)[1]] for sensor_name in upload_sensor_list},
            index = [datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')]
        )
        try:
            InfluxDB().upload_dataframe(df)
        except Exception as e:
            print(e)
            csv_path = Path(self.config['sensor']['csv_dir']) / f"{self.config['device_id']}_{datetime.now().strftime('%Y%m%d-%H%M.csv')}"
            df.to_csv(csv_path)

    
    def _is_valid(self, data, sensor:str):
        """
        センサデータの値の取得状態を判定するメソッド
        
        Args:
            data(int|float): センサデータ
            sensor(str): センサ名
        
        Notes:
            センサデータに応じてエラーを出力
            
            SUCCESS             = 0  : 正常
            
            EMPTY_STRING_ERROR  = 1  : 空文字エラー
            
            NAN_ERROR           = 2  : nanエラー
            
            INF_ERROR           = 3  : infエラー
            
            MIN_VALUE_ERROR     = 4  : 最小値エラー
            
            MAX_VALUE_ERROR     = 5  : 最大値エラー
        """
        if not data:  
            return SensorResult.EMPTY_STRING_ERROR
        if data == 'nan':  
            return SensorResult.NAN_ERROR
        if data == 'inf': 
            return SensorResult.INF_ERROR
        if float(data) < self.config['sensor']['min_value'][sensor]:  
            return SensorResult.MIN_VALUE_ERROR
        if float(data) > self.config['sensor']['max_value'][sensor]: 
            return SensorResult.MAX_VALUE_ERROR
        return SensorResult.SUCCESS
    