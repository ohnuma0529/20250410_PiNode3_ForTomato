from sensor import Sensor
from camera import Camera
from wilt import cal_wilt

if __name__ == "__main__":
    Sensor().upload_csv()
    Camera().save_images()
    try:
        cal_wilt()
    except Exception as e:
        print(f"Wilt Error: {e}")