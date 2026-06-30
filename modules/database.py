"""SQLite database helpers for surveillance event storage."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import config
from modules.logger import logger


def _connect() -> sqlite3.Connection:
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    """Create the events table if it does not exist."""
    try:
        with _connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    confidence REAL,
                    timestamp TEXT NOT NULL,
                    image_path TEXT,
                    video_path TEXT,
                    latitude REAL,
                    longitude REAL
                )
                """
            )
            conn.commit()
        logger.info("Database initialized at %s", config.DATABASE_PATH)
    except sqlite3.Error as exc:
        logger.error("Database initialization failed: %s", exc)
        raise


def insert_event(
    event_type: str,
    confidence: float | None = None,
    image_path: str | None = None,
    video_path: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    timestamp: str | None = None,
) -> int | None:
    """Insert a surveillance event and return its row id."""
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with _connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (
                    event_type, confidence, timestamp,
                    image_path, video_path, latitude, longitude
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    confidence,
                    ts,
                    image_path,
                    video_path,
                    latitude,
                    longitude,
                ),
            )
            conn.commit()
            event_id = cursor.lastrowid
        logger.info(
            "Event stored: id=%s type=%s confidence=%s",
            event_id,
            event_type,
            confidence,
        )
        return event_id
    except sqlite3.Error as exc:
        logger.error("Failed to insert event: %s", exc)
        return None


def fetch_events(
    date_filter: str | None = None,
    event_type: str | None = None,
    min_confidence: float | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Fetch events with optional filters."""
    query = "SELECT * FROM events WHERE 1=1"
    params: list[Any] = []

    if date_filter:
        query += " AND timestamp LIKE ?"
        params.append(f"{date_filter}%")
    if event_type:
        query += " AND event_type LIKE ?"
        params.append(f"%{event_type}%")
    if min_confidence is not None:
        query += " AND confidence >= ?"
        params.append(min_confidence)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    try:
        with _connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        logger.error("Failed to fetch events: %s", exc)
        return []


def get_statistics() -> dict[str, int]:
    """Return aggregate statistics for the dashboard."""
    stats = {
        "total_events": 0,
        "threats_detected": 0,
        "known_faces": 0,
        "unknown_faces": 0,
        "alerts_sent": 0,
    }
    try:
        with _connect() as conn:
            stats["total_events"] = conn.execute(
                "SELECT COUNT(*) FROM events"
            ).fetchone()[0]
            stats["threats_detected"] = conn.execute(
                """
                SELECT COUNT(*) FROM events
                WHERE event_type LIKE '%threat%'
                   OR event_type LIKE '%object%'
                   OR event_type LIKE '%intrusion%'
                   OR event_type LIKE '%motion%'
                """
            ).fetchone()[0]
            stats["known_faces"] = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type LIKE '%known_face%'"
            ).fetchone()[0]
            stats["unknown_faces"] = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type LIKE '%unknown_face%'"
            ).fetchone()[0]
            stats["alerts_sent"] = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type LIKE '%alert%'"
            ).fetchone()[0]
    except sqlite3.Error as exc:
        logger.error("Failed to fetch statistics: %s", exc)
    return stats


def snapshot_filename() -> str:
    """Generate snapshot filename: YYYYMMDD_HHMMSS.jpg."""
    return datetime.now().strftime("%Y%m%d_%H%M%S.jpg")


def save_snapshot(frame, snapshots_dir: Path | None = None) -> str | None:
    """Save a frame snapshot and return the file path."""
    import cv2

    directory = snapshots_dir or config.SNAPSHOTS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    filename = snapshot_filename()
    path = directory / filename
    try:
        cv2.imwrite(str(path), frame)
        logger.info("Snapshot saved: %s", path)
        return str(path)
    except Exception as exc:
        logger.error("Failed to save snapshot: %s", exc)
        return None
