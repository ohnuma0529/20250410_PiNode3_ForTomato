import json
from pathlib import Path
import os
import pandas as pd

def get_pinode_config(config_path="/home/pinode3/config.json"):
    """
    Pinodeの基本情報を取得
    
    Returns:
        pinode_config(json_object): config.jsonに含まれるPinode基礎情報
    
    Notes:
        [config.json](https://github.com/MinenoLab/PiNode3/blob/e3983b7810d5797727f4daf57e4e7f7a659df84a/config.json)

    """
    if Path(config_path).is_file():
        with open(config_path) as f:
            pinode_config = json.load(f)
        return pinode_config
    else:
        raise FileNotFoundError("Config file not found")

def read_csv(file_path):
    if os.path.exists(file_path) and file_path.endswith(".csv"):
        try:
            df = pd.read_csv(file_path, index_col=0)
            # datetime型に変換
            df.incex = pd.to_datetime(df.index)
            return df
        except Exception as e:
            print(e)
            return pd.DataFrame()
    else:
        return pd.DataFrame()

def save_csv(df, file_path):
    if not file_path.endswith(".csv"):
        file_path += ".csv"
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    try:
        df.to_csv(file_path)
    except Exception as e:
        print(e)