"""
Pytest tests for bl531_api
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from bl531.bl531_api import bl531  # noqa: E402, I100 - import after path setup


def test_count_with_diode():
    result = bl531.count(detectors=["diode"], num=1)

    assert result.run_uid is not None
    assert result.plan_name is not None
    assert result.timestamp is not None


def test_count_with_diode_and_det():
    result = bl531.count(detectors=["diode", "det"], num=1)

    assert result.run_uid is not None


def test_scan_with_diode():
    result = bl531.scan(
        detectors=["diode"],
        motor="hexapod_motor_Ty",
        start=0,
        stop=0.3,
        num=5,
    )

    assert result.run_uid is not None


def test_invalid_detector_is_rejected():
    with pytest.raises(ValueError):
        bl531.scan(
            detectors=["non-existing"],
            motor="hexapod_motor_Ry",
            start=-0.5,
            stop=0.5,
            num=5,
        )


def test_scan_with_multiple_detectors():
    result = bl531.scan(
        detectors=["diode", "det"],
        motor="hexapod_motor_Ry",
        start=-0.5,
        stop=0.5,
        num=5,
    )

    assert result.run_uid is not None


if __name__ == "__main__":
    pytest.main([__file__])
