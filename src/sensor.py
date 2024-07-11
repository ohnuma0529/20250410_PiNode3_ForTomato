import json
import subprocess
import time
import spidev
import os
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import read_sensor

import util
from db import InfluxDB

class SensorResult(Enum):
    SUCCESS             = 0  # 正常
    EMPTY_STRING_ERROR  = 1  # 空文字エラー
    NAN_ERROR           = 2  # nanエラー
    INF_ERROR           = 3  # infエラー
    MIN_VALUE_ERROR     = 4  # 最小値エラー
    MAX_VALUE_ERROR     = 5  # 最大値エラー

class MCP3204:
    def __init__(self, spi, vref=5.0):
        self.spi = spi
        self.vref = vref

    def read(self, ch):
        if ch < 0 or ch > 4:
            return -1
        data2 = (ch << 6) & 0xff
        ret = self.spi.xfer2([0x06, data2, 0x00])
        raw = ((ret[1] & 0x0f) << 8) + ret[2]
        volts = raw * self.vref / 4096.0
        return volts

class Sensor:
    def __init__(self):
        read_sensor.init_pigpio()
        self.config = util.get_pinode_config()

        self.previous_data_path = self.config['sensor']['previous_data_path']
        with open(self.previous_data_path, "r") as f:
            self.previous_sensor_data = json.load(f)

        self.i2c_sensor_list = list(self.config['sensor']['i2c_command'].keys())
        self.spi_sensor_list = list(self.config['sensor']['spi_channel'].keys())
    
    def get(self, sensor:str):
        for _ in range(self.config['sensor']['max_retry_count'][sensor]):
            try:
                data = read_sensor.get(sensor)
                time.sleep(self.config['sensor']['sleep_time'][sensor])
                result = self._is_valid(data, sensor)
                if result == SensorResult.SUCCESS:
                    # 前回値を保存
                    with open(self.previous_data_path, 'w') as f:
                        self.previous_sensor_data[sensor] = float(data)
                        json.dump(self.previous_sensor_data, f, indent=4)
                    return result, float(data)
            except Exception as e:
                print(e)
            finally:
                time.sleep(self.config['sensor']['retry_interval'][sensor])
        # 取得失敗した場合は前回値を渡す
        return result, self.previous_sensor_data[sensor]

    def upload_csv(self, upload_sensor_list=[]):
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

    def _get_raw_data(self, sensor:str):
        if sensor in self.i2c_sensor_list: 
            data = subprocess.run(
                self.config['sensor']['i2c_command'][sensor].split(' '),
                capture_output=True,
                text=True
            ).stdout.strip()
        elif sensor in self.spi_sensor_list:
            dev = spidev.SpiDev()
            dev.open(0, 0)
            dev.max_speed_hz = 50000
            data = MCP3204(dev).read(self.config['sensor']['spi_channel'][sensor])
            dev.close()
        else:
            raise ValueError(f"sensor: {sensor} is not found in config.json")
        return data
    
    def _is_valid(self, data, sensor:str):
        if not data:  # 空文字を確認
            return SensorResult.EMPTY_STRING_ERROR
        if data == 'nan':  # nanを確認
            return SensorResult.NAN_ERROR
        if data == 'inf':  # infを確認
            return SensorResult.INF_ERROR
        if float(data) < self.config['sensor']['min_value'][sensor]:  # 最小値を確認
            return SensorResult.MIN_VALUE_ERROR
        if float(data) > self.config['sensor']['max_value'][sensor]:  # 最大値を確認
            return SensorResult.MAX_VALUE_ERROR
        return SensorResult.SUCCESS
    
    def _gpio_init(self, sensor:str):
        # GPIOピン番号4を有効化
        os.system("echo 4 > /sys/class/gpio/export")
        time.sleep(self.config['sensor']['retry_interval'][sensor])
        # GPIOピン番号4をアウトプットモードに設定
        os.system("echo out > /sys/class/gpio/gpio4/direction")
        time.sleep(self.config['sensor']['retry_interval'][sensor])
        # GPIOピン番号4の出力を0に設定
        os.system("echo 0 > /sys/class/gpio/gpio4/value")
        time.sleep(self.config['sensor']['retry_interval'][sensor])
        # GPIOピン番号4の出力を1に設定
        os.system("echo 1 > /sys/class/gpio/gpio4/value")
        time.sleep(self.config['sensor']['retry_interval'][sensor])