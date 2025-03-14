import time
import signal
import sys

import pigpio


# --------------------------------------
# デバッグ用。Trueにすると動きません
SHOW_TERM       = False
SHOW_UART       = False
# --------------------------------------


# --------------------------------------
# pigpioでは数値だけで呼ぶものを、ラズパイのピン名称で呼び出します
GPIO18_LED      = 18                # 12  GPIO18_LED        LED_G
# --------------------------------------
GPIO12_DSW1     = 12                # 32  GPIO12_DSW1       SW1_1
GPIO12_DSW2     = 16                # 36  GPIO16_DSW2       SW1_2
GPIO12_DSW3     = 20                # 38  GPIO20_DSW3       SW1_3
GPIO12_DSW4     = 21                # 40  GPIO21_DSW4       SW1_4
# --------------------------------------
GPIO04_I2CEN1_  =  4                # 07  GPIO04_I2CEN1#    SCLE1, SDAE1 (SHT25)
GPIO05_I2CEN2_  =  5                # 29  GPIO05_I2CEN2#    SCLE2, SDAE2 (RL78/S1133, Int)
GPIO06_I2CEN3_  =  6                # 31  GPIO06_I2CEN3#    SCLE3, SDAE3 (RL78/S1133, Ext)
GPIO13_I2CEN4_  = 13                # 33  GPIO13_I2CEN4#    SHT85
GPIO19_I2CEN5_  = 19                # 35  GPIO19_I2CEN5#    I2C CN8
# --------------------------------------
GPIO25_SPI_OE_  = 25                # 22  GPIO25_SPI_OE#    SPI Ext CN11
# --------------------------------------
ADDR_I2C1       = 0x40              # 0x40  SHT25
ADDR_I2C2       = 0x30              # 0x30  RL78/S1133, Int
ADDR_I2C3       = 0x31              # 0x31  RL78/S1133, Ext
ADDR_I2C4       = 0x44              # 0x44  SHT85
ADDR_I2C5       = 0x44              # 0x44  SHT85
# ADDR_I2C5       = 0xNN              # 0xNN  I2C CN8
# --------------------------------------
SPI0_BUS        = 0                 # 24  CE0#              ADC MCP3204
SPI0_CLK_HZ     = 1000000           # 
SPI0_MODE       = 3                 # 
# 
SPI1_BUS        = 1                 # 26  CE1#              SPI Ext CN11
SPI1_CLK_HZ     = 1000000           # 
SPI1_MODE       = 3                 # 
# --------------------------------------
UART0_DEV       = "/dev/ttyS0"      # 08  TXD0              debug
UART0_BAUD      = 115200            # 10  RXD0              debug
# --------------------------------------


# --------------------------------------
g_huart0 = 0
# --------------------------------------


def signal_handler(signal, frame):
    """
    デバッグ用
    """
    global quit
    
    quit = True
    show_term("\n")


def show_term(text):
    """
    デバッグ用
    """
    if SHOW_TERM:
        print(text, end="")
    
    return


def show_uart(pi, text):
    """
    デバッグ用
    """
    if SHOW_UART:
        uart_write(pi, text)
    
    return


def led_show(pi, on):
    """
    LED点灯用関数.未使用
    """
    pi.write(GPIO18_LED, on)
    
    if on == 1:
        state = "On"
    else:
        state = "Off"
    
    show_term("LED:        {0}\n".format(state))
    show_uart(pi, "LED:        {0}\n".format(state))
    
    return on



def dsw_read(pi):
    """
    Raspberry_piでのデジタルスイッチ(DIPスイッチ)の状態を読み取るためのメソッド
    
    Returns:
        dsw (int): 各種スイッチ状態をまとめた結合値
    
    Notes:
        各種操作を以下に示す．重複内容は割愛
        
        dsw1 = pi.read(12): GPIOピン12の状態(ON=0,OFF=1)を読み取りdsw1に代入
        
        dsw1 = ~dsw1 & 0x01: 読み取ったスイッチの状態 (dsw1) を反転. (ON=1,OFF=0)
        
        dsw  = (dsw4 << 3) | (dsw3 << 2) | (dsw2 << 1) | (dsw1 << 0):
        
        各種スイッチの反転した状態の値をビットシフト演算で結合.   
    """
    dsw1 = pi.read(12)
    dsw2 = pi.read(16)
    dsw3 = pi.read(20)
    dsw4 = pi.read(21)
    
    dsw1 = ~dsw1 & 0x01
    dsw2 = ~dsw2 & 0x01
    dsw3 = ~dsw3 & 0x01
    dsw4 = ~dsw4 & 0x01
    
    dsw  = (dsw4 << 3) | (dsw3 << 2) | (dsw2 << 1) | (dsw1 << 0)
    
    show_term("DSW(4321):  {0}{1}{2}{3}\n".format(dsw4, dsw3, dsw2, dsw1))
    show_uart(pi, "DSW(4321):  {0}{1}{2}{3}\n".format(dsw4, dsw3, dsw2, dsw1))
    
    return dsw


