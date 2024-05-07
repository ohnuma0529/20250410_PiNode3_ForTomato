from pathlib import Path
import util
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

class InfluxDB:
    def __init__(self):
        pinode_config   = util.get_pinode_config()
        self.org        = pinode_config["influxdb"]["organization"]
        self.bucket     = pinode_config["influxdb"]["bucket"]
        self.device_id  = pinode_config["device_id"]
        self.url        = f"http://localhost:{pinode_config['influxdb']['port']}"

        with open(Path(__file__).parent / "token.txt") as f:
            self.token = f.read().strip()
    
    def upload_dataframe(self, data):
        write_client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        write_api = write_client.write_api(write_options=SYNCHRONOUS)
        write_api.write(
            self.bucket,
            self.org,
            record=data,
            data_frame_measurement_name=self.device_id
        )