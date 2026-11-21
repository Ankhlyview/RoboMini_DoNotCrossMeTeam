from __future__ import annotations
from typing import List,Sequence,Tuple
from dataclasses import dataclass

import math
import cv2
import numpy as np

# 这个是红蓝双方的提取颜色的hsv值
# 实际情况下，这个两个值还得经过一些小调整
team_hsv = {"blue":((93,120,150),(117,255,255)),"red":((0,150,150),(8,255,255))}

@dataclass(frozen=True)
class Detection:
    state:str         # 识别到的类型，要不要打的
    center_x:float    # 靶的中心的x
    center_y:float    # 靶的中心的x
    num_bars:int      # 一共有多少个条

    ratio:float
    area:float
    radius:float
    bars:Tuple[Tuple[float,float,float],...]    # 用于记录每一个靶的详细参数
    quality:float

    @property
    def is_pending(self) -> bool:
        return self.state == "pending"
    
class RuneDetect:

    # 初始化相关参数()
    def __init__(self,side:str = "blue",hsv_low:Sequence[int] | None = None,
                 hsv_high:Sequence[int] | None=None,min_bar_area:int=45,max_bar_area:int=1800,
                 max_bar_dim:int=80,min_aspect:float=0.2,max_aspect:float=5.0,
                 cluster_dist:float=85.0,min_green:float=25.0)->None:
        if side not in team_hsv:
            raise ValueError(f"don't have this color")
        self.side = side
        self.range = team_hsv[side]
        self.min_bar_area = min_bar_area
        self.max_bar_area = max_bar_area
        self.max_bar_dim = max_bar_dim
        self.min_aspect = min_aspect
        self.max_aspect = max_aspect
        self.cluster_dist = cluster_dist
        # 或许以后有用()
        self.min_green = min_green

    # 单纯就是一个获得掩码的函数
    def get_mask(self,img:np.ndarray) -> np.ndarray:
        out = None
        hsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
        for low,high in self.range:
            part = cv2.inRange(hsv,np.array(low,np.uint8),np.array(high,np.uint8))
            out = part if out is None else cv2.bitwise_or(out,part)
        kernel = np.ones((3,3),np.uint8)
        out = cv2.morphologyEx(out,cv2.MORPH_OPEN,kernel)
        return out
    
    # 通过连同性测试和一些判断，来获得离散的条的一些信息
    # 后期修改的话，就是增加一些限制条件或者减少一点限制条件
    def bars(self,img:np.ndarray):
        mask = self.mask(img)
        count,labels,stats,centroids = cv2.connectedComponentsWithStats(mask,8)
        bars = []

        for i in range(1,count):
            x,y,w,h,area = (int(k) for k in stats[i])
            if area < self.min_bar_area or area > self.max_bar_area:
                continue
            if w > self.max_bar_dim or h > self.max_bar_dim:
                continue
            aspect = w/max(h,1)
            if aspect < self.min_aspect or aspect > self.max_aspect :
                continue
            bars.append({
                "u":float(centroids[i][0]),
                "v":float(centroids[i][1]),
                "area":float(area),
                "w":w,"h":h
            })

        return mask,bars
    
    # 一个聚类算法函数()
    def cluster_(self,bars):
        n = len(bars)
        parent = list(range(n))

        # 一个很简单的归属问题
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        
        def union(a,b):
            pa,pb = find(a),find(b)
            if pa != pb:
                parent[pb] = pa

        dist2 = self.cluster_dist * self.cluster_dist
        for i in range(n):
            for j in range(i + 1,n):
                dx = bars[i]["u"] - bars[j]["u"]
                dy = bars[i]["v"] - bars[j]["v"]
                if dx * dx + dy * dy <= dist2:
                    union(i,j)

        # ?
        groups = {}
        for i in range(n):
            groups.setdefault(find(i), []).append(bars[i])
        return list(groups.values())
        
    # 检测主程序接口
    def detect_process(self,img:np.ndarray)->List[Detection]:
        mask,bars = self.bars(img)
        detections:List[Detection] = []
        # 这个是对一组进行了一些操作
        for group in self.cluster_(bars):
            num_bars = len(group)
            if num_bars < 2:
                continue
            total_areas = sum(b["area"] for b in group)
            us = np.array([b["u"] for b in group],dtype=float)
            vs = np.array([b["v"] for b in group],dtype=float)
            weights = np.array([b["area"] for b in group],dtype=float)
            """虽然但是这样是有一定的bias的"""
            center_x = float(np.sum(us*weights)/max(weights.sum(),1e-9))
            center_y = float(np.sum(vs*weights)/max(weights.sum(),1e-9))
            # 用一些神秘的方式计算一些值
            pts = np.stack([us - center_x, vs - center_y], axis=1)
            cov = pts.T @ pts / max(num_bars, 1)
            eig = np.linalg.eigvalsh(cov)
            ratio = float(eig[0] / max(eig[1], 1e-9))
            radius = float(np.max(np.hypot(us - center_x, vs - center_y))) + 12.0

            """如果想要更加准确的识别的话，就一定要用更加准确的方式来进行判断"""
            if num_bars >= 4:
                state = "pending"
            elif num_bars == 3 and ratio >= 0.12:
                state = "pending"
            elif num_bars == 2:
                state = "active"
            else:
                continue
            
            # 依旧计算一些神秘的小数值
            if state == "pending":
                quality = min(1.0, total_areas / 900.0) * (0.5 + 0.5 * ratio)
            else:
                quality = min(1.0, total_areas/ 600.0)

            detections.append(
                Detection(
                    state=state,
                    u=center_x,
                    v=center_y,
                    num_bars=num_bars,
                    ratio=ratio,
                    area=total_areas,
                    radius=radius,
                    bars=tuple((b["u"], b["v"], b["area"]) for b in group),
                    quality=float(quality),
                )
            )
        # 说实话，我没有理解这个操作的实际意义
        detections.sort(key=lambda d: d.area, reverse=True)
        return detections

def draw_detections(image: np.ndarray, detections: Sequence[Detection]) -> np.ndarray:
    out = image.copy()
    for det in detections:
        pending = det.is_pending
        color = (0, 255, 0) if pending else (0, 165, 255)
        center = (int(round(det.u)), int(round(det.v)))
        cv2.circle(out, center, int(max(det.radius + 8, 20)), color, 2)
        cv2.drawMarker(out, center, color, cv2.MARKER_CROSS, 14, 2)
        label = f"{'PENDING' if pending else 'ACTIVE'} {det.n_bars}"
        ty = int(max(center[1] - det.radius - 18, 16))
        cv2.putText(out, label, (max(center[0] - 48, 4), ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    return out


def draw_hud(image: np.ndarray, lines: Sequence[str],
             origin: Tuple[int, int] = (12, 22)) -> np.ndarray:
    out = image
    x, y = origin
    for i, line in enumerate(lines):
        yy = y + i * 22
        cv2.putText(out, line, (x + 1, yy + 1), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(out, line, (x, yy), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return out