def sht25_read(pi):
    """
    温湿度センサからのデータを読み取り送信するメソッド
    
    Returns:
        fT(float): 温度
        fH(float): 湿度
    
    Attributes:
        ADDR_I2C1 (constants): I2Cデバイスのアドレス
    
    Notes:
        pi.write(GPIO04_I2CEN1_, 0): GPIOピン GPIO04_I2CEN1_からの信号を読み取るためのモードに変更
        
        
        pi.i2c_open(1, addr, 0): I2Cデバイスとの通信を準備
            
            第1引数: 使用するI2Cバスの番号を指定. Raspberry Piの場合は'1'はI2Cバス1を指す
            
            第2引数: I2Cデバイスのアドレス
            
            第3引数: オプションフラグ. 基本的には0を指定
        
        pi.i2c_write_byte(handle, 0xE3): センサへ0xE3コマンドを送信.温度データを取得開始                     
        
        rxrT, rxdT = pi.i2c_read_device(handle, 3):
        
        通信準備されたI2Cデバイスから温度データを読み取る.今回の場合は3バイトのデータを読み取る
        
        rxrT: 読み取りの結果やエラーコードなど、通信の成否や追加のステータス情報を格納
        
            rxrT = 3: 指定したバイト数（この場合は3バイト）が正常に読み取られたことを示す
        
            rxrT = 0: 実行失敗時意図的に0に設定
        
                      rxrTが0以下の場合,エラーとして処理
        
        rxdT: 実際に読み取ったデータを格納
    
        pi.i2c_write_byte(handle, 0xE3): センサへ0xE3コマンドを送信.湿度データを取得開始                     
    
        rxrH, rxdH = pi.i2c_read_device(handle, 3):
    
            通信準備されたI2Cデバイスから温度データを読み取る.今回の場合は3バイトのデータを読み取る
    
            rxrH: 読み取りの結果やエラーコードなど、通信の成否や追加のステータス情報を格納
    
                rxrH = 3: 指定したバイト数（この場合は3バイト）が正常に読み取られたことを示す
    
                rxrH = 0: 実行失敗時意図的に0に設定 
    
            rxdH: 実際に読み取ったデータを格納
    
        pi.i2c_close(handle): I2Cハンドルを閉じてリソースを解放
    
        pi.write(GPIO04_I2CEN1_, 1): GPIOピン GPIO04_I2CEN1_を外部のデバイスや回路に信号を送るためのモードに変更
    
        以下の操作を温度センサ，湿度センサから得た測定値に対して実行
    
            受け取った3バイトのデータからセンサ測定値を抽出.正しくデータが得られなかった場合すべてのデータ値を0とする.
    
        各センサで固有の変換式に基づいて生データを物理量に変換して温度，湿度を返却
    
    """
    addr = ADDR_I2C1                            
    
    pi.write(GPIO04_I2CEN1_, 0)
    
    handle = pi.i2c_open(1, addr, 0)
    
    try:
        pi.i2c_write_byte(handle, 0xE3)
        rxrT, rxdT = pi.i2c_read_device(handle, 3)
    except:
        rxrT = 0
    
    try:
        pi.i2c_write_byte(handle, 0xE5)
        rxrH, rxdH = pi.i2c_read_device(handle, 3)
    except:
        rxrH = 0
    
    pi.i2c_close(handle)
    
    pi.write(GPIO04_I2CEN1_, 1)
    
    if rxrT > 0:
        nT = (rxdT[0] << 8) | (rxdT[1] & 0xFC)
    else: 
        nT = 0
    
    if rxrH > 0:
        nH = (rxdH[0] << 8) | (rxdH[1] & 0xFC)
    else:
        nH = 0
    
    fT = -46.85 + 175.72 * (nT / 65536)
    fH =  -6.00 + 125.00 * (nH / 65536)
    
    show_term("SHT25:      tmp: {0:6.3f}, hum: {1:6.3f}".format(fT, fH))
    show_uart(pi, "SHT25:      tmp: {0:6.3f}, hum: {1:6.3f}".format(fT, fH))
    show_uart(pi, "\n")
    
    show_term("\n")
    
    return fT, fH


