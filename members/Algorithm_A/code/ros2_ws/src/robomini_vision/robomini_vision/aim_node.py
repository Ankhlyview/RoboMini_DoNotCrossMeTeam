#!/usr/bin/env python3
"""Auto-aim node for the ROBOMINI energy rune (traditional vision only).

Pipeline (one camera frame):

1. HSV segmentation of the team-coloured light bars.
2. Connected components -> bars -> single-link clustering into plates.
3. Plate classification: 4 bars cross = ``pending``, 2 bars = ``active``.
4. Plate centre pixel -> ray -> intersection with the rune plane
   (``y = -0.116`` for blue, ``+0.116`` for red).
5. Snap the intersection to the known rune circle (R = 0.35 m) to obtain the
   plate pose (position + orientation).
6. Predict the target motion (rotating small/big rune) and solve the ballistic
   yaw/pitch from the muzzle, including gravity compensation.
7. Publish ``/vision_to_gimbal`` (mode 1 aim / mode 2 fire) and a debug image
   with the recognised pending/active lights drawn on it.

The node never reads ``/rune/state`` for control: that topic is only used by an
optional ``compare_ground_truth`` diagnostic.  Everything needed to aim comes
from the camera, the camera intrinsics and the gimbal IMU quaternion.
"""

from __future__ import annotations

import math
import os
import time

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image

from robomini_interfaces.msg import (
    GimbalToVision,
    RuneHit,
    RuneState,
    VisionToGimbal,
)

from . import geometry
from .detector import Detection, RuneDetector, draw_detections, draw_hud


