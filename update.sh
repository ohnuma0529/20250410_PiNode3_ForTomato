#!/bin/bash

echo "=== Python/サービス/設定ファイルの更新 ==="

sudo chmod 755 -R src/*
sudo cp src/* /usr/local/bin/pinode3
sudo chmod 777 service/*
sudo cp service/* /etc/systemd/system/
sudo mkdir -p /home/pinode3/data/sensor/lost
sudo mkdir -p /home/pinode3/data/image/image1
sudo mkdir -p /home/pinode3/data/image/image2
sudo mkdir -p /home/pinode3/data/image/image3
sudo mkdir -p /home/pinode3/data/image/image4
sudo cp src/previous_sensor_data.json /home/pinode3/data
sudo cp config.json /home/pinode3/
sudo chmod 666 /home/pinode3/config.json
sudo chmod -R 777 /home/pinode3/data

# systemd 再読み込みとサービスの再起動（任意）
echo "=== systemd サービスの再起動 ==="

sudo systemctl daemon-reload
sudo systemctl start data_collector.timer
sudo systemctl enable data_collector.timer
sudo systemctl start data_collector.service
sudo systemctl start copy_folder.timer
sudo systemctl enable copy_folder.timer
sudo systemctl start cpu_checker.service
sudo systemctl enable cpu_checker.service
sudo systemctl start wilt.timer
sudo systemctl enable wilt.timer
sudo systemctl start wilt.service
sudo systemctl enable daily_reboot.timer
sudo systemctl start daily_reboot.timer

echo "=== 更新完了 ==="
