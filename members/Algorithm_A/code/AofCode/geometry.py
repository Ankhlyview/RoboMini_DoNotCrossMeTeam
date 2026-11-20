from __future__ import annotations
from dataclasses import dataclass

import math
import numpy as np

# 这个文档基本都是写像素和世界的转换的
"""特别提醒,这个玩意在世纪上十分依赖于yaw和pitch的正确性,所以说得压力电控,要不然就得买一个编码器"""
"""特别提醒x2,这个我们现在是一个理想的物理模型，在不考虑空气阻力，弹丸的旋转等等一切的扰动"""

gravity = 9.81    # 广州市的重力加速度是9.7883m/s/s
ball_speed = 12   # 这个要考虑实际的速度(这个速度不可能太慢)(单位:m/s2)
orbital_radius = 0.350  # 这个是世界的值(单位:m)
hub_height = 0.928  # 这个也是世界的值，是指旋转中心的高度，m
plate_size = 0.195  # 这个不知道是什么东西
target_count = 5    # 

yaw_limit = math.pi/2.0                # yaw的最大片转角
pitch_min_limit = math.radians(-10.0)  # pitch的上限
pitch_max_limit = math.radians(45.0)   # pitch的下线

# 下面的所有值都是在yaw和pitch都为0的时候册出来的值
camera_offset = np.array([0.0, 0.036, 0.075], dtype=float)     # 相机的偏差,m
muzzle_offset = np.array([0.0, 0.095, 0.0], dtype=float)       # 枪口的偏差,m
pitch_pivot_offset = np.array([0.0, 0.0, 0.145], dtype=float)  # 俯仰轴的偏差,m

"""特别提醒x3,上述的值是在仿真环境中的值，实际上应该手动去量()"""

# 因为一些坐标系的设置关系，需要进行一些转置函数
R_ROS_IN_PL = np.array(
    [
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0],
    ],
    dtype=float,
)

teams = ("blue","red")

# base:yaw和pitch的原点
# plane_y:五个靶的共享的坐标
# axis:这个是Buff中心的位置，也就是旋转中心
# normal:就是靶的朝向
# base_yaw:刚开始时yaw的大小(这里因为仿真的问题一个是pi)
# forward:发射台的初始朝向
team_geometry = {
    "blue": {
        "base": np.array([0.0, -2.07, 0.495], dtype=float),
        "plane_y": -0.116,
        "axis": np.array([0.0, 0.0, hub_height], dtype=float),
        "normal": np.array([0.0, -1.0, 0.0], dtype=float),
        "base_yaw": 0.0,
        "forward": np.array([0.0, 1.0, 0.0], dtype=float),
    },
    "red": {
        "base": np.array([0.0, 2.07, 0.495], dtype=float),
        "plane_y": 0.116,
        "axis": np.array([0.0, 0.0, hub_height], dtype=float),
        "normal": np.array([0.0, 1.0, 0.0], dtype=float),
        "base_yaw": math.pi,
        "forward": np.array([0.0, -1.0, 0.0], dtype=float),
    },
}
"""特别提醒x3,上述的值是在仿真环境中的值，实际上应该手动去量()"""


def check_side(side:str)->str:
    if side not in teams:
        raise ValueError(f"根本就没有这样的队伍")
    return side

# 可以看成一种初始化
def geometry(side:str)->dict:
    return team_geometry[check_side(side)]

# 限制角度的值一直在(-pi,pi]中
def wrap_pi(angle:float)->float:
    return math.atan2(math.sin(angle),math.cos(angle))

# 下面都是一些旋转矩阵或者4元数的生成函数
def rot_z(angle:float)->float:
    Sin,Cos = math.sin(angle),math.cos(angle)
    return np.array([Cos,-Sin,0.0],[Sin,Cos,0.0],[0.0,0.0,1.0])

def rot_x(angle:float)->float:
    Sin,Cos = math.sin(angle),math.cos(angle)
    return np.array([1.0,0.0,0.0],[0.0,Cos,-Sin],[0.0,Sin,Cos])

def quat_to_matrix(q) -> np.ndarray:
    w, x, y, z = (float(v) for v in q)
    n = math.sqrt(w * w + x * x + y * y + z * z)
    if n < 1e-12:
        return np.eye(3)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=float,
    )

def matrix_to_quat(r: np.ndarray):
    m = np.asarray(r, dtype=float)
    trace = m[0, 0] + m[1, 1] + m[2, 2]
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2.0
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2.0
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2.0
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    q = np.array([w, x, y, z])
    return q / max(np.linalg.norm(q), 1e-12)

# 相机的位姿
@dataclass(frozen=True)
class CameraPose:
    position:np.ndarray
    rotation:np.ndarray

# 这个最大的问题是不知道pitch_link在哪？
def pitch_link_origin(side:str,yaw:float,pitch:float)->np.ndarray:
    g = geometry(side)
    pivot = g["base"] + pitch_pivot_offset
    rotation_matrix = rot_z(g["base_yaw"]+float(yaw)) @ rot_x(float(pitch))
    return pivot + rotation_matrix @ (g["base"] - pivot)

def camera_pose(side: str, yaw: float, pitch: float) -> CameraPose:
    g = geometry(side)
    rotation_matrix = rot_z(g["base_yaw"] + float(yaw)) @ rot_x(float(pitch))
    position = pitch_link_origin(side, yaw, pitch) + rotation_matrix @ camera_offset
    return CameraPose(position=position, rotation=rotation_matrix @ R_ROS_IN_PL)

