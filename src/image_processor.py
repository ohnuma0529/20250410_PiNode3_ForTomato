import cv2
import numpy as np
from datetime import datetime, timedelta
import os
import pandas as pd
import sys
import torch
import time

from ultralytics import YOLO

try:
    sys.path.append("/usr/local/bin/pinode3/Depth-Anything-V2")
    from depth_anything_v2.dpt import DepthAnythingV2
except ImportError:
    sys.path.append("/home/pi/20250410_PiNode3_ForTomato/Depth-Anything-V2")
    from depth_anything_v2.dpt import DepthAnythingV2

import util

def get_depth_map(image):
    encoder = "vits"  # モデルの種類を指定
    model_configs = {
        'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
        'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
        'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]},
        'vitg': {'encoder': 'vitg', 'features': 384, 'out_channels': [1536, 1536, 1536, 1536]}
    }
    depth_model = DepthAnythingV2(**model_configs[encoder])
    try:
        depth_model.load_state_dict(torch.load(f"/usr/local/bin/pinode3/Depth-Anything-V2/depth_anything_v2_{encoder}.pth", map_location="cpu"))
    except FileNotFoundError:
        depth_model.load_state_dict(torch.load(f"/home/pi/20250410_PiNode3_ForTomato/Depth-Anything-V2/depth_anything_v2_{encoder}.pth", map_location="cpu"))
    #以下2行はGPUテスト用
    # depth_model.eval()
    # depth_model = depth_model.to('cuda')

    depth_image = depth_model.infer_image(image)
    depth = (depth_image - depth_image.min()) / (depth_image.max() - depth_image.min()) * 255  # 0-255にスケーリング
    depth = depth.astype(np.uint8)
    return depth

#bboxリストと深度推定画像より、bbox毎の平均深度を計算する関数
#depth0-255で深度を表現する二次元配列
# bboxリストと深度推定画像より、bbox毎の平均深度を計算し、深度でソートする関数
def calc_depth(bbox_list, depth):
    depth_info = []

    for bbox in bbox_list:
        x1, y1, x2, y2 = map(int, bbox)
        # 各bbox領域の平均深度を計算し、bbox座標と深度のペアを追加
        avg_depth = np.mean(depth[y1:y2, x1:x2])
        depth_info.append((bbox, avg_depth))

    # 深度でソートして返す
    depth_info.sort(key=lambda x: x[1], reverse=True)

    # bboxリストと深度リストをそれぞれ分離して返す
    sorted_bbox_list = [item[0] for item in depth_info]
    sorted_depth_list = [item[1] for item in depth_info]

    return [sorted_bbox_list, sorted_depth_list]

# bboxの縁が画像の縁に近い場合、bboxを削除する関数
#bbox_listはbbox_list[0]にbboxの座標、bbox_list[1]に深度が格納されている
#bbox削除時は深度も一緒に削除する
def remove_edge_bbox(bbox_list, height, width, rate=0.95):
    center_x = width // 2
    center_y = height // 2
    # 矩形のサイズを計算
    rect_width = int(width * rate)
    rect_height = int(height * (rate - 0.1))

    #左上
    start_x = center_x - rect_width // 2
    start_y = center_y - rect_height // 2
    #右下
    end_x = center_x + rect_width // 2
    # end_y = center_y
    end_y = center_y + rect_height // 2
    
    #bboxの線が縁に含まれていたらbbox_listから削除
    new_bbox_list = []
    new_depth_list = []
    for i, bbox in enumerate(bbox_list[0]):
        x1, y1, x2, y2 = bbox
        if x1 > start_x and y1 > start_y and x2 < end_x and y2 < end_y:
            #座標と深度をnew_bbox_listに追加
            # new_bbox_list.append(bbox_list[:, i])    
            new_bbox_list.append(bbox)
            new_depth_list.append(bbox_list[1][i])
        
    # return new_bbox_list
    return [new_bbox_list, new_depth_list]

