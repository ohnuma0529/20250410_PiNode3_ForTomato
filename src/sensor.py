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

    constants:
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
    
    paramerters:
    spi: SPIインターフェースオブジェクト
    vref: 参照電圧(今回の場合は5.0V)

    """
    def __init__(self, spi, vref=5.0):
        self.spi = spi
        self.vref = vref

    # def read(self, ch):
    #     """
    #     指定したチャンネルからアナログ値を読み取りデジタル値に変換後，電圧に変換して返す

    #     Parameter:
    #     ch: チャンネル番号 (0～3)
    #     Return:
    #     チャンネルの電圧値(ボルト単位),チャンネル番号が無効な場合-1

    #     Details:
    #     MCP3204の通信フォーマットではSPI通信を通じて3バイトのデータでの送信が行われる.
        
    #     xfer2([0x06, data2, 0x00])では通信フォーマットに従って以下の3バイトのデータを指定する
    #     1番目のバイト: '0x06' スタートビットとモードビット(今回はシングルエンドモード)
    #                    スタートビット: MCP3204に対して通信の開始を示すビット
    #                    モードビット: MCP3204がどのモードでデータを取得するかを示すビット.今回はシングルエンドモード
    #     2番目のバイト: data2  チャネル番号 
    #                   '0bCCCC0000'のようなフォーマットで指定する. CCCC部分にチャネル番号を指定
    #                   CCCC部分をチャネル番号にするため (ch << 6) & 0xff を実行してchをシフト&整形
    #     3番目のバイト: '0x00' ダミーバイト
    #                    このバイトはMCP3204からの応答データを完全に受信するために必要である.
    #                    今回個のバイトで送るデータはないが通信サイクルを成立させるために適当なダミーデータを指定

    #     通信によって返却された3バイトの値がretに格納される
    #     ret (list): ret[0]: 1番目のバイト: 最初の送信データに対するMCP3204からの応答. (一般的には無視される)  
    #                 ret[1]: 2番目のバイト: 下位4ビットにデータが含まれる
    #                 ret[2]: 3番目のバイト: 8ビットすべてにデータが含まれる
        
    #     raw = ((ret[1] & 0x0f) << 8) + ret[2]ではret[1]とret[2]の意味を持つバイトを12ビットとして取り出す.

    #     volts = raw * self.vref / 4096.0 :ADCが生成する12ビットのデジタル値がアナログ入力電圧にどのように対応するかを計算
    #                                       4096(2^12)で割ることでデジタル値を電圧値にスケーリングして正確な電圧値を取得
    #     """
    #     if ch < 0 or ch > 4:
    #         return -1
    #     data2 = (ch << 6) & 0xff
    #     ret = self.spi.xfer2([0x06, data2, 0x00])
    #     raw = ((ret[1] & 0x0f) << 8) + ret[2]
    #     volts = raw * self.vref / 4096.0
    #     return volts

class Sensor:
    """
    センサからの情報取得を行う        
    """
    def __init__(self):
        """
        センサクラスの初期化を行うメソッド
        
        Details:
        センサデータ読み込みのためにGPIOの初期化, pigpioデーモンとの接続を作成(グローバル変数 pi)
        各種設定をconfig.jsonから取得

        前回取得したセンサデータがprevious_sensor_data.jsonに記録されている
        このデータを取得しself.previous_sensor_data.jsonに格納        
        [previous_sensor_data.json] https://github.com/MinenoLab/PiNode3/blob/815bc1191299f1e08c01693903b32b1550b43e7c/src/previous_sensor_data.json

        I2CセンサのコマンドとSPIチャンネルのリストを取得
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
        
        Parameters:
        sensor(str): センサ名
        
        Returns: 
            result(int): センサ名
            data(float): センサデータ
            
        Details:
        センサごとに指定回数だけデータ取得を試みる(デフォルトではすべてのセンサで3回試行)
        data = read_sensor.get(sensor): センサデータを取得 
        result = self._is_valid(data, sensor):センサデータ状態を取得
        センサデータが正常に取得できていた場合previous_sensor_dataを書き換えてdata,resultを返却
        センサデータを正常に取得できなかった場合は前回値を返却
        
        """
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
        """
        センサから値を取得しデータセットを作成.その後送信
        
        Parameters:
        upload_sensor_list: アップロードしたいセンサのリスト
                            指定しない場合,upload_sensor_listが指定される
        
        Details:
        upload_sensor_list: 取得するデータのカラム
        カラムに設定された要素についてセンサデータを取得する．このとき，インデックスとして時刻データを設定
        データが正常であればinfluxDBでデータセットを送信
        データが正常でない場合,csvファイルに保存
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

    # def _get_raw_data(self, sensor:str):
    #     if sensor in self.i2c_sensor_list: 
    #         data = subprocess.run(
    #             self.config['sensor']['i2c_command'][sensor].split(' '),
    #             capture_output=True,
    #             text=True
    #         ).stdout.strip()
    #     elif sensor in self.spi_sensor_list:
    #         dev = spidev.SpiDev()
    #         dev.open(0, 0)
    #         dev.max_speed_hz = 50000
    #         data = MCP3204(dev).read(self.config['sensor']['spi_channel'][sensor])
    #         dev.close()
    #     else:
    #         raise ValueError(f"sensor: {sensor} is not found in config.json")
    #     return data
    
    def _is_valid(self, data, sensor:str):
        """
        センサデータの値の取得状態を判定するメソッド
        
        Parameters:
        data(int|float): センサデータ
        sensor(str): センサ名
        
        Details:
        センサデータに応じてエラーを出力
        SUCCESS             = 0  : 正常
        EMPTY_STRING_ERROR  = 1  : 空文字エラー
        NAN_ERROR           = 2  : nanエラー
        INF_ERROR           = 3  : infエラー
        MIN_VALUE_ERROR     = 4  : 最小値エラー
        MAX_VALUE_ERROR     = 5  : 最大値エラー
        """
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
    
    # def _gpio_init(self, sensor:str):
    #     # GPIOピン番号4を有効化
    #     os.system("echo 4 > /sys/class/gpio/export")
    #     time.sleep(self.config['sensor']['retry_interval'][sensor])
    #     # GPIOピン番号4をアウトプットモードに設定
    #     os.system("echo out > /sys/class/gpio/gpio4/direction")
    #     time.sleep(self.config['sensor']['retry_interval'][sensor])
    #     # GPIOピン番号4の出力を0に設定
    #     os.system("echo 0 > /sys/class/gpio/gpio4/value")
    #     time.sleep(self.config['sensor']['retry_interval'][sensor])
    #     # GPIOピン番号4の出力を1に設定
    #     os.system("echo 1 > /sys/class/gpio/gpio4/value")
    #     time.sleep(self.config['sensor']['retry_interval'][sensor])