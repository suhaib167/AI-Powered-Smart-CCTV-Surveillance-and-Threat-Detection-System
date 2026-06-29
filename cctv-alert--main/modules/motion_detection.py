"""Motion detection using background subtraction."""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2

import config
from modules.logger import logger

if TYPE_CHECKING:
    import numpy as np

_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=True)
_motion_detected = False


def detect_motion(frame: "np.ndarray") -> bool:
    """
    Detect significant motion in the frame.

    Returns True when motion area exceeds configured threshold.
    """
    global _motion_detected
    if not config.MOTION_DETECTION_ENABLED:
        return False

    try:
        fg_mask = _subtractor.apply(frame)
        _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion_area = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 500)
        _motion_detected = motion_area > config.MOTION_THRESHOLD

        if _motion_detected:
            cv2.putText(
                frame,
                "MOTION DETECTED",
                (10, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 165, 255),
                2,
            )
            logger.debug("Motion detected: area=%.0f", motion_area)
        return _motion_detected
    except Exception as exc:
        logger.error("Motion detection error: %s", exc)
        return False
