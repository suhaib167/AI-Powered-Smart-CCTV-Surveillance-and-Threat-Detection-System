"""
AI Smart CCTV Surveillance System — Flask application entry point.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from pathlib import Path

import cv2
from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

import config
from modules.alert_system import get_alerts_sent_count, send_alert
from modules.behavior_analysis import detect_behavior, is_intrusion
from modules.database import (
    fetch_events,
    get_statistics,
    initialize_database,
    insert_event,
    save_snapshot,
)
from modules.face_recognition import draw_face_labels, recognize_faces
from modules.gps_tracking import get_current_location
from modules.logger import logger
from modules.motion_detection import detect_motion
from modules.object_detection import detect_objects
from modules.video_recorder import add_frame, record_evidence

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["UPLOAD_FOLDER"] = str(config.UPLOADS_DIR)

from ultralytics import YOLO

model = YOLO("yolov8n.pt")

camera = None
_session_stats = {
    "detections": 0,
    "threats": 0,
    "known_faces": 0,
    "unknown_faces": 0,
}


def _ensure_directories() -> None:
    """Create required runtime directories."""
    for directory in (
        config.UPLOADS_DIR,
        config.SNAPSHOTS_DIR,
        config.EVIDENCE_DIR,
        config.LOGS_DIR,
        config.KNOWN_FACES_DIR,
        config.MODEL_PATH.parent,
        config.DATABASE_PATH.parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def async_send_alert(**kwargs) -> None:
    """Dispatch alerts on a background thread."""
    thread = threading.Thread(target=send_alert, kwargs=kwargs, daemon=True)
    thread.start()


def _process_frame(frame):
    """Run full surveillance pipeline on a single frame."""
    global _session_stats
    location = get_current_location()
    add_frame(frame)

    motion = detect_motion(frame)
    detections = detect_objects(frame)
    detection_labels = [d.label for d in detections]

    for det in detections:
        _session_stats["detections"] += 1
        snapshot = save_snapshot(frame)
        insert_event(
            event_type=f"object:{det.label}",
            confidence=det.confidence,
            image_path=snapshot,
            latitude=location.latitude,
            longitude=location.longitude,
        )

    faces = recognize_faces(frame)
    draw_face_labels(frame, faces)

    for face in faces:
        snapshot = save_snapshot(frame)
        if face.is_known:
            _session_stats["known_faces"] += 1
            insert_event(
                event_type=f"known_face:{face.name}",
                confidence=1.0 - (face.distance or 0),
                image_path=snapshot,
                latitude=location.latitude,
                longitude=location.longitude,
            )
        else:
            _session_stats["unknown_faces"] += 1
            insert_event(
                event_type="unknown_face",
                confidence=None,
                image_path=snapshot,
                latitude=location.latitude,
                longitude=location.longitude,
            )
            async_send_alert(
                alert_type="Unknown Person",
                message=f"Unknown person detected: {face.name}",
                frame=frame,
                snapshot_path=snapshot,
                cooldown_key="unknown_face",
            )
            insert_event(
                event_type="alert:unknown_face",
                image_path=snapshot,
                latitude=location.latitude,
                longitude=location.longitude,
            )

    status = detect_behavior(detection_labels)
    intrusion = is_intrusion(motion, bool(detections))

    if status == "threat" or intrusion:
        _session_stats["threats"] += 1
        snapshot = save_snapshot(frame)
        video_path = record_evidence()
        threat_type = "intrusion" if intrusion else "threat"
        max_conf = max((d.confidence for d in detections), default=None)

        insert_event(
            event_type=f"{threat_type}:detected",
            confidence=max_conf,
            image_path=snapshot,
            video_path=video_path,
            latitude=location.latitude,
            longitude=location.longitude,
        )

        threading.Thread(
            target=send_alert,
            kwargs={
                "alert_type": threat_type.title(),
                "message": "Dangerous object or intrusion detected!",
                "frame": frame,
                "confidence": max_conf,
                "snapshot_path": snapshot,
                "cooldown_key": "threat",
            },
            daemon=True,
        ).start()

        insert_event(
            event_type=f"alert:{threat_type}",
            confidence=max_conf,
            image_path=snapshot,
            video_path=video_path,
            latitude=location.latitude,
            longitude=location.longitude,
        )

    if motion and not detections:
        insert_event(
            event_type="motion",
            image_path=save_snapshot(frame),
            latitude=location.latitude,
            longitude=location.longitude,
        )

    return frame


def gen_frames():
    """MJPEG stream generator for live surveillance feed."""
    global camera
    while camera is not None and camera.isOpened():
        try:
            success, frame = camera.read()
            if not success:
                logger.warning("Failed to read camera frame")
                break

            frame = _process_frame(frame)
            ret, buffer = cv2.imencode(".jpg", frame)
            if not ret:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
        except Exception as exc:
            logger.error("Frame processing error: %s", exc)
            break


@app.route("/")
def index():
    """Main surveillance dashboard."""
    stats = get_statistics()
    stats["session_detections"] = _session_stats["detections"]
    stats["session_alerts"] = get_alerts_sent_count()
    return render_template("dashboard.html", stats=stats)


@app.route("/history")
def history():
    """Detection history page with filters."""
    date_filter = request.args.get("date", "")
    event_type = request.args.get("type", "")
    min_confidence = request.args.get("confidence", "")
    conf_value = float(min_confidence) if min_confidence else None

    events = fetch_events(
        date_filter=date_filter or None,
        event_type=event_type or None,
        min_confidence=conf_value,
    )
    return render_template(
        "history.html",
        events=events,
        date_filter=date_filter,
        event_type=event_type,
        min_confidence=min_confidence,
    )


@app.route("/start_camera", methods=["POST"])
def start_camera():
    """Start live webcam capture."""
    global camera
    try:
        if camera is not None:
            camera.release()
        camera = cv2.VideoCapture(config.CAMERA_INDEX)
        if not camera.isOpened():
            logger.error("Camera unavailable at index %s", config.CAMERA_INDEX)
            return jsonify({"error": "Camera unavailable"}), 503
        logger.info("Camera started at index %s", config.CAMERA_INDEX)
    except Exception as exc:
        logger.error("Failed to start camera: %s", exc)
    return _redirect_home()


@app.route("/upload_video", methods=["POST"])
def upload_video():
    """Process uploaded video file as camera source."""
    global camera
    video = request.files.get("video")
    if not video or not video.filename:
        return _redirect_home()

    try:
        video_path = config.UPLOADS_DIR / video.filename
        video.save(str(video_path))
        if camera is not None:
            camera.release()
        camera = cv2.VideoCapture(str(video_path))
        if not camera.isOpened():
            logger.error("Failed to open uploaded video: %s", video_path)
        else:
            logger.info("Video source loaded: %s", video_path)
    except Exception as exc:
        logger.error("Video upload failed: %s", exc)
    return _redirect_home()


@app.route("/video_feed")
def video_feed():
    """Live MJPEG video stream."""
    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/snapshots/<path:filename>")
def serve_snapshot(filename: str):
    """Serve snapshot images."""
    return send_from_directory(config.SNAPSHOTS_DIR, filename)


@app.route("/evidence/<path:filename>")
def serve_evidence(filename: str):
    """Serve evidence video files."""
    return send_from_directory(config.EVIDENCE_DIR, filename)


# REST API endpoints
@app.route("/api/events")
def api_events():
    """Return filtered events as JSON."""
    events = fetch_events(
        date_filter=request.args.get("date"),
        event_type=request.args.get("type"),
        min_confidence=float(request.args["confidence"])
        if request.args.get("confidence")
        else None,
    )
    return jsonify(events)


@app.route("/api/stats")
def api_stats():
    """Return dashboard statistics."""
    stats = get_statistics()
    stats.update(_session_stats)
    stats["alerts_sent_session"] = get_alerts_sent_count()
    return jsonify(stats)


@app.route("/api/health")
def api_health():
    """System health monitoring endpoint."""
    model_exists = config.MODEL_PATH.exists()
    camera_ok = camera is not None and camera.isOpened() if camera else False
    db_ok = config.DATABASE_PATH.exists()

    return jsonify(
        {
            "status": "healthy" if model_exists and db_ok else "degraded",
            "timestamp": datetime.now().isoformat(),
            "camera_active": camera_ok,
            "model_loaded": model_exists,
            "database_ready": db_ok,
            "modules": {
                "object_detection": model_exists,
                "face_recognition": config.KNOWN_FACES_DIR.exists(),
                "motion_detection": config.MOTION_DETECTION_ENABLED,
            },
        }
    )


def _redirect_home():
    from flask import redirect

    return redirect("/")


if __name__ == "__main__":
    _ensure_directories()
    initialize_database()
    logger.info("AI Smart CCTV Surveillance System starting")
    app.run(debug=config.DEBUG, host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
