import cv2
import timeout_decorator
import subprocess
import time
from cobs import cobs
import serial
import json
import datetime as dt

from pathlib import Path

from usb import USB
import util

class Camera:
    def __init__(self):
        self.config = util.get_pinode_config()

    def save_images(self):
        devices = USB().get()
        for port, type, name in devices:
            if type == 'SPRESENSE':
                file_name = "image{:1}/{}_{:02}_HDR_{}.jpg".format(port, self.config['device_id'], port, dt.datetime.now().strftime('%Y%m%d-%H%M'))
                SPRESENSE(name).save(file_name)
            elif type == 'USB Camera':
                file_name = "image{:1}/{}_{:02}_RGB_{}.jpg".format(port, self.config['device_id'], port, dt.datetime.now().strftime('%Y%m%d-%H%M'))
                UsbCamera(name).save(file_name)

class SPRESENSE:
    BAUD_RATE   = 115200  # ボーレート
    BUFF_SIZE   = 100  # 1回の通信で送られてくるデータサイズ
    TYPE_INFO   = 0
    TYPE_IMAGE  = 1
    TYPE_FINISH = 2
    TYPE_ERROR  = 3

    def __init__(self, port_num):
        self.port_num = port_num
        self.config = util.get_pinode_config()

    def save(self, file_name):
        local_file_path = str(Path(self.config['camera']['image_dir']['local']) / Path(file_name))

        # 3回実行してエラーの場合は終了する
        for i in range(3):
            try:
                with serial.Serial(self.port_num, self.BAUD_RATE, timeout = 3) as ser:
                    time.sleep(2)     # Arduino側との接続のための待ち時間
                    img = self._get_image_data(ser)
                    print(f"save image : {local_file_path}")
                    with open(local_file_path, "wb") as f:
                        f.write(img)
                return True
            except Exception as e:
                print(e)
                self._reboot()
        print("failed to get image")
        return False

    def _reboot(self):
        subprocess.call("sudo sh -c \"echo -n \"1-1\" > /sys/bus/usb/drivers/usb/unbind\"", shell=True)
        time.sleep(1)
        subprocess.call("sudo sh -c \"echo -n \"1-1\" > /sys/bus/usb/drivers/usb/bind\"", shell=True)
        time.sleep(5)

    def _get_packet(self, ser):
        try:
            img = b''
            while True:
                val = ser.read()
                if val == b'\x00':
                    break
                img += val
            decoded = cobs.decode(img)
            index = int(decoded[1]) * 1000 + int(decoded[2]) * 100 + int(decoded[3]) * 10 + int(decoded[4])
            return decoded[0], index, decoded[5:]
        except Exception as e:
            return self.TYPE_ERROR, 0, b''

    def _check_packet(self, data):
        if len(data) != self.BUFF_SIZE:
            return False
        return True

    def _send_request_image(self, ser):
        ser.write(str.encode('S\n'))

    def _send_complete_image(self, ser):
        ser.write(str.encode('E\n'))

    def _send_request_resend(self, ser, index):
        ser.write(str.encode(f'R{index}\n'))

    @timeout_decorator.timeout(50, use_signals=False)
    def _get_image_data(self, ser):
        img = b''
        resend_index_list = []
        finish_flag = False
        send_flg = []

        self._send_request_image(ser)

        while True:
            code, index, data = self._get_packet(ser)

            # データ取得
            if code == self.TYPE_INFO:
                img = bytearray(index * self.BUFF_SIZE)
                max_index = index
                send_flg = [False] * max_index
            elif code == self.TYPE_IMAGE:
                if self._check_packet(data):
                    img[index*self.BUFF_SIZE:(index+1)*self.BUFF_SIZE] = data
                    send_flg[index] = True
                    if index in resend_index_list:
                        resend_index_list.remove(index)
                else:
                    resend_index_list.append(index)
            elif code == self.TYPE_FINISH:
                img += data
                finish_flag = True
            elif code == self.TYPE_ERROR:
                print('cant get data')

            # 終了チェック
            if finish_flag:
                if False in send_flg:
                    print("resend", send_flg.index(False))
                    self._send_request_resend(ser, send_flg.index(False))
                for index in resend_index_list:
                    self._send_request_resend(ser, index)
                if (len(resend_index_list) == 0) and (not (False in send_flg)):
                    self._send_complete_image(ser)
                    break
        return img

class UsbCamera:
    def __init__(self, device_name):
        self.config = util.get_pinode_config()
        self.device_name = device_name
    
    @timeout_decorator.timeout(20)
    def save(self, file_name):
        cap = cv2.VideoCapture(self.device_name, cv2.CAP_V4L)
        for _ in range(50):
            ret, frame = cap.read()
        if not ret:
            return False

        local_file_path = str(Path(self.config['camera']['image_dir']['local']) / Path(file_name))
        print(f"save image : {local_file_path}")
        cv2.imwrite(local_file_path, frame)
        return True