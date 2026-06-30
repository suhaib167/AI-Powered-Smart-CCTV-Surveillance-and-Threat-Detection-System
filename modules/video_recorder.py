"""Video evidence recorder for threat events."""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import cv2

import config
from modules.logger import logger

if TYPE_CHECKING:
    import numpy as np

_buffer: deque = deque(maxlen=config.RECORDING_FPS * config.RECORDING_DURATION_SECONDS)
_recording_lock = threading.Lock()
_is_recording = False


def add_frame(frame: "np.ndarray") -> None:
    """Buffer frames for evidence recording."""
    _buffer.append(frame.copy())


def record_evidence() -> str | None:
    """
    Save buffered frames as a 10-second MP4 in evidence/.

    Returns the saved video path or None on failure.
    """
    global _is_recording

    with _recording_lock:
        if _is_recording or len(_buffer) < 5:
            return None
        _is_recording = True

    config.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    filename = datetime.now().strftime("%Y%m%d_%H%M%S_evidence.mp4")
    output_path = config.EVIDENCE_DIR / filename

    try:
        frames = list(_buffer)
        if not frames:
            return None

        height, width = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(output_path),
            fourcc,
            config.RECORDING_FPS,
            (width, height),
        )
        for frame in frames:
            writer.write(frame)
        writer.release()
        logger.info("Evidence video saved: %s", output_path)
        return str(output_path)
    except Exception as exc:
        logger.error("Evidence recording failed: %s", exc)
        return None
    finally:
        with _recording_lock:
            _is_recording = False