def s1133_int():
    """
    光度センサからのデータを読み取り送信するメソッド
    
    Returns:
        lux(int): 光の強度
    
    Attributes:
        ADDR_I2C2 (constants): I2Cデバイスのアドレス
    
    Notes:
        
        pi.write(GPIO05_I2CEN2_, 0): GPIOピン GPIO05_I2CEN2_からの信号を読み取るためのモードに変更
        
        pi.i2c_open(1, addr, 0): I2Cデバイスとの通信を準備
            
            第1引数: 使用するI2Cバスの番号を指定. Raspberry Piの場合は'1'はI2Cバス1を指す
            
            第2引数: I2Cデバイスのアドレス
            
            第3引数: オプションフラグ. 基本的には0を指定
        
        rxr, rxd = pi.i2c_read_device(handle, 3):
        
            通信準備されたI2Cデバイスからデータを読み取る.今回の場合は3バイトのデータを読み取る
        
            rxr: 読み取りの結果やエラーコードなど、通信の成否や追加のステータス情報を格納
        
                rxr = 3: 指定したバイト数（この場合は3バイト）が正常に読み取られたことを示す
        
                rxr = 0: バイト数が0で、何も読み取られなかったことを示す
        
                        rxrが0以下の場合,エラーとして処理
        
            rxd: 実際に読み取ったデータを格納
        
        pi.i2c_close(handle): I2Cハンドルを閉じてリソースを解放
        
        pi.write(GPIO05_I2CEN2_, 1): GPIOピン GPIO05_I2CEN2_を外部のデバイスや回路に信号を送るためのモードに変更
        
        受け取った3バイトのデータからセンサ測定値を抽出.
        
        正しくデータが得られなかった場合すべてのデータ値を0とする.
        
        センサ固有の変換式に基づいて生データを物理量に変換後返却
    """
    addr = ADDR_I2C2                       
    
    pi.write(GPIO05_I2CEN2_, 0)
    
    handle = pi.i2c_open(1, addr, 0)
    
    rxr, rxd = pi.i2c_read_device(handle, 3)
    
    pi.i2c_close(handle)
    
    pi.write(GPIO05_I2CEN2_, 1)
    
    if rxr > 0:
        val = ((rxd[0] & 0xff) << 4) | ((rxd[1] & 0xf0) >> 4)
        rng = ((rxd[1] & 0x0c) >> 2)
        dsw = ((rxd[1] & 0x02) >> 1)
        lvd = ((rxd[1] & 0x01) >> 0)
    else:
        val = 0
        rng = 0
        dsw = 0
        lvd = 0
    
    div = (1, 1, 4, 16)
    lux = int(val / 4096 * 250000 / div[rng])
    
    show_term("S1133in:    lux: {0:6d}, rng: {1}, dsw: {2}, lvd: {3}, ".format(lux, rng, dsw, lvd))
    show_uart(pi, "S1133in:    lux: {0:6d}, rng: {1}, dsw: {2}, lvd: {3}, ".format(lux, rng, dsw, lvd))
    show_uart(pi, "\n")
    
    show_term("\n")
    
    return lux
    
    
