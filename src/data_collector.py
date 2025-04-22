from sensor import Sensor
from camera import Camera
from wilt import cal_wilt

if __name__ == "__main__":
    Sensor().upload_csv()
    Camera().save_images()