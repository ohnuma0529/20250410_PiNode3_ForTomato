from pathlib import Path
import util
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

class InfluxDB:
    """
    InfluxDBへのデータアップロードのためのクラス

    Notes:
        port: 8086: influxdbのポート番号 
        
        portを除く各種変数は運用前にconfig.jsonを書き換えておくこと
        
        token: InfluxDBの認証キーが書かれているtxt. install.shで作成. InfluxDBへのアップロード時に使用

    """
    def __init__(self):
        pinode_config   = util.get_pinode_config()
        self.org        = pinode_config["influxdb"]["organization"]
        self.bucket     = pinode_config["influxdb"]["bucket"]
        self.device_id  = pinode_config["device_id"]
        self.url        = pinode_config["influxdb"]["url"]
        self.token      = pinode_config["influxdb"]["token"]

        self.org_edge   = pinode_config["influxdb_edge"]["organization"]
        self.bucket_edge= pinode_config["influxdb_edge"]["bucket"]
        self.url_edge   = pinode_config["influxdb_edge"]["url"]
        self.token_edge = pinode_config["influxdb_edge"]["token"]
    
    def upload_dataframe(self, data):
        """
        データをInfluxDBへアップロードする際に使用
        Notes:
            write_Options=SYNCRONOUS: データの書き込みを同期的に行う．データが完全に書き終わるまでプログラムの実行を停止．
        
            書き込み内容のパラメータ:
                bucket : データを書き込むバケット名．データベースのようなもの
                
                org    : InfluxDBのオーガニゼーション名
                
                record : 書き込むデータ
                
                data_frame_measurement_name : InfluxDBにおけるデータカテゴリのようなもの.SQLでいうテーブル名

        """
        write_client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        write_api = write_client.write_api(write_options=SYNCHRONOUS)
        write_api.write(
            self.bucket,
            self.org,
            record=data,
            data_frame_measurement_name=self.device_id
        )

    def upload_dataframe_edge(self, data):
        """
        データをInfluxDBへアップロードする際に使用
        Notes:
            write_Options=SYNCRONOUS: データの書き込みを同期的に行う．データが完全に書き終わるまでプログラムの実行を停止．
        
            書き込み内容のパラメータ:
                bucket : データを書き込むバケット名．データベースのようなもの
                
                org    : InfluxDBのオーガニゼーション名
                
                record : 書き込むデータ
                
                data_frame_measurement_name : InfluxDBにおけるデータカテゴリのようなもの.SQLでいうテーブル名

        """
        write_client = InfluxDBClient(url=self.url_edge, token=self.token_edge, org=self.org_edge)
        write_api = write_client.write_api(write_options=SYNCHRONOUS)
        write_api.write(
            self.bucket_edge,
            self.org_edge,
            record=data,
            data_frame_measurement_name=self.device_id
        )