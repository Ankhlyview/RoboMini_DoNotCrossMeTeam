"""Unit tests for the HSV light-bar detector (no ROS required)."""

import cv2
import numpy as np
import pytest

from robomini_vision.detector import RuneDetector

BLUE = (255, 159, 0)      # BGR of the blue light bars in the simulation
RED = (71, 89, 252)       # BGR of the red light bars in the simulation


def _blank(width=640, height=480):
    return np.zeros((height, width, 3), dtype=np.uint8)


def _bar(img, cx, cy, w, h, color):
    cv2.rectangle(img, (int(cx - w / 2), int(cy - h / 2)),
                  (int(cx + w / 2), int(cy + h / 2)), color, -1)


def _pending_cross(img, cx, cy, color):
    # radial pair (vertical) + tangential pair (horizontal)
    _bar(img, cx, cy - 37, 12, 24, color)
    _bar(img, cx, cy + 37, 12, 24, color)
    _bar(img, cx - 37, cy, 24, 12, color)
    _bar(img, cx + 37, cy, 24, 12, color)


def _active_pair(img, cx, cy, color):
    _bar(img, cx - 37, cy, 24, 12, color)
    _bar(img, cx + 37, cy, 24, 12, color)


def test_pending_blue_cross():
    img = _blank()
    _pending_cross(img, 320, 240, BLUE)
    det = RuneDetector("blue").detect(img)
    assert len(det) == 1
    assert det[0].state == "pending"
    assert det[0].n_bars == 4
    assert det[0].u == pytest.approx(320, abs=3)
    assert det[0].v == pytest.approx(240, abs=3)


def test_active_blue_pair():
    img = _blank()
    _active_pair(img, 320, 240, BLUE)
    det = RuneDetector("blue").detect(img)
    assert len(det) == 1
    assert det[0].state == "active"
    assert det[0].n_bars == 2


def test_red_bars_and_field_line():
    img = _blank()
    _pending_cross(img, 320, 240, RED)
    # pure red field marking: long thin line, G channel ~0
    cv2.rectangle(img, (20, 400), (620, 404), (0, 0, 255), -1)
    det = RuneDetector("red").detect(img)
    assert len(det) == 1
    assert det[0].state == "pending"
    assert det[0].v == pytest.approx(240, abs=5)


def test_blue_field_line_is_ignored():
    img = _blank()
    cv2.rectangle(img, (20, 400), (620, 404), (255, 0, 0), -1)  # pure blue
    assert RuneDetector("blue").detect(img) == []

