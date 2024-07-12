################################################################################
# このコードはPinode3テスト用プログラムCheckExt.pyをベースにセンサ名で値を返すコードです
# 
################################################################################

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


# --------------------------------------
# デバッグ用
def signal_handler(signal, frame):
# --------------------------------------
  global quit
  
  quit = True
  show_term("\n")
# --------------------------------------


# --------------------------------------
# デバッグ用
def show_term(text):
# --------------------------------------
  if SHOW_TERM:
    print(text, end="")
  
  return
# --------------------------------------


# --------------------------------------
# デバッグ用
def show_uart(pi, text):
# --------------------------------------
  if SHOW_UART:
#   print(text, end="")
    uart_write(pi, text)
  
  return
# --------------------------------------


# --------------------------------------
# LED点灯用関数。未使用
def led_show(pi, on):
# --------------------------------------
  pi.write(GPIO18_LED, on)
  
  if on == 1:
    state = "On"
  else:
    state = "Off"
  
  show_term("LED:        {0}\n".format(state))
  show_uart(pi, "LED:        {0}\n".format(state))
  
  return on
# --------------------------------------


# --------------------------------------
# Pinode3識別用。トグルスイッチで個体を15台まで識別可能
def dsw_read(pi):
# --------------------------------------
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
# --------------------------------------


# --------------------------------------
def sht25_read(pi):
# --------------------------------------
  addr = ADDR_I2C1                                          # 0x40  SHT25
# show_term("Addr: 0x{0:02x}, ".format(addr))
  
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
  
# show_term("Ret: {0}, ".format(rxrT))
# if rxrT == 3:
#   show_term("DataT: 0x{0:02x}, 0x{1:02x}, 0x{2:02x}, ".format(rxdT[0], rxdT[1], rxdT[2]))
  
  if rxrT > 0:
    nT = (rxdT[0] << 8) | (rxdT[1] & 0xFC)
    nH = (rxdH[0] << 8) | (rxdH[1] & 0xFC)
  else:
    nT = 0
    nH = 0
  
# show_term("Ret: {0}, ".format(rxrH))
# if rxrH == 3:
#   show_term("DataH: 0x{0:02x}, 0x{1:02x}, 0x{2:02x}, ".format(rxdH[0], rxdH[1], rxdH[2]))
  
  fT = -46.85 + 175.72 * (nT / 65536)
  fH =  -6.00 + 125.00 * (nH / 65536)
  
# show_term("\n")
  show_term("SHT25:      tmp: {0:6.3f}, hum: {1:6.3f}".format(fT, fH))
  show_uart(pi, "SHT25:      tmp: {0:6.3f}, hum: {1:6.3f}".format(fT, fH))
  show_uart(pi, "\n")
  
  show_term("\n")
  
  return fT, fH
# --------------------------------------


# --------------------------------------
def s1133_int():
# --------------------------------------
  addr = ADDR_I2C2                                          # 0x30  RL78/S1133, Int
# show_term("Addr: 0x{0:02x}, ".format(addr))
  
  pi.write(GPIO05_I2CEN2_, 0)
  
  handle = pi.i2c_open(1, addr, 0)
  
  rxr, rxd = pi.i2c_read_device(handle, 3)
  
  pi.i2c_close(handle)
  
  pi.write(GPIO05_I2CEN2_, 1)
  
# show_term("Ret: {0}, ".format(rxr))
# if rxr == 3:
#   show_term("Data: 0x{0:02x}, 0x{1:02x}, 0x{2:02x}, ".format(rxd[0], rxd[1], rxd[2]))
  
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
  
# show_term("\n")
  show_term("S1133in:    lux: {0:6d}, rng: {1}, dsw: {2}, lvd: {3}, ".format(lux, rng, dsw, lvd))
  show_uart(pi, "S1133in:    lux: {0:6d}, rng: {1}, dsw: {2}, lvd: {3}, ".format(lux, rng, dsw, lvd))
  show_uart(pi, "\n")
  
  show_term("\n")
  
  return lux
#   return {"lux": lux, "rng": rng, "dsw": dsw, "lvd": lvd}
# --------------------------------------


# --------------------------------------
def s1133_ext():
# --------------------------------------
  addr = ADDR_I2C3                                          # 0x31  RL78/S1133, Ext
