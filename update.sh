#!/bin/bash

echo "=== Python/サービス/設定ファイルの更新 ==="

# `src/*` を `/usr/local/bin/pinode3` に再コピー
sudo chmod 755 -R src/*
sudo cp src/* /usr/local/bin/pinode3

# serviceファイルの再登録（必要であれば）
sudo chmod 777 service/*
sudo cp service/* /etc/systemd/system/

# 設定ファイルの更新
sudo cp config.json /home/pinode3/
sudo chmod 666 /home/pinode3/config.json

# systemd 再読み込みとサービスの再起動（任意）
echo "=== systemd サービスの再起動 ==="
sudo systemctl daemon-reload
sudo systemctl restart data_collector.service
sudo systemctl restart cpu_checker.service

echo "=== 更新完了 ==="
