"""Multi-channel alert system with cooldown and snapshot delivery."""

from __future__ import annotations

import smtplib
import time
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import requests

import config
from modules.gps_tracking import get_current_location
from modules.logger import logger

if TYPE_CHECKING:
    import numpy as np

_last_alert_times: dict[str, float] = {}
_alert_count = 0


def get_alerts_sent_count() -> int:
    """Return number of alerts sent in this session."""
    return _alert_count


def _cooldown_active(alert_key: str) -> bool:
    """Return True if alert type is still in cooldown window."""
    now = time.time()
    last = _last_alert_times.get(alert_key, 0)
    if now - last < config.ALERT_COOLDOWN_SECONDS:
        logger.info(
            "Alert '%s' skipped (cooldown %ss)",
            alert_key,
            config.ALERT_COOLDOWN_SECONDS,
        )
        return True
    _last_alert_times[alert_key] = now
    return False


def play_alarm() -> None:
    """Play local alarm sound if available."""
    if not config.ALARM_SOUND_PATH.exists():
        logger.warning("Alarm sound file not found: %s", config.ALARM_SOUND_PATH)
        return
    try:
        from playsound import playsound

        playsound(str(config.ALARM_SOUND_PATH))
        logger.info("Alarm sound played")
    except Exception as exc:
        logger.error("Alarm sound failed: %s", exc)


def _send_email(
    subject: str,
    body: str,
    snapshot_path: str | None,
    receiver: str | None = None,
) -> None:
    """Send email alert via Gmail SMTP."""
    if not config.EMAIL_USER or not config.EMAIL_PASS:
        logger.warning("Email credentials not configured; skipping email alert")
        return

    receiver_email = receiver or config.EMAIL_USER
    msg = MIMEMultipart()
    msg["From"] = config.EMAIL_USER
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if snapshot_path and Path(snapshot_path).exists():
        with open(snapshot_path, "rb") as file:
            attachment = MIMEApplication(file.read(), Name=Path(snapshot_path).name)
            attachment["Content-Disposition"] = (
                f'attachment; filename="{Path(snapshot_path).name}"'
            )
            msg.attach(attachment)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(config.EMAIL_USER, config.EMAIL_PASS)
            server.sendmail(config.EMAIL_USER, receiver_email, msg.as_string())
        logger.info("Email alert sent: %s", subject)
    except smtplib.SMTPException as exc:
        logger.error("Email alert failed: %s", exc)


def _send_telegram(
    alert_type: str,
    confidence: float | None,
    timestamp: str,
    snapshot_path: str | None,
    maps_link: str,
) -> None:
    """Send Telegram text and photo alert."""
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured; skipping Telegram alert")
        return

    conf_text = f"{confidence * 100:.1f}%" if confidence is not None else "N/A"
    text = (
        "🚨 SECURITY ALERT\n\n"
        f"Type: {alert_type}\n"
        f"Confidence: {conf_text}\n\n"
        f"Time: {timestamp}\n\n"
        f"Location:\n{maps_link}"
    )

    try:
        text_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(
            text_url,
            data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
            },
            timeout=30,
        )
        response.raise_for_status()
        logger.info("Telegram text alert sent")

        if snapshot_path and Path(snapshot_path).exists():
            photo_url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendPhoto"
            with open(snapshot_path, "rb") as photo:
                photo_response = requests.post(
                    photo_url,
                    data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": text},
                    files={"photo": photo},
                    timeout=30,
                )
                photo_response.raise_for_status()
            logger.info("Telegram photo alert sent")
    except requests.RequestException as exc:
        logger.error("Telegram alert failed: %s", exc)


def send_alert(
    alert_type: str,
    message: str,
    frame: "np.ndarray | None" = None,
    confidence: float | None = None,
    snapshot_path: str | None = None,
    cooldown_key: str | None = None,
) -> bool:
    """
    Send email, Telegram, and sound alerts with cooldown protection.

    Returns True if alert was dispatched, False if skipped or failed.
    """
    global _alert_count
    key = cooldown_key or alert_type
    if _cooldown_active(key):
        return False

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    location = get_current_location()
    maps_link = location.maps_link

    if snapshot_path is None and frame is not None:
        from modules.database import save_snapshot

        snapshot_path = save_snapshot(frame)

    play_alarm()

    subject = f"SECURITY ALERT | {alert_type} | {timestamp}"
    email_body = (
        f"ALERT: {alert_type}\n\n"
        f"MESSAGE:\n{message}\n\n"
        f"Confidence: {confidence}\n"
        f"Time: {timestamp}\n"
        f"Location: {location.latitude}, {location.longitude}\n"
        f"Maps: {maps_link}\n"
    )

    try:
        _send_email(subject, email_body, snapshot_path)
        _send_telegram(alert_type, confidence, timestamp, snapshot_path, maps_link)
        _alert_count += 1
        logger.info("Alert dispatched: %s", alert_type)
        return True
    except Exception as exc:
        logger.error("Alert dispatch error: %s", exc)
        return False