def s1133_ext():
    """
    光度センサからのデータを読み取り送信するメソッド
    
    Returns:
        lux (int): 光の強度
    
    Attributes:
        ADDR_I2C3 (constants): I2Cデバイスのアドレス
    
    Notes:
        他部分はdef s1133_int()と同様のため割愛.
    """
    addr = ADDR_I2C3                                          
    
    pi.write(GPIO06_I2CEN3_, 0)
    
    handle = pi.i2c_open(1, addr, 0)
    
    rxr, rxd = pi.i2c_read_device(handle, 3)
    
    pi.i2c_close(handle)
    
    pi.write(GPIO06_I2CEN3_, 1)
    
    if rxr > 0:
        val = ((rxd[0] & 0xff) << 4) | ((rxd[1] & 0xf0) >> 4)
        rng = ((rxd[1] & 0x0c) >> 2)
        dsw = ((rxd[1] & 0x02) >> 1)
        lvd = ((rxd[1] & 0x01) >> 0)
    else:
        val = 0
        rng = 0
        dsw = 0
        lvd = 0
    
    div = (1, 1, 4, 16)
    lux = int(val / 4096 * 250000 / div[rng])
    
    show_term("S1133ex:    lux: {0:6d}, rng: {1}, dsw: {2}, lvd: {3}, ".format(lux, rng, dsw, lvd))
    show_uart(pi, "S1133ex:    lux: {0:6d}, rng: {1}, dsw: {2}, lvd: {3}, ".format(lux, rng, dsw, lvd))
    show_uart(pi, "\n")
    
    show_term("\n")
    
    return lux
    

def sht85_read(pi):
    """
    強制通風筒からのデータを読み取り送信するメソッド
    
    Returns:
        fT(float): 温度
        fH(float): 湿度
        
    Attributes:
        ADDR_I2C4 (constants): I2Cデバイスのアドレス
    
    Notes:
        pi.write(GPIO13_I2CEN4_, 0): GPIOピン GPIO13_I2CEN4_からの信号を読み取るためのモードに変更
        
        pi.i2c_open(1, addr, 0): I2Cデバイスとの通信を準備
        
            第1引数: 使用するI2Cバスの番号を指定. Raspberry Piの場合は'1'はI2Cバス1を指す
        
            第2引数: I2Cデバイスのアドレス
        
            第3引数: オプションフラグ. 基本的には0を指定
            
        txd = bytearray([0x24, 0x00]): センサへの送信コマンドを指定. コマンド(0x24, 0x00)は測定開始を表す
        
        pi.i2c_write_device(handle, txd): センサへコマンドを送信を実行
                                        
        rxr, rxd = pi.i2c_read_device(handle, 6):
        
            通信準備されたI2Cデバイスからデータを読み取る.今回の場合は6バイトのデータを読み取る
        
            rxr: 読み取りの結果やエラーコードなど、通信の成否や追加のステータス情報を格納
        
                rxr = 6: 指定したバイト数（この場合は6バイト）が正常に読み取られたことを示す
        
                rxr = 0: バイト数が0で、何も読み取られなかったことを示す
        
                        rxrが0以下の場合,エラーとして処理. 実行失敗時意図的に0に設定
        
            rxd: 実際に読み取ったデータを格納
        
        pi.i2c_close(handle): I2Cハンドルを閉じてリソースを解放
        
        pi.write(GPIO13_I2CEN4_, 1): GPIOピン GPIO13_I2CEN4_を外部のデバイスや回路に信号を送るためのモードに変更
        
        受け取った6バイトのデータからセンサ測定値を抽出. 正しくデータが得られなかった場合すべてのデータ値を0とする.
        
        センサ固有の変換式に基づいて生データを物理量に変換後返却
    """
    addr = ADDR_I2C4                                          
    
    pi.write(GPIO13_I2CEN4_, 0)
    
    handle = pi.i2c_open(1, addr, 0)
    
    txd = bytearray([0x24, 0x00])
    try:
        pi.i2c_write_device(handle, txd)
        time.sleep(0.2)
        rxr, rxd = pi.i2c_read_device(handle, 6)
    except:
        rxr = 0
    
    pi.i2c_close(handle)
    
    pi.write(GPIO13_I2CEN4_, 1)
    
    if rxr > 0:
        nT = (rxd[0] << 8) | (rxd[1] << 0)
        nH = (rxd[3] << 8) | (rxd[4] << 0)
    else:
        nT = 0
        nH = 0
    
    fT = -45.00 + 175.00 * (nT / 65535)
    fH =   0.00 + 100.00 * (nH / 65535)
    
    show_term("SHT85:      tmp: {0:6.3f}, hum: {1:6.3f}".format(fT, fH))
    show_uart(pi, "SHT85:      tmp: {0:6.3f}, hum: {1:6.3f}".format(fT, fH))
    show_uart(pi, "\n")
    
    show_term("\n")
    
    return fT, fH