# show_term("Addr: 0x{0:02x}, ".format(addr))
  
  pi.write(GPIO06_I2CEN3_, 0)
  
  handle = pi.i2c_open(1, addr, 0)
  
  rxr, rxd = pi.i2c_read_device(handle, 3)
  
  pi.i2c_close(handle)
  
  pi.write(GPIO06_I2CEN3_, 1)
  
# show_term("Ret: {0}, ".format(rxr))
# if rxr == 3:
#   show_term("Data: 0x{0:02x}, 0x{1:02x}, 0x{2:02x}, ".format(rxd[0], rxd[1], rxd[2]))
  
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
  
# show_term("\n")
  show_term("S1133ex:    lux: {0:6d}, rng: {1}, dsw: {2}, lvd: {3}, ".format(lux, rng, dsw, lvd))
  show_uart(pi, "S1133ex:    lux: {0:6d}, rng: {1}, dsw: {2}, lvd: {3}, ".format(lux, rng, dsw, lvd))
  show_uart(pi, "\n")
  
  show_term("\n")
  
  return lux
#   return {"lux": lux, "rng": rng, "dsw": dsw, "lvd": lvd}
# --------------------------------------


# --------------------------------------
# 強制通風筒
def sht85_read(pi):
# --------------------------------------
  addr = ADDR_I2C4                                          # 0x44  SHT85
# show_term("Addr: 0x{0:02x}, ".format(addr))
  
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
  
# show_term("Ret: {0}, ".format(rxr))
# if rxr == 6:
#   show_term("Data: 0x{0:02x}, 0x{1:02x}, 0x{2:02x}, ".format(rxd[0], rxd[1], rxd[2]))
#   show_term("Data: 0x{0:02x}, 0x{1:02x}, 0x{2:02x}, ".format(rxd[3], rxd[4], rxd[5]))
  
  if rxr > 0:
    nT = (rxd[0] << 8) | (rxd[1] << 0)
    nH = (rxd[3] << 8) | (rxd[4] << 0)
  else:
    nT = 0
    nH = 0
  
  fT = -45.00 + 175.00 * (nT / 65535)
  fH =   0.00 + 100.00 * (nH / 65535)
  
# show_term("\n")
  show_term("SHT85:      tmp: {0:6.3f}, hum: {1:6.3f}".format(fT, fH))
  show_uart(pi, "SHT85:      tmp: {0:6.3f}, hum: {1:6.3f}".format(fT, fH))
  show_uart(pi, "\n")
  
  show_term("\n")
  
  return fT, fH
# --------------------------------------


# --------------------------------------
def mcp3204_read(pi, ch):
# --------------------------------------
# show_term("Channel: {0}, ".format(ch))
  
  pi.write(GPIO25_SPI_OE_, 1)
  
  h = pi.spi_open(SPI0_BUS, SPI0_CLK_HZ, SPI0_MODE)         # 24  CE0#              ADC MCP3204
  
  ch = ch & 0x07
  txd = (0x06 | (ch > 2), 0x00 | (ch << 6), 0x00)
  
  rxr, rxd = pi.spi_xfer(h, txd)
  
  pi.spi_close(h)
  
  pi.write(GPIO25_SPI_OE_, 0)
  
# if rxr == 3:
#   show_term("Data: 0x{0:02x}, 0x{1:02x}, 0x{2:02x}, ".format(rxd[0], rxd[1], rxd[2]))
  
  nV = ((rxd[1] << 8) | (rxd[2] << 0)) & 0x0fff
  
  if ch == 0:
    fV = nV / 4095.0 * 2.048 * 5 / 2
  elif ch == 1:
    fV = nV / 4095.0 * 2.048 * 2 / 2
  else:
    fV = 0.0
  
# show_term("\n")
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
# --------------------------------------


# --------------------------------------
def mcp3204ex_read(pi, ch):
# --------------------------------------
# show_term("Channel: {0}, ".format(ch))
  
  pi.write(GPIO25_SPI_OE_, 0)
  
  h = pi.spi_open(SPI1_BUS, SPI1_CLK_HZ, SPI1_MODE)         # 24  CE0#              ADC MCP3204
  
  ch = ch & 0x07
  txd = (0x06 | (ch > 2), 0x00 | (ch << 6), 0x00)
  
  rxr, rxd = pi.spi_xfer(h, txd)
  
  pi.spi_close(h)
  
  pi.write(GPIO25_SPI_OE_, 1)
  
