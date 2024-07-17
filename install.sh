### InfluxDBのインストール

# 上手く動作しない場合は以下のURLを参照
# https://docs.influxdata.com/influxdb/v2/install/?t=%3Cfont+style%3D%22vertical-align%3A+inherit%3B%22%3E%3Cfont+style%3D%22vertical-align%3A+inherit%3B%22%3ELinux%3C%2Ffont%3E%3C%2Ffont%3E
# https://www.influxdata.com/downloads/?_gl=1*tp92hm*_ga*OTYxNDc3OTA3LjE3MTA1NjEwMjY.*_ga_CNWQ54SDD8*MTcxNDYyNDU3Ny4yLjEuMTcxNDYyNTYxMi42MC4wLjUyNDc4MDY1Mg..

wget -q https://repos.influxdata.com/influxdata-archive_compat.key
echo '393e8779c89ac8d958f81f942f9ad7fb82a25e133faddaf92e15b16e6ac9ce4c influxdata-archive_compat.key' | sha256sum -c && cat influxdata-archive_compat.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg > /dev/null
echo 'deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg] https://repos.influxdata.com/debian stable main' | sudo tee /etc/apt/sources.list.d/influxdata.list

sudo apt-get -y update && sudo apt-get install -y influxdb2
sudo systemctl start influxdb

rm influxdata-archive_compat.key

influx setup \
    --username pinode \
    --password pinode-pass \
    --org pinode \
    --bucket pinode \
    --force

influx auth create -o pinode --all-access | sed -n '2p' | awk '{print $2}' > src/token.txt

### pythonライブラリのインストール
# [仮想環境有効化]
# $ /usr/local/bin/pinod3/python/pinode3/bin/activate
# [仮想環境無効化]
# $ deactivate
# [仮想環境削除]
# $ rm -rf /usr/local/bin/python/pinode3
python -m venv pinode3
source pinode3/bin/activate
pip install -r requirements.txt
sudo mkdir -p /usr/local/bin/pinode3/python/
sudo mv pinode3 /usr/local/bin/pinode3/python/

# USB判別用ドライバの設定
echo === Install USB Identify Driver ===
model=$(grep -m1 -o -w 'Raspberry Pi [0-9]* Model [ABCD]\|Raspberry Pi 3 Model B Plus' /proc/cpuinfo)
echo install $model USB driver
if [[ "$model" == "Raspberry Pi 3 Model B" ]]; then
	sudo cp driver/usb/90-usb_3b.rules /etc/udev/rules.d/90-usb.rules
elif [[ "$model" == "Raspberry Pi 3 Model B Plus"* ]]; then
	sudo cp driver/usb/90-usb_3bp.rules /etc/udev/rules.d/90-usb.rules
elif [[ "$model" == "Raspberry Pi 4 Model B" ]]; then
	sudo cp driver/usb/90-usb_4b.rules /etc/udev/rules.d/90-usb.rules
else
	echo "This device is not a Raspberry Pi."
	exit 1
fi

### python・サービス・設定ファイル等を移行する
echo === Copy Files ===
sudo chmod 755 -R src/*
sudo cp src/* /usr/local/bin/pinode3
sudo chmod 777 service/*
sudo cp service/* /etc/systemd/system/
sudo mkdir -p /home/pinode3/data/sensor/lost
sudo mkdir -p /home/pinode3/data/image
sudo cp src/previous_sensor_data.json /home/pinode3/data/sensor
sudo cp config.json /home/pinode3/
sudo chmod 666 /home/pinode3/config.json
sudo chmod -R 777 /home/pinode3/data

### サービスファイルの登録
echo === Register Service File ===
sudo systemctl daemon-reload
sudo systemctl start data_collector.timer
sudo systemctl start data_collector.service