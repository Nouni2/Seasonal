import os
import sys
import math
import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.time_struct import Time


def parabolic_delta_t(year: float) -> float:
    t = (year - 1820.0) / 100.0
    return -20 + 32 * t * t


def test_delta_t_uses_parabolic_model_at_2050_boundary():
    t = Time.from_gregorian(2050, 1, 1, 12, 0, 0)
    expected = parabolic_delta_t(2050.0)
    assert t.delta_t == pytest.approx(expected, abs=0.1)


def test_delta_t_far_future_continuity_at_2150():
    t = Time.from_gregorian(2150, 1, 1, 12, 0, 0)
    expected = parabolic_delta_t(2150.0)
    assert t.delta_t == pytest.approx(expected, abs=0.1)
