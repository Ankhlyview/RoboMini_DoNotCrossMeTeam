"""Geometry for the ROBOMINI energy-rune auto-aim task.

All lengths are metres, angles radians.  The world frame is the Gazebo world:
Z up, the blue launcher sits at y = -2.07 facing +Y, the red launcher at
y = +2.07 facing -Y.

The camera is rigidly mounted on ``pitch_link``:

* sensor pose in ``pitch_link``: ``(0, 0.036, 0.075)`` with a +90 deg yaw,
* lens: 1280x720, HFOV 60 deg, no distortion,
* the optical axis is parallel to the barrel (+Y of ``pitch_link``).

``GimbalToVision.q`` is the IMU orientation of ``pitch_link`` in the world
(body -> world, ``w, x, y, z``).  There is no TF tree in the simulation, so the
camera pose is rebuilt here from ``q`` and the known mount offset.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRAVITY = 9.81               # 重力加速度
BALL_SPEED_DEFAULT = 12.0    # 子弹的速度

RUNE_RADIUS = 0.350          # target centres on this circle around the hub axis
AXIS_Z = 0.928               # hub axis height
PLATE_SIZE = 0.195           # square plate side (metres)
TARGET_COUNT = 5

YAW_LIMIT = math.pi / 2.0    # 这个是左右摆副的限制
PITCH_MIN = math.radians(-10.0)
PITCH_MAX = math.radians(45.0)

#: 三个安装偏移，均相对 pitch_link 原点，单位 m，坐标轴 = (右, 前, 上)：
#:   CAMERA_OFFSET      : 相机传感器原点（前 0.036，上 0.075）
#:   MUZZLE_OFFSET      : 零俯仰时枪口 muzzle_link 原点（前 0.095）
#:   PITCH_PIVOT_OFFSET : 俯仰关节轴（在 pitch_link 原点上方 0.145）
#:
#: 注意：SDF 里 <joint><pose> 是相对 child link 的，所以俯仰关节轴并不在
#: pitch_link 原点上，而是在它上方 0.145 m。pitch_link/相机/枪口都绕这个
#: 轴转动，`pitch_link_origin()` 会把这部分平移补回来。
#: camera sensor pose inside pitch_link (x, y, z) = (right, forward, up)
CAMERA_OFFSET = np.array([0.0, 0.036, 0.075], dtype=float)  # 相机的位姿
#: muzzle_link origin inside pitch_link (muzzle_offset along the barrel) 
MUZZLE_OFFSET = np.array([0.0, 0.095, 0.0], dtype=float)    # 

#: 俯仰关节轴相对 pitch_link 原点的偏移（SDF 中 pitch_joint 的 <pose> 相对 child link）
PITCH_PIVOT_OFFSET = np.array([0.0, 0.0, 0.145], dtype=float)

#: ROS optical frame (x right, y down, z forward) expressed in pitch_link axes.
#: gz camera looks along +X (sensor), +Y left, +Z up, and the sensor is
#: rotated +90 deg about Z inside pitch_link.
R_ROS_IN_PL = np.array(
    [
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0],
    ],
    dtype=float,
)

TEAMS = ("blue", "red")

#: Per-team static geometry.
#: ``base``  : pitch/yaw axis origin in the world (z = 0.31 table + 0.04 yaw link
#:             + 0.145 pitch joint).
#: ``plane_y``: the five plate centres of this side share this y coordinate.
#: ``normal`` : outward plate normal (towards this side's launcher).
#: ``base_yaw``: world yaw of the launcher model (blue 0, red pi).
# 事实上就是红蓝双方的发射台的配置有点不一样罢了()
TEAM_GEOMETRY = {
    "blue": {
        "base": np.array([0.0, -2.07, 0.495], dtype=float),
        "plane_y": -0.116,
        "axis": np.array([0.0, 0.0, AXIS_Z], dtype=float),
        "normal": np.array([0.0, -1.0, 0.0], dtype=float),
        "base_yaw": 0.0,
        "forward": np.array([0.0, 1.0, 0.0], dtype=float),
    },
    "red": {
        "base": np.array([0.0, 2.07, 0.495], dtype=float),
        "plane_y": 0.116,
        "axis": np.array([0.0, 0.0, AXIS_Z], dtype=float),
        "normal": np.array([0.0, 1.0, 0.0], dtype=float),
        "base_yaw": math.pi,
        "forward": np.array([0.0, -1.0, 0.0], dtype=float),
    },
}

# 是否存在相应的颜色方
def check_side(side: str) -> str:
    if side not in TEAMS:
        raise ValueError(f"side must be one of {TEAMS}, got {side!r}")
    return side

# 初始化配置
def geometry(side: str) -> dict:
    return TEAM_GEOMETRY[check_side(side)]


# ---------------------------------------------------------------------------
# Small math helpers
# ---------------------------------------------------------------------------

# 防止跑飞的限制
def wrap_pi(angle: float) -> float:
    """Wrap to (-pi, pi]."""
    return math.atan2(math.sin(angle), math.cos(angle))

# 按照z轴旋转一定角度的旋转矩阵
def rot_z(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])

# 按照x轴旋转一定角度的旋转矩阵
def rot_x(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])

# 四元数转旋转矩阵
def quat_to_matrix(q) -> np.ndarray:
    """``q`` is ``(w, x, y, z)`` (GimbalToVision order)."""
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

# 上面的逆
def matrix_to_quat(r: np.ndarray):
    """Rotation matrix -> ``(w, x, y, z)``."""
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


# ---------------------------------------------------------------------------
# Camera pose / ray casting
# ---------------------------------------------------------------------------

# 这个类单纯是相机的位姿的结构体
@dataclass(frozen=True)
class CameraPose:
    position: np.ndarray
    rotation: np.ndarray  # maps camera (ROS optical) vectors to world

# 找到云台的俯仰轴的位姿，其实就是为了给相机头找位姿的
def pitch_link_origin(side: str, yaw: float, pitch: float) -> np.ndarray:
    """World position of the pitch_link origin for the given joint angles.

    ``TEAM_GEOMETRY[...]["base"]`` is the pitch_link origin at zero pitch.
    The link rotates about the pitch joint pivot, which sits
    ``PITCH_PIVOT_OFFSET`` above that origin, so the origin itself translates
    as ``pivot + R*(base - pivot)`` when pitching.
    """
    g = geometry(side)
    pivot = g["base"] + PITCH_PIVOT_OFFSET
    r_pl = rot_z(g["base_yaw"] + float(yaw)) @ rot_x(float(pitch))
    return pivot + r_pl @ (g["base"] - pivot)

# 相机的位姿解算
def camera_pose(side: str, yaw: float, pitch: float) -> CameraPose:
    """World pose of the camera from the measured yaw/pitch joint angles.

    Using the joint angles (instead of the IMU quaternion) keeps the two sides
    consistent: Gazebo's IMU on the red launcher reports its orientation in the
    launcher's base frame, i.e. without the model's 180 deg mounting yaw, while
    the joint angles are already relative to that mounting yaw.
    """
    g = geometry(side)
    r_pl = rot_z(g["base_yaw"] + float(yaw)) @ rot_x(float(pitch))
    position = pitch_link_origin(side, yaw, pitch) + r_pl @ CAMERA_OFFSET
    return CameraPose(position=position, rotation=r_pl @ R_ROS_IN_PL)

# 给定两个像素点和相机内参，来解算这个点相对于相机坐标系的偏角的
def pixel_ray(u: float, v: float, k) -> np.ndarray:
    """Unit ray in the ROS optical frame for pixel ``(u, v)``.

    ``k`` is the 3x3 row-major ``CameraInfo.k``.
    """
    fx, fy = float(k[0]), float(k[4])
    cx, cy = float(k[2]), float(k[5])
    if fx <= 0.0 or fy <= 0.0:
        raise ValueError("invalid camera intrinsics")
    ray = np.array([(float(u) - cx) / fx, (float(v) - cy) / fy, 1.0])
    return ray / np.linalg.norm(ray)

# 求给定相机位姿和这个点的角度，求和物理世界中面的那个角重合
def ray_plane(cam: CameraPose, direction: np.ndarray, plane_y: float,
              min_t: float = 0.2, max_t: float = 12.0):
    """Intersect a world ray with the horizontal plane ``y = plane_y``."""
    if abs(direction[1]) < 1e-9:
        return None
    t = (plane_y - cam.position[1]) / direction[1]
    if t < min_t or t > max_t:
        return None
    return cam.position + t * direction

# 综合函数
def pixel_to_plane(u: float, v: float, k, side: str, yaw: float, pitch: float):
    """Pixel -> world point on this side's rune plane (no prior snap)."""
    cam = camera_pose(side, yaw, pitch)
    direction = cam.rotation @ pixel_ray(u, v, k)
    return ray_plane(cam, direction, geometry(side)["plane_y"])