def mcp3204_read(pi, ch):
    """
    茎径センサ値,果実径値を取得するためのメソッド
    
    Args:
        pi (piogio.pi): pigpioライブラリのインスタンス. GPIOピンを制御するために使用
        ch (int) : MPC3204のチャンネル番号 (0 or 1)
    
    Returns:
        fV: 茎径センサ値, 果実径センサ値
    
    Notes:
        pi.write(GPIO25_SPI_OE_, 1): GPIOピン GPIO25_SPI_OE_からの信号を読み取るためのモードに変更
        
        pi.spi_open(SPI0_BUS, SPI0_CLK_HZ, SPI0_MODE): 
        
            SPIバス0を開き,指定のクロック速度とモードで通信を開始
        
            SPI0_BUS        = 0       
        
            SPI0_CLK_HZ     = 1000000          
        
            SPI0_MODE       = 3   
        
        
        SPI通信ではMCP3204に対する3バイトのSPIコマンドが必要となる
        
        xferメソッドで指定する各バイトの値
        
            1バイト目: （0、0、0、0、0、Start、SGL/DIFF、D2）
        
            2バイト目: （D1、D0、何でもよいから6ビット分）
        
            3バイト目:  なんでもよい8ビット(ダミービット)
            
        chをこのフォーマットに適応するように整形を行う
        
        ch = ch & 0x07: chの下位3ビットのみを抽出. 0b00000CCC (0～7)の形に整形
        
        txd = (0x06 | (ch > 2), 0x00 | (ch << 6), 0x00): MCP3204に対して適切なチャネルを指定するための3バイトのSPIコマンドを準備
        
            0x06 | (ch > 2): 1バイト目  
                            
                            '0606'(0b00000110): シングルエンドモードでの実行を指す．
                            
                            (ch > 2): チャンネルのサイズに従って'0606'(0b00000011'0')の最終桁を'0'か'1'にするかを決定する. 
                            
                            この操作を行うことで, ch<3の場合('0606')とch>=3の場合('0607')で分かれるチャンネル指定を正常に行うことができる
            
            0x00 | (ch << 6): 2バイト目  
                            
                            ch = ch & 0x07: chは左づめの3bitに意味を持つビットが存在する状態にする.実際はchは0～3の値であり,意味を持つ値は2ビット分である. 
                            
                            (ch << 6): 6ビットだけchをシフトさせることで意味を持つビットをxferメソッド指定するビット位置に割り当てる. 最後に0x00との or演算を行うことで必要ビット以外のビット位置を0とし,指定フォーマットのバイトを作成する
            
            0x00: 3バイト目: xferメソッド実行時に必要であるが特別送信するデータがないためダミービットを指定する
            
        rxr, rxd = pi.spi_xfer(h, txd) の返却物
            
            rxr: 読み取りの結果やエラーコードなど、通信の成否や追加のステータス情報を格納
            
            rxd (list): rxd[0]: 1番目のバイト: 最初の送信データに対するMCP3204からの応答. (一般的には無視される)  
            
                        rxd[1]: 2番目のバイト: 下位4ビットにデータが含まれる
            
                        rxd[2]: 3番目のバイト: 8ビットすべてにデータが含まれる
            
        pi.i2c_close(handle): I2Cハンドルを閉じてリソースを解放
        
        pi.write(GPIO13_I2CEN4_, 1): GPIOピン GPIO13_I2CEN4_を外部のデバイスや回路に信号を送るためのモードに変更
        
        nV = ((rxd[1] << 8) | (rxd[2] << 0)) & 0x0fff: rxdのうちrxd[1]とrxd[2]の意味を持つビットを12ビットデータとしてnVに格納
        
        センサ固有の変換式に基づいて生データ(nV)を物理量に変換後返却
    """
    pi.write(GPIO25_SPI_OE_, 1)
    
    h = pi.spi_open(SPI0_BUS, SPI0_CLK_HZ, SPI0_MODE)         
    
    ch = ch & 0x07
    txd = (0x06 | (ch > 2), 0x00 | (ch << 6), 0x00)
    
    rxr, rxd = pi.spi_xfer(h, txd)
    
    pi.spi_close(h)
    
    pi.write(GPIO25_SPI_OE_, 0)
    
    nV = ((rxd[1] << 8) | (rxd[2] << 0)) & 0x0fff
    
    if ch == 0:
        fV = nV / 4095.0 * 2.048 * 5 / 2
    elif ch == 1:
        fV = nV / 4095.0 * 2.048 * 2 / 2
    else:
        fV = 0.0
    
    if ch == 0:
        typ = "S"
    elif ch == 1:
        typ = "F"
    else:
        typ = " "
    
    show_term("MCP3204({0}): vol: {1:6.3f}".format(typ, fV))
    show_uart(pi, "MCP3204({0}): vol: {1:6.3f}".format(typ, fV))
    show_uart(pi, "\n")
    
    show_term("\n")
    
    return fV