def get_first_bbox(bbox_list, depth, height=1024, width=1024, leaf_num=5):
    con_list = calc_depth(bbox_list, depth)
    con_list = remove_edge_bbox(con_list, height, width)
    #con_list[0]のbbox座標から、bboxの面積を計算し、画像サイズの半分以上だったら削除
    new_bbox_list = []
    new_depth_list = []
    for i, bbox in enumerate(con_list[0]):
        x1, y1, x2, y2 = bbox
        area = (x2 - x1) * (y2 - y1)
        if area <= (height * width) / 2:
            new_bbox_list.append(bbox)
            new_depth_list.append(con_list[1][i])
            if len(new_bbox_list) == leaf_num:
                break
    new_list = [new_bbox_list, new_depth_list]
    return new_list

#bboxどうしのIoUを計算する関数
def calc_iou(bbox1, bbox2):
    #BBox1とbbox2をfloat型に変換
    bbox1 = list(map(float, bbox1))
    bbox2 = list(map(float, bbox2))
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - intersection
    iou = intersection / union
    return iou

def get_frame(frame, bbox):
    x1, y1, x2, y2 = bbox
    # print("input:", x1, y1, x2, y2)
    #bboxの大きさを1.3倍に拡大
    x1 = int(x1 - (x2 - x1) * 0.15)
    x2 = int(x2 + (x2 - x1) * 0.15)
    y1 = int(y1 - (y2 - y1) * 0.15)
    y2 = int(y2 + (y2 - y1) * 0.15)
    if x1 < 0:
        x1 = 0
    elif x2 > frame.shape[1]:
        x2 = frame.shape[1]
    if y1 < 0:
        y1 = 0
    elif y2 > frame.shape[0]:
        y2 = frame.shape[0]
    # print("output:", x1,y1,x2,y2)
    return frame[y1:y2, x1:x2], x1, y1, x2, y2