# 综合函数的逆
def world_to_pixel(point, k, side: str, yaw: float, pitch: float):
    """Project a world point into the camera; returns (u, v, depth) or None."""
    cam = camera_pose(side, yaw, pitch)
    local = cam.rotation.T @ (np.asarray(point, dtype=float) - cam.position)
    depth = float(local[2])
    if depth <= 1e-6:
        return None
    fx, fy = float(k[0]), float(k[4])
    cx, cy = float(k[2]), float(k[5])
    return (cx + fx * local[0] / depth, cy + fy * local[1] / depth, depth)


# ---------------------------------------------------------------------------
# Rune target geometry
# ---------------------------------------------------------------------------

# 给定一个极角，求这个能量机关在现实中的位置
def target_point(side: str, theta: float) -> np.ndarray:
    """Plate centre on the rune circle at polar angle ``theta`` (X-Z plane)."""
    g = geometry(side)
    return np.array(
        [
            g["axis"][0] + RUNE_RADIUS * math.cos(theta),
            g["plane_y"],
            g["axis"][2] + RUNE_RADIUS * math.sin(theta),
        ]
    )

# 上面的逆
def point_to_theta(side: str, point: np.ndarray) -> float:
    g = geometry(side)
    return math.atan2(float(point[2]) - g["axis"][2],
                      float(point[0]) - g["axis"][0])

