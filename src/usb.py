import os
import subprocess

class USB:
    """
    USBからの情報取得
    """
    def get(self):
        self.ports = self._get_connect_ports()
        self.identifys = [self._identify_usb_device(port) for port in self.ports]
        self.names = [
            self._get_spresense_name(port) if identify == 'SPRESENSE' else self._get_usb_camera_name(port)
            for port, identify in zip(self.ports, self.identifys)
        ]
        return list(sorted(zip(self.ports, self.identifys, self.names), key=lambda x: x[0]))

    ### 接続されているUSBデバイスのポートを確認
    # 1 -> 左上
    # 2 -> 左下
    # 3 -> 右上
    # 4 -> 右下
    def _get_connect_ports(self):
        usb_ports = []
        devices = os.listdir('/dev/')
        for device in devices:
            if 'ttyUSB_' in device:
                usb_ports.append(int(device[-1]))
        return usb_ports

    ### 指定したポートのデバイスの種類を特定（USB CameraかSPRESENSEのみ）
    def _identify_usb_device(self, port):
        device = '/dev/ttyUSB_' + str(port)
        if 'ttyUSB' in os.readlink(device):
            return 'SPRESENSE'
        else:
            return 'USB Camera'

    ### SPRESENSEの接続に必要なデバイス名の取得
    def _get_spresense_name(self, port):
        return '/dev/ttyUSB_' + str(port)

    ### USB Cameraの接続に必要な番号の取得
    def _get_usb_camera_name(self, port):
        assert port in [1, 2, 3, 4]
        model = subprocess.check_output('sudo cat /proc/cpuinfo'.split()).decode()
        device_name = ''
        if 'Raspberry Pi 3 Model B Plus' in model:
            if port == 1:
                device_name = '0:1.1.2:1.0-video'
            elif port == 2:
                device_name = '0:1.1.3:1.0-video'
            elif port == 3:
                device_name = '0:1.3:1.0-video'
            elif port == 4:
                device_name = '0:1.2:1.0-video'
            else:
                raise ValueError("unknown port")
        elif 'Raspberry Pi 4 Model B' in model:
            if port == 1:
                device_name = '0:1.3:1.0-video'
            elif port == 2:
                device_name = '0:1.4:1.0-video'
            elif port == 3:
                device_name = '0:1.1:1.0-video'
            elif port == 4:
                device_name = '0:1.2:1.0-video'
            else:
                raise ValueError("unknown port")
        else:
            device_name = '0:1.' + str(port + 1) + ':1.0-video'

        devices = os.listdir('/dev/v4l/by-path')
        for device in devices:
            if device_name in device:
                retVal = int(os.readlink('/dev/v4l/by-path/' + device)[-1])
                if retVal % 2 == 0:
                    return retVal
        raise ValueError("unknown port")