def mcp3204ex_read(pi, ch):
    """
    茎径センサの値を取得するためのメソッド
    
    Args:
        pi(piogio.pi): pigpioライブラリのインスタンス. GPIOピンを制御するために使用
        ch: MPC3204のチャンネル番号
    
    Returns:
        fV: 果実径センサ値
        
    Notes:
        未使用
    """
    
  
    pi.write(GPIO25_SPI_OE_, 0)
    
    h = pi.spi_open(SPI1_BUS, SPI1_CLK_HZ, SPI1_MODE)  
    
    ch = ch & 0x07
    txd = (0x06 | (ch > 2), 0x00 | (ch << 6), 0x00)
    
    rxr, rxd = pi.spi_xfer(h, txd)
    
    pi.spi_close(h)
    
    pi.write(GPIO25_SPI_OE_, 1)
    
    nV = ((rxd[1] << 8) | (rxd[2] << 0)) & 0x0fff
    
    if ch == 0:
        fV = nV / 4095.0 * 2.048 * 5 / 2
    elif ch == 1:
        fV = nV / 4095.0 * 2.048 * 2 / 2
    else:
        fV = 0.0
    
    if ch == 0:
        typ = "S"
    elif ch == 1:
        typ = "F"
    else:
        typ = " "
    
    show_term("MCP3204({0}): vol: {1:6.3f}".format(typ, fV))
    show_uart(pi, "MCP3204({0}): vol: {1:6.3f}".format(typ, fV))
    show_uart(pi, "\n")
    
    show_term("\n")
    
    return fV


def uart_write(pi, text):
    """
    デバッグ用
    """
    global g_huart0
    
    ret = pi.serial_write(g_huart0, bytearray(text.encode()))
    
    return ret

def main_init(pi):
    """
    GPIOピンを用いた入出力を準備するためのメソッド

    Args:
        pi(piogio.pi): pigpioライブラリのインスタンス. GPIOピンを制御するために使用

    Notes:
        piogio.setmode(gpio,mode)
            
            gpio: 指定したいGPIOピン番号を指定. RasPberryPi上のハードウェアのピン番号
            
            mode: 指定したいGPIOピンの動作モードを表す整数値.
            
                pigpio.INPUT (0): 入力モード。GPIOピンが外部からの信号を読み取るために使用
            
                pigpio.OUTPUT (1): 出力モード。GPIOピンが外部のデバイスや回路に信号を送るために使用
            
    各種実行内容(同様の内容は省略)
    
    pi.set_mode(GPIO18_LED, pigpio.OUTPUT): GPIOピン GPIO18_LED を出力モードに設定

    pi.set_mode(GPIO12_DSW1, pigpio.INPUT): GPIOピン GPIO12_DSW1 を入力モードに設定
    
        SW1_1の状態を読み取るための準備. 他3行も同様 
    
    pi.set_mode(GPIO04_I2CEN1_, pigpio.OUTPUT): GPIOピン GPIO04_I2CEN1_を出力モードに設定
    
        I2C通信のための入力の準備. 他4行も同様 

    pi.set_mode(GPIO25_SPI_OE_, pigpio.OUTPUT): GPIOピン GPIO25_SPI_OE_ を出力モードに設定
    
        SPI制御のための入力準備.
    """
    show_term("main_init()\n")
    
    
    global g_huart0
    
    # GPIO: Output
    pi.set_mode(GPIO18_LED, pigpio.OUTPUT)                    # 12  GPIO18_LED        LED_G
    
    # GPIO: Input
    pi.set_mode(GPIO12_DSW1, pigpio.INPUT)                    # 32  GPIO12_DSW1       SW1_1
    pi.set_mode(GPIO12_DSW2, pigpio.INPUT)                    # 36  GPIO16_DSW2       SW1_2
    pi.set_mode(GPIO12_DSW3, pigpio.INPUT)                    # 38  GPIO20_DSW3       SW1_3
    pi.set_mode(GPIO12_DSW4, pigpio.INPUT)                    # 40  GPIO21_DSW4       SW1_4
    
    # GPIO: Output
    pi.set_mode(GPIO04_I2CEN1_, pigpio.OUTPUT)                # 07  GPIO04_I2CEN1#    SCLE1, SDAE1 (SHT25)
    pi.set_mode(GPIO05_I2CEN2_, pigpio.OUTPUT)                # 29  GPIO05_I2CEN2#    SCLE2, SDAE2 (RL78/S1133, Int)
    pi.set_mode(GPIO06_I2CEN3_, pigpio.OUTPUT)                # 31  GPIO06_I2CEN3#    SCLE3, SDAE3 (RL78/S1133, Ext)
    pi.set_mode(GPIO13_I2CEN4_, pigpio.OUTPUT)                # 33  GPIO13_I2CEN4#    SHT85
    pi.set_mode(GPIO19_I2CEN5_, pigpio.OUTPUT)                # 35  GPIO19_I2CEN5#    I2C CN8
    
    # GPIO: Output
    pi.set_mode(GPIO25_SPI_OE_, pigpio.OUTPUT)                # 22  GPIO25_SPI_OE#    SPI Ext CN11