# 自动吸附(世界函数)
def snap_to_rune(side: str, point: np.ndarray):
    """Snap a plane intersection to the known rune circle.

    Returns ``(snapped_point, theta, residual)``.  The residual is the distance
    between the observed intersection and the circle; a large residual means
    the detection is not a plate of this side (e.g. the back face).
    """
    theta = point_to_theta(side, point)
    snapped = target_point(side, theta)
    return snapped, theta, float(np.linalg.norm(np.asarray(point) - snapped))

# 结算目标装甲板的位姿(这个在整个工程中作用不大)
def target_quaternion(side: str, theta: float):
    """Orientation of the plate frame: x = radial, y = tangent, z = normal."""
    g = geometry(side)
    x_axis = np.array([math.cos(theta), 0.0, math.sin(theta)])
    z_axis = g["normal"]
    y_axis = np.cross(z_axis, x_axis)
    y_axis /= max(np.linalg.norm(y_axis), 1e-12)
    rotation = np.column_stack([x_axis, y_axis, z_axis])
    return matrix_to_quat(rotation)


# ---------------------------------------------------------------------------
# Ballistics / gimbal aim
# ---------------------------------------------------------------------------

# 用于计算yaw
def yaw_from_delta(side: str, dx: float, dy: float) -> float:
    """Joint yaw for a horizontal displacement, 0 = this side's forward."""
    g = geometry(side)
    fx, fy = float(g["forward"][0]), float(g["forward"][1])
    return math.atan2(fx * dy - fy * dx, fx * dx + fy * dy)

# 用服空气阻力的模型去拟合一个pitch角(按照物理学，这个本来是不唯一的角)
def solve_pitch(horizontal: float, dz: float, speed: float) -> float:
    """Launch pitch for a projectile hitting ``(horizontal, dz)``.

    Uses the same no-drag model as the Gazebo plugin:
    ``dz = d*tan(t) - g*d^2 / (2*v^2*cos^2(t))``, solved by bisection on the
    monotonic branch inside the joint limits.
    """
    if speed <= 0.0:
        raise ValueError("speed must be positive")
    if horizontal < 1e-6:
        return PITCH_MAX if dz > 0.0 else PITCH_MIN

    def height_error(theta: float) -> float:
        c = math.cos(theta)
        return (horizontal * math.tan(theta)
                - 0.5 * GRAVITY * horizontal * horizontal / (speed * speed * c * c)
                - dz)

    lo, hi = PITCH_MIN, PITCH_MAX
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
    return pitch_link_origin(side, yaw, pitch) + r_pl @ MUZZLE_OFFSET

# 瞄准函数
def aim_at(side: str, point, speed: float = BALL_SPEED_DEFAULT,
           yaw0: float = 0.0, pitch0: float = 0.0, iterations: int = 6):
    """Joint ``(yaw, pitch)`` that puts a ``speed`` projectile through ``point``.

    The muzzle moves with the pitch joint, so the solution is iterated a few
    times.  The returned angles are clamped to the joint limits.
    """
    point = np.asarray(point, dtype=float)
    yaw, pitch = float(yaw0), float(pitch0)
    for _ in range(max(1, iterations)):
        muzzle = muzzle_position(side, yaw, pitch)
        dx, dy, dz = point - muzzle
        yaw = yaw_from_delta(side, dx, dy)
        horizontal = math.hypot(dx, dy)
        pitch = solve_pitch(horizontal, dz, speed)
    yaw = max(-YAW_LIMIT, min(YAW_LIMIT, yaw))
    pitch = max(PITCH_MIN, min(PITCH_MAX, pitch))
    return yaw, pitch

# 计算飞行时间函数
def flight_time(side: str, point, speed: float = BALL_SPEED_DEFAULT) -> float:
    """Approximate time of flight from the muzzle to ``point``."""
    point = np.asarray(point, dtype=float)
    g = geometry(side)
    muzzle = g["base"] + MUZZLE_OFFSET
    horizontal = math.hypot(point[0] - muzzle[0], point[1] - muzzle[1])
    return max(0.0, horizontal / max(speed, 1e-6))
