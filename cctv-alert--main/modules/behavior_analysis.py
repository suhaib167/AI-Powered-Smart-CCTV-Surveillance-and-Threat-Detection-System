"""Behavior and threat analysis from detected object classes."""

from __future__ import annotations

import config
from modules.logger import logger


def detect_behavior(classes: list[str]) -> str:
    """
    Analyze detected classes and return threat status.

    Returns:
        'threat' if a dangerous class is detected, otherwise 'safe'.
    """
    normalized = {cls.lower().strip() for cls in classes}
    logger.debug("Detected classes: %s", normalized)

    if normalized & config.THREAT_CLASSES:
        return "threat"
    return "safe"


def is_intrusion(motion_detected: bool, object_detected: bool) -> bool:
    """Flag intrusion when motion and object detection coincide."""
    return motion_detected and object_detected
