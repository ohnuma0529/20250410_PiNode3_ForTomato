import json
from pathlib import Path


def get_pinode_config(config_path="/home/pinode3/config.json"):
    if Path(config_path).is_file():
        with open(config_path) as f:
            pinode_config = json.load(f)
        return pinode_config
    else:
        raise FileNotFoundError("Config file not found")