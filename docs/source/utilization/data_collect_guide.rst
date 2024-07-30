===============================
InfluxDB データ取得のガイド
===============================

このガイドでは、InfluxDB v2 APIを使用してデータを取得するための方法を説明します。 以下の方法をカバーします：

- 必要なツールのインストール
- 環境変数の設定
- Bashスクリプトを使用したデータ取得
- InfluxDB GUIを使用したデータ取得
- Pythonを使用したデータ取得

必要なツールのインストール
----------------------------------

以下のツールが必要です。 インストールされていない場合は、以下のコマンドを使用してインストールしてください。

.. code-block:: bash

    sudo apt update
    sudo apt install curl jq

環境変数の設定
-----------------------------

まず以下の環境変数を設定してください。これらは、InfluxDBのURL、トークン、組織名、およびバケット名となります。

.. code-block:: bash

    export INFLUXDB_URL="http://[IP_ADDRESS]:8086"  # InfluxDBのURL
    export INFLUXDB_TOKEN="[YOUR_TOKEN]"            # 認証トークン
    export INFLUXDB_ORG="[YOUR_ORGANIZATION]"       # 組織名
    export INFLUXDB_BUCKET="[YOUR_BUCKET]"          # バケット名

Bashスクリプトを使用したデータ取得
---------------------------------------

InfluxDB v2 APIからデータを取得し、解析を行います。

.. code-block:: bash

    #!/bin/bash

    # クエリを設定
    QUERY='from(bucket: "pinode")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "00")
      |> filter(fn: (r) => r._field== "temperature")
      |> yield(name: "mean")
      '

    # curlコマンドを実行してデータを取得
    response=$(curl --request POST \
      "${INFLUXDB_URL}/api/v2/query?org=${INFLUXDB_ORG}&bucket=get-started" \
      --header "Authorization: Token ${INFLUXDB_TOKEN}" \
      --header "Content-Type: application/vnd.flux" \
      --header "Accept: application/csv" \
      --data "query=${QUERY}" \
    )

    # エラーチェック
    if [ $? -ne 0 ]; then
        echo "curlコマンドの実行中にエラーが発生しました。"
        exit 1
    fi

    # データをCSV形式で保存
    echo "${response}" > ./influxdb_data.csv

スクリプトの実行
------------------------

このスクリプトは、`scripts/fetch_influxdb_data.sh` に記載されています。 これを実行します。

.. code-block:: bash

    scripts/fetch_influxdb_data.sh

スクリプトが正常に実行されると、InfluxDBから取得したデータが`influxdb_data.csv`に保存されます。

InfluxDB GUIを使用したデータ取得
-----------------------------------------

1. InfluxDBのGUIページに移動します。デフォルトのURLは`http://[IP_ADDRESS or HOSTNAME]:8086`です。
2. ログインします。デフォルトのユーザー名は`pinode`、パスワードは`pinode-pass`です。
3. 左側のメニューから「Explore」を選択します。
4. クエリエディタに以下のFluxクエリを入力します。

.. note:: ログイン設定は :doc:`../software-reference/configuration` を参照してください。

.. code-block:: 

    from(bucket: "pinode")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "00")
      |> filter(fn: (r) => r._field == "temperature")
      |> yield(name: "mean")

4. 「Submit」ボタンをクリックしてクエリを実行します。
5. 結果が表示されたら必要に応じてデータをエクスポートします。

Pythonを使用したデータ取得
--------------------------------

以下は、Pythonを使用してInfluxDB v2 APIからデータを取得する例です。

必要なライブラリのインストール
------------------------------

.. code-block:: bash

    pip install influxdb-client

Pythonスクリプト
------------------------

.. code-block:: python

    from influxdb_client import InfluxDBClient

    # 環境変数の設定
    INFLUXDB_URL = "http://[INFLUXDB_URL]:8086"
    INFLUXDB_TOKEN = "[INFLUXDB_TOKEN]"
    INFLUXDB_ORG = "pinode"
    INFLUXDB_BUCKET = "pinode"

    # InfluxDBクライアントの作成
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

    # クエリを設定
    query = """
    from(bucket: "pinode")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "00")
        |> filter(fn: (r) => r._field == "temperature")
        |> yield(name: "mean")
    """

    # クエリを実行
    df = client.query_api().query_data_frame(query)

    # CSVファイルに保存
    df.to_csv("influxdb_data.csv", index=False)

スクリプトの実行
----------------------

このスクリプトは、`scripts/fetch_influxdb_data.py` に記載されています。 これを実行します。

.. code-block:: bash

    python scripts/fetch_influxdb_data.py

スクリプトが正常に実行されると、InfluxDBから取得したデータが`influxdb_data.csv`に保存されます。

InfluxDB データ取得結果
----------------------------

以下の出力は、InfluxDBから取得したデータの例です。 このデータは、特定のバケットから過去1時間の温度データをクエリした結果です。 各フィールドの意味を詳しく説明します。

.. csv-table::
   :header: "result", "table", "_start", "_stop", "_time", "_value", "_field", "_measurement"

   "mean", "0", "2024-06-30T07:49:33.091101235Z", "2024-06-30T08:49:33.091101235Z", "2024-06-30T07:49:53Z", "24.804", "temperature", "00"
   "mean", "0", "2024-06-30T07:49:33.091101235Z", "2024-06-30T08:49:33.091101235Z", "2024-06-30T07:50:54Z", "24.847", "temperature", "00"
   "mean", "0", "2024-06-30T07:49:33.091101235Z", "2024-06-30T08:49:33.091101235Z", "2024-06-30T07:51:03Z", "24.847", "temperature", "00"
   "mean", "0", "2024-06-30T07:49:33.091101235Z", "2024-06-30T08:49:33.091101235Z", "2024-06-30T07:52:13Z", "24.922", "temperature", "00"
   "mean", "0", "2024-06-30T07:49:33.091101235Z", "2024-06-30T08:49:33.091101235Z", "2024-06-30T07:53:23Z", "24.997", "temperature", "00"
   "mean", "0", "2024-06-30T07:49:33.091101235Z", "2024-06-30T08:49:33.091101235Z", "2024-06-30T07:54:33Z", "25.04", "temperature", "00"

各フィールドの説明
---------------------

- **result**: クエリの結果タイプを示します。ここではすべて`mean`となっており、平均値の計算結果を示しています。
- **table**: データのテーブル番号を示します。すべて`0`なので、単一のテーブルに格納されています。
- **_start**: クエリの開始時間を示します。例では `2024-06-30T07:49:33.091101235Z` です。
- **_stop**: クエリの終了時間を示します。例では `2024-06-30T08:49:33.091101235Z` です。
- **_time**: データポイントのタイムスタンプを示します。このタイムスタンプはUTCで表示されます。例えば、 `2024-06-30T07:49:53Z` は `2024年6月30日 07:49:53 UTC` を示しています。
- **_value**: 測定された値を示します。例では温度データの値が表示されています。例えば、 `24.804` は温度を示します。
- **_field**: 測定されたフィールド名を示します。例では `temperature` です。
- **_measurement**: 測定の種類を示します。例では `00` です。