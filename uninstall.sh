# スクリプトファイルの削除
rm -r /usr/local/bin/pinode3

# サービスファイルの削除
systemctl stop data_collector.timer
systemctl stop data_collector.service
systemctl disable data_collector.timer
systemctl disable data_collector.service
rm /etc/systemd/system/data_collector.timer
rm /etc/systemd/system/data_collector.service

# systemd のデーモンをリロード
systemctl daemon-reload

echo "uninstall success"