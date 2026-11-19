"""Unit tests for the geometry / ballistics helpers (no ROS required).

Run from the package root:

    cd members/Algorithm_A/code/ros2_ws/src/robomini_vision
    /usr/bin/python3 -m pytest -q
"""

import math

import numpy as np
import pytest

from robomini_vision import geometry as g

K = [1108.5118865966797, 0.0, 640.0,
     0.0, 1108.5120105743408, 360.0,
     0.0, 0.0, 1.0]


@pytest.mark.parametrize("side", ["blue", "red"])
def test_target_point_on_circle(side):
    theta = 0.4
    point = g.target_point(side, theta)
    axis = g.geometry(side)["axis"]
    radius = math.hypot(point[0] - axis[0], point[2] - axis[2])
    assert radius == pytest.approx(g.RUNE_RADIUS, abs=1e-9)
    assert point[1] == pytest.approx(g.geometry(side)["plane_y"])
    assert g.point_to_theta(side, point) == pytest.approx(theta, abs=1e-9)


@pytest.mark.parametrize("side", ["blue", "red"])
@pytest.mark.parametrize("yaw,pitch", [(0.0, 0.0), (0.2, 0.3), (-0.4, 0.1)])
def test_pixel_plane_round_trip(side, yaw, pitch):
    point = g.target_point(side, 0.4)
    uv = g.world_to_pixel(point, K, side, yaw, pitch)
    assert uv is not None
    u, v, depth = uv
    assert depth > 0.0
    recovered = g.pixel_to_plane(u, v, K, side, yaw, pitch)
    assert recovered is not None
    np.testing.assert_allclose(recovered, point, atol=1e-9)


@pytest.mark.parametrize("side", ["blue", "red"])
def test_aim_solution_hits_target(side):
    speed = 12.0
    target = g.target_point(side, 0.5)
    yaw, pitch = g.aim_at(side, target, speed)

    assert -g.YAW_LIMIT <= yaw <= g.YAW_LIMIT
    assert g.PITCH_MIN <= pitch <= g.PITCH_MAX

    muzzle = g.muzzle_position(side, yaw, pitch)
    base_yaw = g.geometry(side)["base_yaw"]
    direction = g.rot_z(base_yaw + yaw) @ g.rot_x(pitch) @ np.array([0.0, 1.0, 0.0])
    horizontal = math.hypot(target[0] - muzzle[0], target[1] - muzzle[1])
    flight = horizontal / (speed * math.cos(pitch))
    hit = muzzle + direction * speed * flight
    hit[2] -= 0.5 * g.GRAVITY * flight * flight
    np.testing.assert_allclose(hit, target, atol=1e-6)


def test_snap_rejects_wrong_radius():
    # A point on the plane but far from the rune circle.
    point = np.array([0.0, g.geometry("blue")["plane_y"], 0.4])
    _, _, residual = g.snap_to_rune("blue", point)
    assert residual > 0.1


def test_target_quaternion_is_rotation():
    q = g.target_quaternion("blue", 0.7)
    rotation = g.quat_to_matrix(q)
    np.testing.assert_allclose(rotation @ rotation.T, np.eye(3), atol=1e-12)
    assert np.linalg.det(rotation) == pytest.approx(1.0, abs=1e-9)