#   # UART
#   g_huart0 = pi.serial_open(UART0_DEV, UART0_BAUD)          # 08  TXD0              debug
#                                                             # 10  RXD0              debug
  
# show_term("g_huart0: {}\n".format(g_huart0))

# --------------------------------------
# グローバル変数としてpigpioを保持
pi = None
# --------------------------------------

def init_pigpio():
    """
    RasPberryPi上でGPIO制御のためにpigpioライブラリを初期化
    
    Attributes:
        pi (piogio.pi): pigpioライブラリのインスタンス. GPIOピンを制御するために使用
        
    Notes:
        接続をグローバル変数 pi に割り当て
    """
    global pi
    if pi is None:
        pi = pigpio.pi()
        if not pi.connected:
            raise Exception("pigpio connection failed...")
# --------------------------------------


# --------------------------------------
def get(sensor):
    """
    入力文字列に応じた各種センサデータメソッドを起動し出力結果を返却
    
    Args:
        sensor(str): センサ名

    Returns:
        各種センサから得られたデータ

    Notes:
        main.init(pi): GPIOピンを用いた入出力を準備
    
        pi.serial_data_available(g_huart0): 
            
            指定されたシリアルポート(g_huart0)で受信可能なデータのバイト数を整数で返す
            
            受信可能なデータがない場合は0を返す
    
        pi.serial_read_byte(g_huart0):
            
            指定されたシリアルポート(g_huart0)から1バイトのデータを読み込み整数として返す
            
            受信データがない場合は-1を返す
    
        入力文字列に応じて各種センサデータ取得メソッドを起動し, メソッド返却値を返却
    """
    global pi
    global g_huart0

    if pi is None:
        raise Exception("pigpio not initialized. Call init_pigpio first.")

    main_init(pi)

    if sensor == "dsw":
        dsw = dsw_read(pi)
        return dsw

    elif sensor == "i_v_light":
        luxInt = s1133_int()
        return luxInt

    elif sensor == "u_v_light":
        luxExt = s1133_ext()
        return luxExt
        
    elif sensor == "temperature":
        fT, _ = sht25_read(pi)
        return fT
        
    elif sensor == "humidity":
        _, fH = sht25_read(pi)
        return fH

    elif sensor == "temperature_hq":
        fT, _ = sht85_read(pi)
        return fT
        
    elif sensor == "humidity_hq":
        _, fH = sht85_read(pi)
        return fH
        
    elif sensor == "stem":
        fV = mcp3204_read(pi, 0)
        return fV
        
    elif sensor == "fruit_diagram":
        fV = mcp3204_read(pi, 1)
        return fV
        
    else:
        print(f"Unknown sensor type: {sensor}")
    
