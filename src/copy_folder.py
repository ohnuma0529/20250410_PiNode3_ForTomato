import subprocess
from datetime import datetime, timedelta
import json
import os
import shutil

import util

def copy_folder_to_remote(local_folder, remote_ip, remote_user, remote_path, password):
    """
    指定したフォルダをリモートPCにパスワード認証でコピーし、成功したらローカルデータを削除する。

    :param local_folder: ローカルのフォルダパス（例: "/home/user/data"）
    :param remote_ip: リモートPCのIPアドレス（例: "192.168.1.100"）
    :param remote_user: リモートPCのユーザー名（例: "ubuntu"）
    :param remote_path: リモートPCのコピー先ディレクトリ（例: "/home/ubuntu/backup"）
    :param password: SSHログインのパスワード
    """
    # yesterday_time = datetime.now() - timedelta(days=1)
    # date = yesterday_time.strftime('%Y%m%d')
    # local_folder = os.path.join(local_folder, date)

    # フォルダが存在しない場合はスキップ
    if not os.path.exists(local_folder):
        print(f"⚠️ {local_folder} が存在しません。処理をスキップします。")
        return

    # コピーコマンド
    scp_command = [
        "sshpass", "-p", password,
        "scp", "-o", "StrictHostKeyChecking=no", "-r", 
        local_folder,  # コピー元はローカル
        f"{remote_user}@{remote_ip}:{remote_path}"  # コピー先はリモート
    ]


    try:
        subprocess.run(scp_command, check=True)
        print(f"✅ {local_folder} を {remote_user}@{remote_ip}:{remote_path} にコピー完了！")

        # 成功した場合、ローカルフォルダを削除
        shutil.rmtree(local_folder)
        print(f"🗑️ {local_folder} を削除しました。")

    except subprocess.CalledProcessError as e:
        print(f"❌ エラー: {e}")
    except Exception as e:
        print(f"❌ フォルダ削除エラー: {e}")

if __name__ == "__main__":
    pinode_config   = util.get_pinode_config()
    device_id       = pinode_config["device_id"]
    local_dir    = pinode_config["copy_folder"]["edge_savepath"]
    remote_ip       = pinode_config["copy_folder"]["server_IP"]
    remote_user     = pinode_config["copy_folder"]["server_user"]
    remote_dir     = pinode_config["copy_folder"]["server_savepath"]
    password        = pinode_config["copy_folder"]["server_password"]
    
    usb_list        = ["image1", "image2", "image3", "image4"]
    now_date       = datetime.now().strftime('%Y%m%d')
    yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    # yesterday_date = "past_image"
    for usb in usb_list:
        local_folder = os.path.join(local_dir, usb, yesterday_date)
        remote_folder = os.path.join(remote_dir, device_id, usb)
        remote_folder = os.path.join(remote_folder, yesterday_date)
        copy_folder_to_remote(local_folder, remote_ip, remote_user, remote_folder, password)
