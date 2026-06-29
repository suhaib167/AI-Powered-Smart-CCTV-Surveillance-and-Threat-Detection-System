"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Camera
CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", "0"))

# YOLO model
MODEL_PATH: Path = BASE_DIR / "models" / "best.pt"
MODEL_URL: str = os.getenv(
    "MODEL_URL",
    "https://github.com/mohamed-suhaib-ai/Weapons-and-Knives-Detector-with-YOLOv8/"
    "releases/download/model/best.pt",
)
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))

# Paths
DATABASE_PATH: Path = BASE_DIR / "database" / "events.db"
KNOWN_FACES_DIR: Path = BASE_DIR / "known_faces"
SNAPSHOTS_DIR: Path = BASE_DIR / "snapshots"
EVIDENCE_DIR: Path = BASE_DIR / "evidence"
UPLOADS_DIR: Path = BASE_DIR / "uploads"
LOGS_DIR: Path = BASE_DIR / "logs"
LOG_FILE: Path = LOGS_DIR / "app.log"
ALARM_SOUND_PATH: Path = BASE_DIR / "alert.mp3"

# Alert system
ALERT_COOLDOWN_SECONDS: int = int(os.getenv("ALERT_COOLDOWN_SECONDS", "60"))
RECORDING_DURATION_SECONDS: int = int(os.getenv("RECORDING_DURATION_SECONDS", "10"))
RECORDING_FPS: int = int(os.getenv("RECORDING_FPS", "20"))

# Face recognition
FACE_DISTANCE_THRESHOLD: float = float(os.getenv("FACE_DISTANCE_THRESHOLD", "0.35"))

# GPS (static fallback when hardware GPS unavailable)
DEFAULT_LATITUDE: float = float(os.getenv("DEFAULT_LATITUDE", "13.0827"))
DEFAULT_LONGITUDE: float = float(os.getenv("DEFAULT_LONGITUDE", "80.2707"))

# Credentials (never hardcode secrets)
EMAIL_USER: str = os.getenv("EMAIL_USER", "")
EMAIL_PASS: str = os.getenv("EMAIL_PASS", "")
TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# Flask
SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")

# Threat classes for behavior analysis
THREAT_CLASSES: frozenset[str] = frozenset(
    {"gun", "knife", "weapon", "pistol", "rifle", "blade"}
)

# Motion detection (optional)
MOTION_DETECTION_ENABLED: bool = os.getenv(
    "MOTION_DETECTION_ENABLED", "true"
).lower() in ("1", "true", "yes")
MOTION_THRESHOLD: int = int(os.getenv("MOTION_THRESHOLD", "5000"))
