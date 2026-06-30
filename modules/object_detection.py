"""YOLO-based object detection with bounding box visualization."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import requests

import config
from modules.logger import logger

if TYPE_CHECKING:
    import numpy as np
    from ultralytics import YOLO

_yolo_model: "YOLO | None" = None


@dataclass
class Detection:
    """Single object detection result."""

    label: str
    confidence: float
    bbox: tuple[int, int, int, int]


def _download_model() -> None:
    """Download YOLO weights if missing."""
    config.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Model not found. Downloading from %s", config.MODEL_URL)
    try:
        response = requests.get(config.MODEL_URL, timeout=120)
        response.raise_for_status()
        with open(config.MODEL_PATH, "wb") as file:
            file.write(response.content)
        logger.info("Model downloaded to %s", config.MODEL_PATH)
    except requests.RequestException as exc:
        logger.error("Model download failed: %s", exc)
        raise


def load_model() -> "YOLO":
    """Load or return cached YOLO model."""
    global _yolo_model
    if _yolo_model is not None:
        return _yolo_model

    from ultralytics import YOLO

    if not os.path.exists(config.MODEL_PATH):
        _download_model()

    try:
        _yolo_model = YOLO(str(config.MODEL_PATH))
        logger.info("YOLO model loaded from %s", config.MODEL_PATH)
    except Exception as exc:
        logger.error("Failed to load YOLO model: %s", exc)
        raise
    return _yolo_model


def detect_objects(frame: "np.ndarray") -> list[Detection]:
    """
    Run YOLO inference, draw labels on frame, and return detections.

    Each detection includes object name, confidence percentage, and bbox.
    """
    detections: list[Detection] = []
    try:
        model = load_model()
        results = model(frame, verbose=False)[0]

        for box in results.boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            label = model.names[cls_id]

            if confidence < config.CONFIDENCE_THRESHOLD:
                continue

            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
            conf_pct = confidence * 100

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(
                frame,
                f"{label} {conf_pct:.1f}%",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )

            detections.append(
                Detection(label=label, confidence=confidence, bbox=(x1, y1, x2, y2))
            )
            logger.info(
                "Detection: %s | Confidence: %.1f%% | BBox: %s",
                label,
                conf_pct,
                (x1, y1, x2, y2),
            )
    except Exception as exc:
        logger.error("Object detection error: %s", exc)
    return detections
