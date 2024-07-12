import os
import subprocess

class USB:
    """
    USBからの情報取得
    camera.pyから呼び出される
    camera.pyから呼び出される
    """
    def get(self):
        """
        USB接続されている機器の情報をリストとして一括で取得するメソッド
        USB機器が複数接続されている場合は各要素は配列として取得される

        Returns:
        [(self.ports,self.identifys,self.names)] list(int,str,str): ポート番号順に整列

        Details:
        self.ports(list[int]) : USB接続している機器のポート番号
        self.identifys(list(str)) : ポート番号に対するデバイス名(SPRESENSE or USB Camera)
        self.names :(list[str]) (SPRESENSEの場合)接続ポート番号ごとのデバイスファイルパス
                    (list(int)) (USB Cameraの場合)デバイスID
        """
        self.ports = self._get_connect_ports()
        self.identifys = [self._identify_usb_device(port) for port in self.ports]
        self.names = [
            self._get_spresense_name(port) if identify == 'SPRESENSE' else self._get_usb_camera_name(port)
            for port, identify in zip(self.ports, self.identifys)
        ]
        return list(sorted(zip(self.ports, self.identifys, self.names), key=lambda x: x[0]))

    
    def _get_connect_ports(self):
        """
        接続されているデバイスのUSBポート番号を配列として取得
        
        Returns:
        usb_ports(list[int]): USB接続している機器のポート番号

        Details:
        配列内の各値は以下の意味を持つ．
        # 1 -> 左上
        # 2 -> 左下
        # 3 -> 右上
        # 4 -> 右下
        """
        usb_ports = []
        devices = os.listdir('/dev/')
        for device in devices:
            if 'ttyUSB_' in device:
                usb_ports.append(int(device[-1]))
        return usb_ports

    def _identify_usb_device(self, port):
        """
        接続されているUSB機器のデバイス名を取得
        
        Parameters: 
        port(list[int]): USB接続している機器のポート番号

        Returns:
        'SPRESENSE'(str) or 'USB Camera'(str) : ポート番号に対するデバイス名

        Details:
        '/dev/ttyUSB_' + USBポート番号 で指定されたパスにシンボリックリンクが存在する
        シンボリックリンクの参照物のパス内にttyUSBが含まれていればSPRESENSE,入っていなければUSB Cameraの文字列を返す
        """
        device = '/dev/ttyUSB_' + str(port)
        if 'ttyUSB' in os.readlink(device):
            return 'SPRESENSE'
        else:
            return 'USB Camera'

    def _get_spresense_name(self, port):
        """
        Parameters:
        port(list[int]): USB接続している機器のポート番号

        Returns:
        SPRESENSEのデバイスファイルへのパス(str)
        /dev/ttyUSB_1 - /dev/ttyUSB_4 のどれか

        """
        return '/dev/ttyUSB_' + str(port)

    def _get_usb_camera_name(self, port):
        """
        USBカメラのデバイスIDを取得
        opencvでのカメラキャプチャ等で使用
        
        Parameters: 
        port(list[int]): USB接続している機器のポート番号

        Returns:
        retVal(int): USBカメラのデバイスID (0 or 1)

        Details:
        model(str): 接続機器名(Raspberry pi 3 Model B Plus, RasPberry pi 4 Model B等)
            RasPi3とRasPi4では作成されるシンボリック名が異なるため条件文で検索文字を指定
            接続ポートによっても名称が異なる．
        devices(list[str]): 接続デバイスのシンボリックリンクのパス
            シンボリックリンク参照先のパスの最後の値を取得
            シンボリックリンク('/dev/v4l/by-path/?????') -> 機器(path/???1) の最後の値がデバイスIDである
        retval(int): 
            USB接続するとシンボリックリングが2個生成される.取得する名前を小さい数字にするために
            if retVal % 2 == 0: の条件文を追加

        """

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