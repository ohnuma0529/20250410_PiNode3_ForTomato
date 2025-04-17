import json
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import datetime as dt

import util

# InfluxDBの基本情報読み込み
config = util.get_pinode_config()

class InfluxDBWrapper:
    def __init__(self, db_name):
        self.name = db_name
        self.url = config[db_name]['url']
        self.token = config[db_name]['token']
        self.org = config[db_name]['organization']
        self.bucket = config[db_name]['bucket']
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def __enter__(self):
        return self

    def __exit__(self, exctype, excvalue, traceback):
        self.client.close()

    def write_single_point(self, measurement, timestamp, field, value):
        """
        単一のデータポイントを書き込む
        """
        point = Point(measurement).time(timestamp - pd.Timedelta(hours=9)).field(field, value)
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)

    def write_dataframe(self, measurement, df):
        """
        DataFrameのデータを一括で書き込む
        """
        for index, row in df.iterrows():
            point = Point(measurement).time(index - pd.Timedelta(hours=9))
            for col, value in row.items():
                try:
                    point.field(col, float(value))
                except ValueError:
                    continue
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)

    def get(self, measurement, field, start_datetime, end_datetime=dt.datetime.now()):
        """
        指定期間のデータをDataFrameで取得
        """
        start_datetime -= dt.timedelta(hours=9)
        end_datetime -= dt.timedelta(hours=9)
        query_api = self.client.query_api()
        query_text = self.__make_query(measurement, field, start_datetime, end_datetime)
        df = query_api.query_data_frame(query_text)
        df['time'] = df['_time'].dt.tz_localize(None)
        return df.drop(columns=['result', 'table', '_start', '_stop', '_time'])

    def delete_measurement(self, measurement=None, all=False):
        """
        指定されたメジャメントを削除する。
        all=Trueの場合、すべてのメジャメントを削除する。
        """
        delete_api = self.client.delete_api()
        start_time = "1970-01-01T00:00:00Z"
        end_time = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        if all:
            predicate = "_measurement!="
        else:
            predicate = f'_measurement="{measurement}"'
        delete_api.delete(start_time, end_time, predicate, bucket=self.bucket, org=self.org)

    def __make_query(self, measurement, field, start_datetime, end_datetime):
        """
        クエリ文作成
        """
        query_text = f'from(bucket: "{self.bucket}") |> range(start: {start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")}, stop: {end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")})'
        if isinstance(measurement, str):
            query_text += f' |> filter(fn: (r) => r["_measurement"] == "{measurement}")'
        else:
            query_text += ' |> filter(fn: (r) => ' + ' or '.join([f'r["_measurement"] == "{m}"' for m in measurement]) + ')'
        if isinstance(field, str):
            query_text += f' |> filter(fn: (r) => r["_field"] == "{field}")'
        else:
            query_text += ' |> filter(fn: (r) => ' + ' or '.join([f'r["_field"] == "{f}"' for f in field]) + ')'
        return query_text + ' |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'