class AimNode(Node):
    def __init__(self) -> None:
        super().__init__("robomini_aim")

        # ------------------------------------------------------------- params
        ## 全是参数，暂时忽略()
        self.declare_parameter("side", "blue")
        self.declare_parameter("camera_topic", "/camera/image_raw")
        self.declare_parameter("camera_info_topic", "/camera/camera_info")
        self.declare_parameter("ball_speed", 12.0)
        self.declare_parameter("fire", True)
        self.declare_parameter("fire_tolerance", 0.022)
        self.declare_parameter("min_quality", 0.45)
        self.declare_parameter("min_fire_bars", 4)
        self.declare_parameter("process_rate", 30.0)
        self.declare_parameter("save_hits", False)
        self.declare_parameter("lead_latency", 0.06)
        self.declare_parameter("search_timeout", 0.5)
        self.declare_parameter("track_memory", 0.35)
        self.declare_parameter("max_snap_error", 0.05)
        self.declare_parameter("debug_image", True)
        self.declare_parameter("debug_rate", 10.0)
        self.declare_parameter("show_window", False)
        self.declare_parameter("save_dir", "")
        self.declare_parameter("save_every", 2.0)
        self.declare_parameter("compare_ground_truth", False)
        self.declare_parameter("monitor_hits", True)
        # detector tuning
        self.declare_parameter("cluster_eps", 85.0)
        self.declare_parameter("min_bar_area", 45)
        self.declare_parameter("min_green", 25.0)

        self.side = str(self.get_parameter("side").value)
        self.ball_speed = float(self.get_parameter("ball_speed").value)
        self.fire_enabled = bool(self.get_parameter("fire").value)
        self.fire_tol = float(self.get_parameter("fire_tolerance").value)
        self.min_quality = float(self.get_parameter("min_quality").value)
        self.min_fire_bars = int(self.get_parameter("min_fire_bars").value)
        self.process_period = 1.0 / max(1.0, float(self.get_parameter("process_rate").value))
        self.save_hits = bool(self.get_parameter("save_hits").value)
        self.lead_latency = float(self.get_parameter("lead_latency").value)
        self.search_timeout = float(self.get_parameter("search_timeout").value)
        self.track_memory = float(self.get_parameter("track_memory").value)
        self.max_snap_error = float(self.get_parameter("max_snap_error").value)
        self.debug_enabled = bool(self.get_parameter("debug_image").value)
        self.debug_rate = max(1.0, float(self.get_parameter("debug_rate").value))
        self.show_window = bool(self.get_parameter("show_window").value)
        self.save_dir = str(self.get_parameter("save_dir").value).strip()
        self.save_every = max(0.0, float(self.get_parameter("save_every").value))
        self.compare_gt = bool(self.get_parameter("compare_ground_truth").value)
        self.monitor_hits = bool(self.get_parameter("monitor_hits").value)

        self.detector = RuneDetector(
            self.side,
            cluster_eps=float(self.get_parameter("cluster_eps").value),
            min_bar_area=int(self.get_parameter("min_bar_area").value),
            min_green=float(self.get_parameter("min_green").value),
        )

        # ------------------------------------------------------------- state
        self.bridge = CvBridge()
        self.k = None
        self.yaw_meas = 0.0
        self.pitch_meas = 0.0
        self.have_gimbal = False

        self.track = None          # dict: samples [(t, theta)], theta, omega, t
        self.last_pending_t = None
        self.last_cmd = None       # (yaw, pitch, mode)
        self.last_aim = None       # (t, yaw, pitch) for feed-forward
        self.last_detection_t = 0.0

        self.frame_count = 0
        self.shots_requested = 0
        self.bullets = 0
        self.last_bullet_count = None
        self.hits = 0
        self.last_log = 0.0
        self.last_debug = 0.0
        self.last_process = 0.0
        self.last_save = 0.0
        self.last_annotated = None
        self.last_header = None

        self.gt_pending = None
        self.gt_point = None

        # ------------------------------------------------------------- ROS I/O
        self.create_subscription(
            Image, str(self.get_parameter("camera_topic").value),
            self.on_image, qos_profile_sensor_data)
        self.create_subscription(
            CameraInfo, str(self.get_parameter("camera_info_topic").value),
            self.on_camera_info, qos_profile_sensor_data)
        self.create_subscription(GimbalToVision, "/gimbal_to_vision",
                                 self.on_gimbal, 10)
        if self.monitor_hits:
            self.create_subscription(RuneHit, "/rune/hit", self.on_hit, 10)
        if self.compare_gt:
            self.create_subscription(RuneState, "/rune/state", self.on_rune_state, 10)

        self.pub_cmd = self.create_publisher(VisionToGimbal, "/vision_to_gimbal", 10)
        self.pub_debug = self.create_publisher(Image, "/vision/debug_image", 5)
        self.pub_pose = self.create_publisher(PoseStamped, "/vision/target_pose", 10)

        if self.save_dir:
            os.makedirs(self.save_dir, exist_ok=True)

        self.get_logger().info(
            f"robomini_aim started: side={self.side} fire={self.fire_enabled} "
            f"speed={self.ball_speed:.1f} m/s tol={math.degrees(self.fire_tol):.2f} deg "
            f"debug={self.debug_enabled} save_dir={self.save_dir or '-'}")

    # ------------------------------------------------------------------ inputs
    # 接受相机的本体参数，就是相机标定的参数

    def on_camera_info(self, msg: CameraInfo) -> None:
        self.k = list(msg.k)

    # 接受云台的相关的yaw和pitch角
    def on_gimbal(self, msg: GimbalToVision) -> None:
        self.yaw_meas = float(msg.yaw)
        self.pitch_meas = float(msg.pitch)
        self.have_gimbal = True
        count = int(msg.bullet_count)
        if self.last_bullet_count is None:
            self.last_bullet_count = count
        elif count >= self.last_bullet_count:
            self.bullets += count - self.last_bullet_count
            self.last_bullet_count = count
        else:  # uint16 wrap / world reset
            self.bullets += count
            self.last_bullet_count = count

    # 接受裁判系统的小信息，实际上是没有这个东西的(只能靠视觉识别一个？)
    def on_hit(self, msg: RuneHit) -> None:
        if msg.valid:
            self.hits += 1
            self.get_logger().info(
                f"HIT target={msg.target} +{msg.score} score  ({self.hits} hits, "
                f"aim fired {self.shots_requested} requests)")
            if self.save_hits and self.last_annotated is not None and self.save_dir:
                self._save_snapshot(self.last_annotated, prefix="hit")

    # 实际没有的函数(只能用来调试这个)
    def on_rune_state(self, msg: RuneState) -> None:
        # Diagnostic only, never used for aiming.
        try:
            idx = list(msg.target_states).index(1)
        except ValueError:
            self.gt_pending = None
            self.gt_point = None
            return
        self.gt_pending = idx
        self.gt_point = geometry.target_point(self.side, float(msg.target_angles[idx]))

    # ------------------------------------------------------------------ helpers
    # 将一个照片中的像素点投影到世界上，然后得到极角(就是相对于旋转中心的角)
    # 这个就是借助摄像机现在的位姿和射线相交的位置，这里最主要的问题是旋转中心是怎么确定的
    # 这个还加上了吸附功能，吸附在一个圆上
    # 这玩意也是个合集
    def _track_theta(self, detection: Detection):
        if self.k is None:
            return None
        point = geometry.pixel_to_plane(
            detection.u, detection.v, self.k, self.side,
            self.yaw_meas, self.pitch_meas)
        if point is None:
            return None
        snapped, theta, residual = geometry.snap_to_rune(self.side, point)
        if residual > self.max_snap_error:
            return None
        return snapped, theta, residual


    # 这个用最小二乘法来进行了角速度的估算
    # 我们尝试用EKF进行再次的尝试
    @staticmethod
    def _estimate_omega(samples):
        if len(samples) < 3:
            return 0.0
        t = np.array([s[0] for s in samples], dtype=float)
        a = np.array([s[1] for s in samples], dtype=float)
        # unwrap relative to the first sample
        unwrapped = a[0] + np.unwrap(a - a[0])
        t0 = t - t.mean()
        denom = float(np.sum(t0 * t0))
        if denom < 1e-9:
            return 0.0
        omega = float(np.sum(t0 * (unwrapped - unwrapped.mean())) / denom)
        return max(-4.0, min(4.0, omega))

    # 用给滑动窗口(就是过去几秒和最新的来进行轨迹的更新，其实就是一个滑动窗口结合上面一个函数)，最后给出一个角速度
    # 同时在这里进行了一次切换目标的检测(),我们也可以用这个方法在EKF中
    def _update_track(self, now: float, theta: float) -> float:
        """Update the target track, returns the estimated angular velocity."""
        if self.track is None:
            self.track = {"samples": [(now, theta)], "theta": theta,
                          "omega": 0.0, "t": now, "settle": 1}
            return 0.0

        dt = now - self.track["t"]
        predicted = self.track["theta"] + self.track["omega"] * max(dt, 0.0)
        jump = abs(geometry.wrap_pi(theta - predicted))
        if jump > 0.40:
            # The referee switched the pending target (or the hub did a large step).
            self.track = {"samples": [(now, theta)], "theta": theta,
                          "omega": 0.0, "t": now, "settle": 1}
            return 0.0

        self.track["samples"].append((now, theta))
        self.track["samples"] = [s for s in self.track["samples"] if now - s[0] <= 0.7]
        self.track["omega"] = self._estimate_omega(self.track["samples"])
        self.track["theta"] = theta
        self.track["t"] = now
        self.track["settle"] = min(self.track["settle"] + 1, 100)
        return self.track["omega"]

    # 预测击打时候的角度
    def _predict_theta(self, now: float, theta: float) -> float:
        omega = self.track["omega"] if self.track else 0.0
        if abs(omega) < 0.05:
            return theta
        point = geometry.target_point(self.side, theta)
        t_flight = geometry.flight_time(self.side, point, self.ball_speed)
        return theta + omega * (t_flight + self.lead_latency)

    # ------------------------------------------------------------------ main loop
    # 主循环()
    def on_image(self, msg: Image) -> None:
        now = time.monotonic()                                                                  # 记录时间
        if now - self.last_process < self.process_period:                                       # 这个就是两次的处理时间特别短的话，直接返回
            return
        self.last_process = now
        if self.k is None or not self.have_gimbal:
            return
        try:
            bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")                       # 将节点传递的信息转成opencv的形式
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f"cv_bridge failed: {exc}", throttle_duration_sec=2.0)
            return
        self.frame_count += 1
        self.last_header = msg.header

        detections = self.detector.detect(bgr)                                                   # 进行检测，返回有很多的东西
        pending: list[tuple[Detection, np.ndarray, float, float]] = []
        for det in detections:                                                                   # 通过处理获得极角等等元素，并且筛选出相应的情况(我们只打4格灯条的情况)
            if not det.is_pending or det.quality < self.min_quality:
                continue
            solved = self._track_theta(det)
            if solved is None:
                continue
            point, theta, residual = solved
            pending.append((det, point, theta, residual))

        # 后面就在决定追踪的物体和解包物体的位姿等信息，然后发布打击命令
        chosen = None
        if pending:
            if self.track is not None:
                dt = now - self.track["t"]
                predicted = self.track["theta"] + self.track["omega"] * max(dt, 0.0)
                pending.sort(key=lambda item: abs(geometry.wrap_pi(item[2] - predicted)))
            else:
                pending.sort(key=lambda item: item[0].quality, reverse=True)
            chosen = pending[0]

        if chosen is not None:
            det, point, theta, residual = chosen
            omega = self._update_track(now, theta)
            theta_pred = self._predict_theta(now, theta)
            target = geometry.target_point(self.side, theta_pred)

            yaw, pitch = geometry.aim_at(
                self.side, target, self.ball_speed,
                yaw0=self.yaw_meas, pitch0=self.pitch_meas)
            err_yaw = geometry.wrap_pi(yaw - self.yaw_meas)
            err_pitch = pitch - self.pitch_meas
            aligned = abs(err_yaw) < self.fire_tol and abs(err_pitch) < self.fire_tol
            quality_ok = (det.n_bars >= self.min_fire_bars
                          and det.quality >= self.min_quality)
            settle_ok = bool(self.track and self.track["settle"] >= 2)
            fire = self.fire_enabled and aligned and quality_ok and settle_ok
            mode = 2 if fire else 1

            self.last_detection_t = now
            self.last_pending_t = now
            if fire and (self.last_cmd is None or self.last_cmd[2] != 2):
                self.shots_requested += 1

            self._publish_command(yaw, pitch, mode, now)
            self._publish_pose(point, theta, msg.header)

            if self.debug_enabled:
                self._debug(bgr, detections, chosen=(det, point, theta, omega,
                                                     target, yaw, pitch,
                                                     err_yaw, err_pitch,
                                                     aligned, fire, residual), now=now)
            if now - self.last_log > 1.0:
                self.last_log = now
                self._log_state(det, point, theta, omega, target, yaw, pitch,
                                err_yaw, err_pitch, aligned, fire)
            return

        # ---------------------------------------------------------- reacquire
        if self.track is not None and self.last_pending_t is not None \
                and (now - self.last_pending_t) < self.track_memory:
            # Dead-reckon through a short detection gap, but never fire.
            theta = self.track["theta"] + self.track["omega"] * (now - self.track["t"])
            target = geometry.target_point(self.side, theta)
            yaw, pitch = geometry.aim_at(
                self.side, target, self.ball_speed,
                yaw0=self.yaw_meas, pitch0=self.pitch_meas)
            self._publish_command(yaw, pitch, 1, now)
        elif self.last_pending_t is None or (now - self.last_pending_t) > self.search_timeout:
            # Point at the hub centre so that all five plates re-enter the FOV.
            home = np.array([0.0, geometry.geometry(self.side)["plane_y"],
                             geometry.AXIS_Z])
            yaw, pitch = geometry.aim_at(
                self.side, home, self.ball_speed,
                yaw0=self.yaw_meas, pitch0=self.pitch_meas)
            self._publish_command(yaw, pitch, 1, now)
            if now - self.last_log > 1.0:
                self.last_log = now
                self.get_logger().info(
                    f"SEARCH pending  aim=({yaw:+.3f},{pitch:+.3f}) "
                    f"detections={len(detections)}")
        else:
            self._republish_last(now)

        if self.debug_enabled:
            self._debug(bgr, detections, chosen=None, now=now)

    # ------------------------------------------------------------------ output
    # 发布命令，最然但是这个和小海龟不一样，这个发布一条就行了，但是海龟1s后就停止了
    def _publish_command(self, yaw: float, pitch: float, mode: int, now: float) -> None:
        yaw_vel = pitch_vel = 0.0
        if self.last_aim is not None:
            lt, ly, lp = self.last_aim
            dt = now - lt
            dyaw = geometry.wrap_pi(yaw - ly)
            if 0.0 < dt < 0.2 and abs(dyaw) < 0.15:
                yaw_vel = max(-3.0, min(3.0, dyaw / dt))
                pitch_vel = max(-2.0, min(2.0, (pitch - lp) / dt))
        self.last_aim = (now, yaw, pitch)

        cmd = VisionToGimbal()
        cmd.mode = int(mode)
        cmd.yaw = float(yaw)
        cmd.pitch = float(pitch)
        cmd.yaw_vel = float(yaw_vel)
        cmd.pitch_vel = float(pitch_vel)
        cmd.yaw_acc = 0.0
        cmd.pitch_acc = 0.0
        self.pub_cmd.publish(cmd)
        self.last_cmd = (float(yaw), float(pitch), int(mode), now)

    def _republish_last(self, now: float) -> None:
        if self.last_cmd is None:
            return
        yaw, pitch, mode, t = self.last_cmd
        if now - t < 0.05:
            return
        self._publish_command(yaw, pitch, mode, now)

    # 构建位姿的msg
    def _publish_pose(self, point: np.ndarray, theta: float, header) -> None:
        msg = PoseStamped()
        msg.header = header
        msg.header.frame_id = "world"
        msg.pose.position.x = float(point[0])
        msg.pose.position.y = float(point[1])
        msg.pose.position.z = float(point[2])
        qw, qx, qy, qz = geometry.target_quaternion(self.side, theta)
        msg.pose.orientation.w = float(qw)
        msg.pose.orientation.x = float(qx)
        msg.pose.orientation.y = float(qy)
        msg.pose.orientation.z = float(qz)
        self.pub_pose.publish(msg)

    # ------------------------------------------------------------------ debug
    def _debug(self, bgr, detections, chosen, now: float) -> None:
        due_publish = (now - self.last_debug) >= 1.0 / self.debug_rate
        due_save = (self.save_dir and self.save_every > 0.0
                    and now - self.last_save >= self.save_every)
        if not (due_publish or due_save or self.show_window):
            return
        vis = draw_detections(bgr, detections)
        cv2.drawMarker(vis, (bgr.shape[1] // 2, bgr.shape[0] // 2),
                       (128, 128, 128), cv2.MARKER_CROSS, 24, 1)
        lines = [f"side={self.side}  det={len(detections)}  "
                 f"pending={sum(1 for d in detections if d.is_pending)}"]
        if chosen is not None:
            (det, point, theta, omega, target, yaw, pitch,
             err_yaw, err_pitch, aligned, fire, residual) = chosen
            cv2.circle(vis, (int(det.u), int(det.v)), int(det.radius + 16),
                       (0, 255, 0), 2)
            cv2.drawMarker(vis, (int(det.u), int(det.v)), (0, 255, 0),
                           cv2.MARKER_CROSS, 28, 2)
            lines += [
                f"PENDING px=({det.u:.0f},{det.v:.0f}) n={det.n_bars} "
                f"q={det.quality:.2f} res={residual * 1000:.0f}mm",
                f"pose  x={point[0]:+.3f} y={point[1]:+.3f} z={point[2]:+.3f} "
                f"theta={theta:+.3f}",
                f"omega={omega:+.2f} rad/s  lead={math.degrees(omega * 0.16):+.1f} deg",
                f"aim   yaw={yaw:+.3f} pitch={pitch:+.3f} "
                f"meas=({self.yaw_meas:+.3f},{self.pitch_meas:+.3f})",
                f"err   yaw={math.degrees(err_yaw):+.2f} pitch={math.degrees(err_pitch):+.2f} deg "
                f"{'ALIGNED' if aligned else ''}",
                f"fire={fire}  shots={self.bullets}  hits={self.hits}",
            ]
            if self.compare_gt and self.gt_point is not None:
                err3 = float(np.linalg.norm(point - self.gt_point))
                lines.append(f"GT[{self.gt_pending}] err={err3 * 1000:.1f} mm")
        else:
            lines.append("SEARCH / no pending target")
        draw_hud(vis, lines)
        self.last_annotated = vis

        if due_publish:
            self.last_debug = now
            out = self.bridge.cv2_to_imgmsg(vis, encoding="bgr8")
            if self.last_header is not None:
                out.header = self.last_header
            self.pub_debug.publish(out)

        if self.show_window:
            cv2.imshow("robomini_vision", cv2.resize(vis, (960, 540)))
            cv2.waitKey(1)

        if due_save:
            self.last_save = now
            self._save_snapshot(vis, prefix="pending" if chosen else "search")

    def _save_snapshot(self, image, prefix: str = "frame") -> None:
        if not self.save_dir:
            return
        try:
            name = time.strftime("%Y%m%d_%H%M%S") + f"_{prefix}_{self.frame_count:06d}.png"
            path = os.path.join(self.save_dir, name)
            cv2.imwrite(path, image)
            self.get_logger().info(f"snapshot saved: {path}")
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f"snapshot failed: {exc}")

    def _log_state(self, det, point, theta, omega, target, yaw, pitch,
                   err_yaw, err_pitch, aligned, fire) -> None:
        extra = ""
        if self.compare_gt and self.gt_point is not None:
            err3 = float(np.linalg.norm(point - self.gt_point))
            extra = f" gt_err={err3 * 1000:.1f}mm gt_idx={self.gt_pending}"
        self.get_logger().info(
            f"pend px=({det.u:.0f},{det.v:.0f}) n={det.n_bars} q={det.quality:.2f} "
            f"pose=({target[0]:+.3f},{target[1]:+.3f},{target[2]:+.3f}) "
            f"theta={theta:+.3f} omega={omega:+.2f} "
            f"aim=({yaw:+.3f},{pitch:+.3f}) meas=({self.yaw_meas:+.3f},{self.pitch_meas:+.3f}) "
            f"err=({math.degrees(err_yaw):+.2f},{math.degrees(err_pitch):+.2f})deg "
            f"aligned={aligned} fire={fire} shots={self.bullets} hits={self.hits}{extra}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = AimNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