class image_processor:
    def __init__(self, df, image_dir, now_time):
        setting = util.get_pinode_config()
        self.edge_id = setting["device_id"]
        self.df = df
        self.image_dir = image_dir
        self.tracking_num = setting["wilt"]["tracking_num"]
        self.now_time = now_time
        self.server_flag = setting["wilt"]["server_flag"]
        self.camera_usb = setting["wilt"]["camera_usb"]
        self.camera_type = setting["wilt"]["camera_type"]

        if self.server_flag:
            self.detect = YOLO("weights/detect/20241106_detect.pt")
            self.pose = YOLO("weights/pose/20241217_3200aug.pt")
        else:
            try:
                self.detect = YOLO("weights/detect/20241106_detect_saved_model/20241106_detect_float32.tflite")
                self.pose = YOLO("weights/pose/20241217_3200aug.pt")
            except Exception as e:
                # print("Error loading model:", e)
                self.detect = YOLO("/home/pi/20250410_PiNode3_ForTomato/weights/detect/20241106_detect_saved_model/20241106_detect_float32.tflite")
                self.pose = YOLO("/home/pi/20250410_PiNode3_ForTomato/weights/pose/20241217_3200aug.pt")
        
        self.detect_size = 1024
        self.pose_size = 640
        self.key_list = []
    
    def get(self):
        return self.df

    #初回画像，再検出時の処理
    #深度推定，葉のBBox検出，BBoxの平均深度計算，追跡数までを追跡対象としてbbox情報をdfに保存
    #処理後にre_detectionを0にして返す
    # todo
    # 1. 再検出時に生き残っている葉を引き継ぐ機能
    #   ➡葉削除時に，列を消すのではなく，更新しないだけに留める
    # 2. 現在トラッキング中の葉の
    def first_detection(self):
        # image_dirの中で最も新しい画像を取得．
        # 01_20250208_0701.jpgの形式．0701部分が時分を表す
        images = os.listdir(self.image_dir)

        if not images:
            print("画像フォルダが存在しません")
            return self.df

        #now_timeの画像を取得
        for i in range(3):
            check_time = self.now_time - timedelta(minutes=i)
            file_name = f"{self.edge_id}_{self.camera_usb}_{self.camera_type}_{check_time.strftime('%Y%m%d-%H%M')}.jpg"
            print("file_name:", file_name)
            if file_name in images:
                break  # 見つかったらループ終了
        else:
            print("エラー: 対応する画像ファイルが3回試行しても見つかりません")
            return self.df
        image = cv2.imread(os.path.join(self.image_dir, file_name))
        image = cv2.resize(image, (self.detect_size, self.detect_size))
        # 深度推定
        depth = get_depth_map(image)

        # 葉のBBox検出
        results = self.detect.predict(image, imgsz=self.detect_size, conf=0.3, save=False, project="/tmp")

        result = results[0]
        bbox_list = [box.xyxy[0].tolist() for box in result.boxes]
        tracking_list = get_first_bbox(bbox_list, depth, self.detect_size, self.detect_size, leaf_num=self.tracking_num)

        # dfに保存
        leaf_num = 0
        if "all_leaf_num" in self.df.columns:
            try:
                leaf_num = self.df["all_leaf_num"].dropna().iloc[-1]
            except:
                pass
        key_list = []
        for i in range(len(tracking_list[0])):
            leaf_id = int(leaf_num + i + 1)
            x1, y1, x2, y2 = tracking_list[0][i]
        
            self.df.loc[self.now_time, [f'{leaf_id}_bbox_x1', f'{leaf_id}_bbox_y1', 
                                        f'{leaf_id}_bbox_x2', f'{leaf_id}_bbox_y2', 
                                        f'{leaf_id}_bbox_center_x1', f'{leaf_id}_bbox_center_y1']] = [
                x1, y1, x2, y2, (x1 + x2) / 2, (y1 + y2) / 2
            ]
            key_list.append(leaf_id)
        self.key_list = key_list
        self.df.loc[self.now_time, ['re_detection', 'all_leaf_num', 'now_leaf_num']] = [
            0, leaf_num + leaf_num+len(tracking_list[0]), len(tracking_list[0])
]


        # pose推定
        for i in self.key_list:
            x1 = self.df[str(i) + "_bbox_x1"].dropna().iloc[-1]
            y1 = self.df[str(i) + "_bbox_y1"].dropna().iloc[-1]
            x2 = self.df[str(i) + "_bbox_x2"].dropna().iloc[-1]
            y2 = self.df[str(i) + "_bbox_y2"].dropna().iloc[-1]
            # bboxから画像を切り出して640x640にリサイズ
            clip, new_x1, new_y1, new_x2, new_y2 = get_frame(image, [x1, y1, x2, y2])
            clip = cv2.resize(clip, (self.pose_size, self.pose_size))
            # POSE推定
            pose_results = self.pose.predict(clip, imgsz=640, conf=0.1, save=False, project="/tmp")
            xys = pose_results[0].keypoints.xy[0].tolist()
            base_x, base_y = xys[0][0], xys[0][1]
            tip_x, tip_y = xys[1][0], xys[1][1]
            base_x = base_x /self.pose_size * (new_x2 - new_x1) + new_x1
            base_y = base_y /self.pose_size * (new_y2 - new_y1) + new_y1
            tip_x = tip_x /self.pose_size * (new_x2 - new_x1) + new_x1
            tip_y = tip_y /self.pose_size * (new_y2 - new_y1) + new_y1
            # dfに保存
            self.df.loc[self.now_time, [f'{i}_base_x', f'{i}_base_y', f'{i}_tip_x', f'{i}_tip_y', f'{i}_angle', f'{i}_length']] = [
                base_x, base_y, tip_x, tip_y,
                np.arctan2(tip_y - base_y, tip_x - base_x),
                np.sqrt((tip_x - base_x) ** 2 + (tip_y - base_y) ** 2)
            ]
        print(self.df)
            # 萎れ指標を計算
        self.cal_wilt()
        self.cal_final_wilt()
        # print(self.df)
        
        return self.df

    def get_best_bbox(self, bbox_list):
        for i in self.key_list:
            bbox = [self.df[str(i) + "_bbox_x1"].dropna().iloc[-1], self.df[str(i) + "_bbox_y1"].dropna().iloc[-1], self.df[str(i) + "_bbox_x2"].dropna().iloc[-1], self.df[str(i) + "_bbox_y2"].dropna().iloc[-1]]
            #floatに変換
            bbox = list(map(float, bbox))
            best_iou = 0
            for bbox2 in bbox_list:
                iou = calc_iou(bbox, bbox2)
                if iou > best_iou:
                    best_iou = iou
                    best_bbox = bbox2
            if best_iou < 0.25:
                best_bbox = bbox
            # dfを更新
            self.df.loc[self.now_time, [f'{i}_bbox_x1', f'{i}_bbox_y1', f'{i}_bbox_x2', f'{i}_bbox_y2', f'{i}_center_x', f'{i}_center_y']] = [
                best_bbox[0], best_bbox[1], best_bbox[2], best_bbox[3],
                (best_bbox[0] + best_bbox[2]) / 2,
                (best_bbox[1] + best_bbox[3]) / 2
            ]

        return self.df

    # 更新されていないbboxがある場合、そのbboxを削除する関数
    def check_bbox(self):
        if len(self.df[str(self.key_list[0]) + '_bbox_x1'].dropna()) < 10:
            return self.df, self.key_list
        for i in self.key_list:
            if len(self.df[str(i) + '_bbox_x1'].dropna()) < 10:
                continue
            # 時点前のbbox
            bbox10 = [self.df[str(i) + "_bbox_x1"].dropna().iloc[-10], self.df[str(i) + "_bbox_y1"].dropna().iloc[-10], self.df[str(i) + "_bbox_x2"].dropna().iloc[-10], self.df[str(i) + "_bbox_y2"].dropna().iloc[-10]]
            bbox5 = [self.df[str(i) + "_bbox_x1"].dropna().iloc[-5], self.df[str(i) + "_bbox_y1"].dropna().iloc[-5], self.df[str(i) + "_bbox_x2"].dropna().iloc[-5], self.df[str(i) + "_bbox_y2"].dropna().iloc[-5]]
            bbox3 = [self.df[str(i) + "_bbox_x1"].dropna().iloc[-3], self.df[str(i) + "_bbox_y1"].dropna().iloc[-3], self.df[str(i) + "_bbox_x2"].dropna().iloc[-3], self.df[str(i) + "_bbox_y2"].dropna().iloc[-3]]
            bbox = [self.df[str(i) + "_bbox_x1"].dropna().iloc[-1], self.df[str(i) + "_bbox_y1"].dropna().iloc[-1], self.df[str(i) + "_bbox_x2"].dropna().iloc[-1], self.df[str(i) + "_bbox_y2"].dropna().iloc[-1]]
            # 4時点のbboxの座標が同じなら削除
            if bbox == bbox3 == bbox5 == bbox10:
                # remove_list = [col for col in self.df.columns if col.startswith(str(i) + "_")]
                # self.df.drop(columns=remove_list, inplace=True)
                # key_listから排除
                self.key_list.remove(i)
        return self.df, self.key_list
    
    # IOUが0.8以上のbboxがある場合、数字の小さいほうのbboxを削除する関数
    def check_bbox2(self):
        for i in self.key_list:
            bbox = [self.df[str(i) + "_bbox_x1"].dropna().iloc[-1], self.df[str(i) + "_bbox_y1"].dropna().iloc[-1], self.df[str(i) + "_bbox_x2"].dropna().iloc[-1], self.df[str(i) + "_bbox_y2"].dropna().iloc[-1]]
            for j in self.key_list:
                if i == j:
                    continue
                bbox2 = [self.df[str(j) + "_bbox_x1"].dropna().iloc[-1], self.df[str(j) + "_bbox_y1"].dropna().iloc[-1], self.df[str(j) + "_bbox_x2"].dropna().iloc[-1], self.df[str(j) + "_bbox_y2"].dropna().iloc[-1]]
                iou = calc_iou(bbox, bbox2)
                if iou > 0.8:
                    if i > j:
                        # remove_list = [col for col in self.df.columns if col.startswith(str(i) + "_")]
                        # self.df.drop(columns=remove_list, inplace=True)
                        self.key_list.remove(i)
                    else:
                        # remove_list = [col for col in self.df.columns if col.startswith(str(j) + "_")]
                        # self.df.drop(columns=remove_list, inplace=True)
                        self.key_list.remove(j)
        return self.df, self.key_list

    #10分前の角度と現在の角度の差を計算
    # 全葉の角度変化の中央値の倍を閾値として、その値を超える葉を削除する関数
    # 角度はラジアン
    def check_bbox3(self):
        angle_diff_list = []
        for i in self.key_list:
            if len(self.df[str(i) + '_angle'].dropna()) < 35:
                return self.df, self.key_list
            # angle_diffの絶対値を計算してリストに追加
            angle_diff = abs(self.df[str(i) + "_angle"].dropna().iloc[-2] - self.df[str(i) + "_angle"].dropna().iloc[-30])
            angle_diff_list.append(angle_diff)
        # 絶対値の差の中央値に基づく閾値を設定
        if len(self.df[str(self.key_list[0]) + '_angle'].dropna()) > 30:
            threshold = 0.5
        else:
            threshold = np.median(angle_diff_list) * 20
        # print("threshold:", threshold)
        # print("angle_diff_list:", angle_diff_list)

        for i, angle_diff in zip(self.key_list, angle_diff_list):
            if angle_diff > threshold:  # 既に絶対値をとっているので条件はそのまま
                # remove_list = [col for col in self.df.columns if col.startswith(str(i) + "_")]
                # self.df.drop(columns=remove_list, inplace=True)
                self.key_list.remove(i)
        return self.df, self.key_list

    def cal_wilt(self):
                # b'' を NaN に変換し、その後 NaN のある行を削除
        self.df.replace({b'': np.nan}, inplace=True)
        # self.df.dropna(inplace=True)

        for key in self.key_list:
            if not str(key) + "_bbox_x1" in self.df.columns:
                print(key)
                continue
            if len(self.df[str(key) + "_angle"]) < 35:
                self.df[str(key) + "_wilt"] = 0
                continue
            # 現時点(self.now_time) - 30分のタイムスタンプを作成
            if len(self.df) > 30:
                lookback_index = self.df.index[-30]
            else:
                lookback_index = self.df.index[0]  # データが30行未満なら最初の行を使用
                
            leaf_length = self.df.loc[:, str(key) + '_length'].mean()
            # 30時点前が無ければcontinue
            try:
                if np.isnan(self.df[str(key) + "_angle"].dropna().loc[lookback_index]):
                    self.df[str(key) + "_wilt"] = 0
                    continue
                if np.pi / 2 <= self.df[str(key) + "_angle"].loc[lookback_index] <= 3 * np.pi / 2:
                    self.df[str(key) + "_angle_diff"] = self.df[str(key) + "_angle"].dropna().loc[lookback_index] - self.df[str(key) + "_angle"]
                else:
                    self.df[str(key) + "_angle_diff"] = self.df[str(key) + "_angle"] - self.df[str(key) + "_angle"].dropna().loc[lookback_index]
                
                self.df[str(key) + "_sin"] = np.sin(self.df[str(key) + "_angle_diff"]) * -1
                self.df[str(key) + "_center_diff"] = (self.detect_size - self.df[str(key) + "_center_y"]) - (self.detect_size - self.df[str(key) + "_center_y"].dropna().loc[lookback_index])
                self.df[str(key) + "_std_center_diff"] = self.df[str(key) + "_center_diff"] / leaf_length
                self.df[str(key) + "_wilt"] = self.df[str(key) + "_sin"] + self.df[str(key) + "_std_center_diff"]
                self.df[str(key) + "_wilt"] = self.df[str(key) + "_wilt"].rolling(5).mean().interpolate()
            except:
                self.df[str(key) + "_wilt"] = 0
                continue       
        return self.df
    
    def cal_final_wilt(self):
        if len(self.df) < 35:
            self.df["final_wilt"] = 0
            return self.df
        max_lifetime = 0
        max_key = 1
        for key in self.key_list:
            if not str(key) + "_wilt" in self.df.columns:
                continue
            count = len(self.df[str(key) + "_wilt"].dropna()[self.df[str(key) + "_wilt"].dropna() != 0])
            if count > max_lifetime:
                max_lifetime = count
                max_key = key
        self.df["final_wilt"] = self.df[str(max_key) + "_wilt"]
        # self.df["max_key"] = max_key
        self.df.loc[self.now_time, "max_key"] = max_key
        return self.df
    
    def get_key_list(self):
        latest_row = self.df.iloc[-1]
        bbox_ids = [int(col.split("_")[0]) for col in self.df.columns 
                    if "_bbox_x1" in col and not pd.isna(latest_row[col])]

        return bbox_ids

    # 前回のbbox情報があることが前提
    # 1. bboxの検出
    # 2. IoUを計算して，追跡
    # 　　➡前の行のBBoxがある列のみ処理
    # 3. bboxから画像を切り出して640x640にリサイズ
    # 4. POSE推定，元画像の座標に変換
    # 5. 各情報をdfに保存
    # 　　➡保存前に安定性を評価し，安定していない葉は更新しない

    def tracking(self):
        # 葉のBBox検出
        images = os.listdir(self.image_dir)

        if not images:
            print("画像フォルダが存在しません")
            return self.df

        #now_timeの画像を取得
        for i in range(3):
            check_time = self.now_time - timedelta(minutes=i)
            file_name = f"{self.edge_id}_{self.camera_usb}_{self.camera_type}_{check_time.strftime('%Y%m%d-%H%M')}.jpg"
            print("file_name:", file_name)
            if file_name in images:
                break  # 見つかったらループ終了
        else:
            print("エラー: 対応する画像ファイルが3回試行しても見つかりません")
            return self.df
        image = cv2.imread(os.path.join(self.image_dir, file_name))
        image = cv2.resize(image, (self.detect_size, self.detect_size))
        self.key_list = [int(i.split("_")[0]) for i in self.df.columns if "_bbox_x1" in i]
        print("key_list:", self.key_list)
        try:
            results = self.detect.predict(image, imgsz=self.detect_size, conf=0.3, save=False, project="/tmp")
            result = results[0]
            bbox_list = [box.xyxy[0].tolist() for box in result.boxes]

            # ３種類の削除関数を実行し，key_listを更新
            self.check_bbox()
            self.check_bbox2()
            self.check_bbox3()

            # IoUが高いBBoxを用いて更新
            # bbox情報を更新
            self.df = self.get_best_bbox(bbox_list)
            
            for i in self.key_list:
                x1 = self.df[str(i) + "_bbox_x1"].dropna().iloc[-1]
                y1 = self.df[str(i) + "_bbox_y1"].dropna().iloc[-1]
                x2 = self.df[str(i) + "_bbox_x2"].dropna().iloc[-1]
                y2 = self.df[str(i) + "_bbox_y2"].dropna().iloc[-1]
                # bboxから画像を切り出して640x640にリサイズ
                clip, new_x1, new_y1, new_x2, new_y2 = get_frame(image, [x1, y1, x2, y2])
                clip = cv2.resize(clip, (self.pose_size, self.pose_size))
                # POSE推定
                pose_results = self.pose.predict(clip, imgsz=640, conf=0.1, save=False, project="/tmp")
                xys = pose_results[0].keypoints.xy[0].tolist()
                base_x, base_y = xys[0][0], xys[0][1]
                tip_x, tip_y = xys[1][0], xys[1][1]
                base_x = base_x /self.pose_size * (new_x2 - new_x1) + new_x1
                base_y = base_y /self.pose_size * (new_y2 - new_y1) + new_y1
                tip_x = tip_x /self.pose_size * (new_x2 - new_x1) + new_x1
                tip_y = tip_y /self.pose_size * (new_y2 - new_y1) + new_y1
                # dfに保存
                self.df.loc[self.now_time, [f'{i}_base_x', f'{i}_base_y', f'{i}_tip_x', f'{i}_tip_y', f'{i}_angle', f'{i}_length']] = [
                    base_x, base_y, tip_x, tip_y,
                    np.arctan2(tip_y - base_y, tip_x - base_x),
                    np.sqrt((tip_x - base_x) ** 2 + (tip_y - base_y) ** 2),
                ]
            self.df.loc[self.now_time, 'now_leaf_num'] = len(self.key_list)
            self.df.loc[self.now_time, 're_detection'] = 0
                # 萎れ指標を計算
            self.cal_wilt()
            self.cal_final_wilt()

            if len(self.key_list) < 5:
                self.df.loc[self.now_time, 're_detection'] = 1
        except:
            self.df.loc[self.now_time, 're_detection'] = 1
        return self.df


if __name__ == "__main__":
    # now_time = datetime.now().replace(second=0, microsecond=0)
    now_time = datetime.strptime("2025-04-12 12:00:00", "%Y-%m-%d %H:%M:%S")
    df = pd.DataFrame()
    image_dir = "/home/pinode3/data/image/image4"
    date = now_time.strftime('%Y%m%d')
    image_dir = os.path.join(image_dir, date)
    img_pro = image_processor(df, image_dir,now_time)
    img_pro.first_detection()