# if rxr == 3:
#   show_term("Data: 0x{0:02x}, 0x{1:02x}, 0x{2:02x}, ".format(rxd[0], rxd[1], rxd[2]))
  
  nV = ((rxd[1] << 8) | (rxd[2] << 0)) & 0x0fff
  
  if ch == 0:
    fV = nV / 4095.0 * 2.048 * 5 / 2
  elif ch == 1:
    fV = nV / 4095.0 * 2.048 * 2 / 2
  else:
    fV = 0.0
  
# show_term("\n")
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
# --------------------------------------


# --------------------------------------
def uart_write(pi, text):
# --------------------------------------
  global g_huart0
  
  ret = pi.serial_write(g_huart0, bytearray(text.encode()))
  
  return ret
# --------------------------------------


# --------------------------------------
def main_init(pi):
# --------------------------------------
  show_term("main_init()\n")
  
  # global constants and variables
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

pi = None
# --------------------------------------
# 追記：グローバル変数としてpigpioを保持
def init_pigpio():
# --------------------------------------
    global pi
    if pi is None:
        pi = pigpio.pi()
        if not pi.connected:
            raise Exception("pigpio connection failed...")
# --------------------------------------


# --------------------------------------
# 追記
def get(sensor):
# --------------------------------------
    global pi
    global g_huart0

    if pi is None:
        raise Exception("pigpio not initialized. Call init_pigpio first.")

    main_init(pi)

    ret = pi.serial_data_available(g_huart0)
    if ret > 0:
      rxd = pi.serial_read_byte(g_huart0)
      if rxd == 0x03:
        show_term("^C\n")
        # とりあえずエラー文出す
        raise Exception("Serial read terminated: Received 0x03 indicating a termination signal.")

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
    

# --------------------------------------

# 以下未使用
# # --------------------------------------
# def main_term(pi):
# # --------------------------------------
#   show_term("main_term()\n")
  
#   # global constants and variables
#   global g_huart0
  
#   # UART
#   pi.serial_close(g_huart0)
# # --------------------------------------


# # --------------------------------------
# def main(pi):
# # --------------------------------------
#   show_term("main()\n")
  
#   global quit
#   global g_huart0
  
#   signal.signal(signal.SIGINT, signal_handler)
  
#   main_init(pi)
  
# #   show_term("\n")
# #   show_uart(pi, "checkext.py has started.\n")
# #   show_uart(pi, "\n")
  
# #   count = 0
  
#   while True:
#     if quit:
#       break
    
#     ret = pi.serial_data_available(g_huart0)
#     if ret > 0:
#       rxd = pi.serial_read_byte(g_huart0)
#       if rxd == 0x03:
#         show_term("^C\n")
#         break
    
#     show_term("Count:      {}\n".format(count))
#     show_uart(pi, "Count:      {}\n".format(count))
    
#     led_on = count % 2
#     led_show(pi, led_on)
    
#     dsw_read(pi)
    
#     luxInt = s1133_int()
#     luxExt = s1133_ext()
    
#     fT, fH = sht25_read(pi)
    
#     fT, fH = sht85_read(pi)
    
#   # fT, fH = sht85ex_read(pi)
    
#     fV = mcp3204_read(pi, 0)
#     fV = mcp3204_read(pi, 1)
    
#   # fV = mcp3204ex_read(pi, 0)
#   # fV = mcp3204ex_read(pi, 1)

# # 過去デバッグ用。センサ取得回数カウント
# #     show_term("\n")
# #     show_uart(pi, "\n")
# #     count = count + 1
# #     time.sleep(1.7)
# #   show_uart(pi, "checkext.py has stopped.\n")
# #   show_uart(pi, "\n")
# #   main_term(pi)
# # --------------------------------------


# # --------------------------------------
# if __name__ == "__main__":
# # --------------------------------------
#   global quit
  
#   show_term("__main__\n")
  
#   quit = False
  
#   pi = pigpio.pi()
#   if not pi.connected:
#     raise Exception("pigpio connection faild...")
  
#   try:
#     main(pi)
#   finally:
#     pi.stop()
  
#   exit(0)
# # --------------------------------------