# 这个k是相机的内参()有空看看详细实现
# 通过一个像素坐标得到一个相机坐标下的值
def pixel_ray(u:float,v:float,k)->np.ndarray:
    fx, fy = float(k[0]), float(k[4])
    cx, cy = float(k[2]), float(k[5])
    if fx <= 0.0 or fy <= 0.0:
        raise ValueError("invalid camera intrinsics")
    ray = np.array([(float(u) - cx) / fx, (float(v) - cy) / fy, 1.0])
    return ray / np.linalg.norm(ray)

# 射线和平面的交点
def ray_plane(cam: CameraPose, direction: np.ndarray, plane_y: float,
              min_t: float = 0.2, max_t: float = 12.0):
    if abs(direction[1]) < 1e-9:
        return None
    t = (plane_y - cam.position[1]) / direction[1]
    if t < min_t or t > max_t:
        return None
    return cam.position + t * direction

# 这个就是上面函数的综合形态
def pixel_to_plane(u: float, v: float, k, side: str, yaw: float, pitch: float):
    cam = camera_pose(side, yaw, pitch)
    direction = cam.rotation @ pixel_ray(u, v, k)
    return ray_plane(cam, direction, geometry(side)["plane_y"])


def world_to_pixel(point, k, side: str, yaw: float, pitch: float):
    cam = camera_pose(side, yaw, pitch)
    local = cam.rotation.T @ (np.asarray(point, dtype=float) - cam.position)
    depth = float(local[2])
    if depth <= 1e-6:
        return None
    fx, fy = float(k[0]), float(k[4])
    cx, cy = float(k[2]), float(k[5])
    return (cx + fx * local[0] / depth, cy + fy * local[1] / depth, depth)

# 在世界中，通过一个角度来得到响应目标的位置
def target_point(side:str,theta:float)->np.ndarray:
    g = geometry(side)
    return np.array([
        g["axis"][0] + orbital_radius * math.cos(theta),
        g["plane_y"],
        g["axis"][1] + orbital_radius * math.sin(theta),
    ])

# 上面的逆
def point_to_theta(side: str, point: np.ndarray) -> float:
    g = geometry(side)
    return math.atan2(float(point[2]) - g["axis"][2],
                      float(point[0]) - g["axis"][0])

# 这个自动吸附写的有点一言难尽()
"""这个可以进行修改"""
def snap_to_rune(side: str, point: np.ndarray):
    theta = point_to_theta(side, point)
    snapped = target_point(side, theta)
    return snapped, theta, float(np.linalg.norm(np.asarray(point) - snapped))

# 结算目标装甲板的位姿(这个在整个工程中作用不大)(因为都是正对的)
def target_quaternion(side: str, theta: float):
    g = geometry(side)
    x_axis = np.array([math.cos(theta), 0.0, math.sin(theta)])
    z_axis = g["normal"]
    y_axis = np.cross(z_axis, x_axis)
    y_axis /= max(np.linalg.norm(y_axis), 1e-12)
    rotation = np.column_stack([x_axis, y_axis, z_axis])
    return matrix_to_quat(rotation)


"""-------------------------------------------------------------------"""
# 用于计算yaw
def yaw_from_delta(side: str, dx: float, dy: float) -> float:
    g = geometry(side)
    fx, fy = float(g["forward"][0]), float(g["forward"][1])
    return math.atan2(fx * dy - fy * dx, fx * dx + fy * dy)

# 用服空气阻力的模型去拟合一个pitch角(按照物理学，这个本来是不唯一的角)
def solve_pitch(horizontal: float, dz: float, speed: float) -> float:
    if speed <= 0.0:
        raise ValueError("speed must be positive")
    if horizontal < 1e-6:
        return pitch_max_limit if dz > 0.0 else pitch_min_limit

    def height_error(theta: float) -> float:
        c = math.cos(theta)
        return (horizontal * math.tan(theta)
                - 0.5 * gravity * horizontal * horizontal / (speed * speed * c * c)
                - dz)

    lo, hi = pitch_min_limit, pitch_max_limit
    if height_error(lo) > 0.0:
        return lo
    if height_error(hi) < 0.0:
        return hi
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if height_error(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)

# 计算枪口位置(角度和摄像头相同)
def muzzle_position(side: str, yaw: float, pitch: float) -> np.ndarray:
    g = geometry(side)
    r_pl = rot_z(g["base_yaw"] + float(yaw)) @ rot_x(float(pitch))
    return pitch_link_origin(side, yaw, pitch) + r_pl @ muzzle_offset

# 瞄准函数
def aim_at(side: str, point, speed: float = ball_speed,
           yaw0: float = 0.0, pitch0: float = 0.0, iterations: int = 6):
    point = np.asarray(point, dtype=float)
    yaw, pitch = float(yaw0), float(pitch0)
    for _ in range(max(1, iterations)):
        muzzle = muzzle_position(side, yaw, pitch)
        dx, dy, dz = point - muzzle
        yaw = yaw_from_delta(side, dx, dy)
        horizontal = math.hypot(dx, dy)
        pitch = solve_pitch(horizontal, dz, speed)
    yaw = max(-yaw_limit, min(yaw_limit, yaw))
    pitch = max(pitch_min_limit, min(pitch_max_limit, pitch))
    return yaw, pitch

# 计算飞行时间函数
def flight_time(side: str, point, speed: float = ball_speed) -> float:
    point = np.asarray(point, dtype=float)
    g = geometry(side)
    muzzle = g["base"] + muzzle_offset
    horizontal = math.hypot(point[0] - muzzle[0], point[1] - muzzle[1])
    return max(0.0, horizontal / max(speed, 1e-6))