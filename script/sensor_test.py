import time
import read_sensor

sensors = [
    "dsw",
    "i_v_light",
    "u_v_light",
    "temperature",
    "humidity",
    "temperature_hq",
    "humidity_hq",
    "stem",
    "fruit_diagram"
]

# pigpioの初期化を一回に
read_sensor.init_pigpio()

try:
    while True:
        print("===============================")
        for sensor in sensors:
            data = read_sensor.get(sensor)
            print(f"{sensor}: {data}")
        print("===============================\n")
        time.sleep(1)
except KeyboardInterrupt:
    print("Program stopped by user.")