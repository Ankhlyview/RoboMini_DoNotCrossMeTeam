"""Traditional HSV/connected-component detector for the energy rune lights.

The rune has five plates per side.  Each plate carries four light bars:

* two radial bars (inner/outer) on opposite sides of the plate centre,
* two tangential bars on the other axis.

The referee maps them to three states:

=====  ==========================================
state  visible bars
=====  ==========================================
off    none
active only the two tangential bars
pending all four bars (radial + tangential)
=====  ==========================================

So a pending plate is recognised by "four bars arranged in a cross"; an active
plate by "two collinear bars".  The plate centre is the area-weighted centroid
of its bars (the four-bar layout is symmetric about the plate centre).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import cv2
import numpy as np

# OpenCV HSV ranges (H in 0..180, S/V in 0..255).
# The blue bars render around H=101, while the blue field lines are H=120;
# the upper bound below is what keeps the field markings out of the mask.

# 这个是HSV的识别相应颜色的值
TEAM_HSV = {
    "blue": (((93, 120, 150), (117, 255, 255)),),
    "red": (
        ((0, 150, 150), (8, 255, 255)),
        ((172, 150, 150), (180, 255, 255)),
    ),
}


# 这个就是Detection的返回变量列表
@dataclass(frozen=True)
class Detection:
    state: str          # "pending" | "active"
    u: float            # plate centre pixel
    v: float
    n_bars: int
    ratio: float        # PCA minor/major eigenvalue ratio (2D spread)
    area: float         # total light-pixel area
    radius: float       # approximate plate radius in pixels (for drawing)
    bars: Tuple[Tuple[float, float, float], ...]
    quality: float      # 0..1 confidence used for firing

    @property
    def is_pending(self) -> bool:
        return self.state == "pending"


class RuneDetector:
    """HSV light-bar detector + pending/active classifier."""

    def __init__(
        self,
        side: str = "blue",
        *,
        hsv_low: Sequence[int] | None = None,
        hsv_high: Sequence[int] | None = None,
        min_bar_area: int = 45,
        max_bar_area: int = 1800,
        max_bar_dim: int = 80,
        min_aspect: float = 0.2,
        max_aspect: float = 5.0,
        cluster_eps: float = 85.0,    #聚类算法用到的值
        min_green: float = 25.0,
    ) -> None:
        if side not in TEAM_HSV:
            raise ValueError(f"side must be one of {tuple(TEAM_HSV)}, got {side!r}")
        self.side = side
        if hsv_low is not None and hsv_high is not None:
            self.ranges = ((tuple(int(v) for v in hsv_low),
                            tuple(int(v) for v in hsv_high)),)
        else:
            self.ranges = TEAM_HSV[side]
        self.min_bar_area = int(min_bar_area)
        self.max_bar_area = int(max_bar_area)
        self.max_bar_dim = int(max_bar_dim)
        self.min_aspect = float(min_aspect)
        self.max_aspect = float(max_aspect)
        self.cluster_eps = float(cluster_eps)
        # Field markings are pure red/blue (BGR G channel ~0), while the rune
        # light bars are tinted (blue G~159, red G~89).  This rejects field lines.
        self.min_green = float(min_green)

    # ------------------------------------------------------------------
    # Mask / bars
    # ------------------------------------------------------------------
    ## 生成了一个mask图，就是将相应的颜色提取出来了
    def mask(self, bgr: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        out = None
        for low, high in self.ranges:
            part = cv2.inRange(hsv, np.array(low, np.uint8), np.array(high, np.uint8))
            out = part if out is None else cv2.bitwise_or(out, part)
        assert out is not None
        kernel = np.ones((3, 3), np.uint8)
        out = cv2.morphologyEx(out, cv2.MORPH_OPEN, kernel)
        return out

    ##用于找一个一个的扇页上的条的
    def bars(self, bgr: np.ndarray):
        mask = self.mask(bgr)
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
        bars = []
        for i in range(1, count):
            x, y, w, h, area = (int(v) for v in stats[i])
            if area < self.min_bar_area or area > self.max_bar_area:
                continue
            comp = labels[y:y + h, x:x + w] == i
            if comp.any():
                mean_green = float(bgr[y:y + h, x:x + w, 1][comp].mean())
                if mean_green < self.min_green:
                    continue
            if w > self.max_bar_dim or h > self.max_bar_dim:
                continue
            aspect = w / max(h, 1)
            if aspect < self.min_aspect or aspect > self.max_aspect:
                continue
            bars.append(
                {
                    "u": float(centroids[i][0]), #X
                    "v": float(centroids[i][1]), #Y
                    "area": float(area),
                    "w": w,
                    "h": h,
                }
            )
        return mask, bars

    ## 聚类算法，实际上就是算了个距离的分类
    ## 事实上注意到这个结算的形式，还是有点费时间的
    def _cluster(self, bars):
        n = len(bars)
        parent = list(range(n))

        # 这个就是找到一个条的最后一个亲人
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        # 认为这个a,b两个节点是一个叶片上的
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        eps2 = self.cluster_eps ** 2
        for i in range(n):
            for j in range(i + 1, n):
                dx = bars[i]["u"] - bars[j]["u"]
                dy = bars[i]["v"] - bars[j]["v"]
                if dx * dx + dy * dy <= eps2:
                    union(i, j)

        groups = {}
        for i in range(n):
            groups.setdefault(find(i), []).append(bars[i])
        return list(groups.values())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    # 直接调用的总体的检测的列表()
    def detect(self, bgr: np.ndarray) -> List[Detection]:
        """Return pending/active detections, largest first."""
        mask, bars = self.bars(bgr)
        detections: List[Detection] = []
        for group in self._cluster(bars):
            n_bars = len(group)
            if n_bars < 2:
                continue
            total_area = sum(b["area"] for b in group)
            us = np.array([b["u"] for b in group], dtype=float)
            vs = np.array([b["v"] for b in group], dtype=float)
            # area-weighted centre (all bars have similar area)
            weights = np.array([b["area"] for b in group], dtype=float)
            cu = float(np.sum(us * weights) / max(weights.sum(), 1e-9))
            cv_ = float(np.sum(vs * weights) / max(weights.sum(), 1e-9))
            pts = np.stack([us - cu, vs - cv_], axis=1)
            cov = pts.T @ pts / max(n_bars, 1)
            eig = np.linalg.eigvalsh(cov)
            ratio = float(eig[0] / max(eig[1], 1e-9))
            radius = float(np.max(np.hypot(us - cu, vs - cv_))) + 12.0

            if n_bars >= 4:
                state = "pending"
            elif n_bars == 3 and ratio >= 0.12:
                state = "pending"
            elif n_bars == 2:
                state = "active"
            else:
                continue

            # Confidence is used by the aim node before it pulls the trigger.
            if state == "pending":
                quality = min(1.0, total_area / 900.0) * (0.5 + 0.5 * ratio)
            else:
                quality = min(1.0, total_area / 600.0)

            detections.append(
                Detection(
                    state=state,
                    u=cu,
                    v=cv_,
                    n_bars=n_bars,
                    ratio=ratio,
                    area=total_area,
                    radius=radius,
                    bars=tuple((b["u"], b["v"], b["area"]) for b in group),
                    quality=float(quality),
                )
            )
        detections.sort(key=lambda d: d.area, reverse=True)
        return detections


# 画框的函数
def draw_detections(image: np.ndarray, detections: Sequence[Detection]) -> np.ndarray:
    """Draw circles/labels for pending (green) and active (orange) plates."""
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
