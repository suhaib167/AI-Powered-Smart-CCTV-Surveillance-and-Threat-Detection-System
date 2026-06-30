"""Face recognition using DeepFace with known_faces/ auto-loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2

import config
from modules.logger import logger

if TYPE_CHECKING:
    import numpy as np

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class FaceResult:
    """Face recognition outcome."""

    name: str
    is_known: bool
    distance: float | None = None


def load_face_database(db_path: Path | None = None) -> Path:
    """Ensure known_faces directory exists and return its path."""
    path = db_path or config.KNOWN_FACES_DIR
    path.mkdir(parents=True, exist_ok=True)
    count = sum(
        1
        for f in path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    logger.info("Known faces database: %s (%d images)", path, count)
    return path


def _identity_to_name(identity_path: str) -> str:
    """Extract person name from identity file path."""
    return Path(identity_path).stem.replace("_", " ").title()


def recognize_faces(
    frame: "np.ndarray",
    db_path: Path | None = None,
    threshold: float | None = None,
) -> list[FaceResult]:
    """
    Recognize faces in frame against known_faces/.

    Returns known and unknown person results. Unknown persons should trigger alerts.
    """
    results: list[FaceResult] = []
    database_path = load_face_database(db_path)
    distance_threshold = threshold or config.FACE_DISTANCE_THRESHOLD
    temp_path = config.BASE_DIR / "temp_frame.jpg"

    try:
        from deepface import DeepFace

        cv2.imwrite(str(temp_path), frame)

        extracted = DeepFace.extract_faces(
            img_path=str(temp_path),
            enforce_detection=False,
            detector_backend="opencv",
        )
        if not extracted:
            return results

        matches = DeepFace.find(
            img_path=str(temp_path),
            db_path=str(database_path),
            model_name="VGG-Face",
            enforce_detection=False,
            distance_metric="cosine",
            silent=True,
        )

        if matches and len(matches[0]) > 0:
            seen: set[str] = set()
            for _, row in matches[0].iterrows():
                distance = float(row.get("distance", 1.0))
                identity = str(row.get("identity", ""))
                name = _identity_to_name(identity)
                is_known = distance <= distance_threshold

                if name in seen:
                    continue
                seen.add(name)

                results.append(
                    FaceResult(name=name, is_known=is_known, distance=distance)
                )
                status = "Known" if is_known else "Unknown"
                logger.info("Face: %s | %s Person | distance=%.3f", name, status, distance)
        else:
            results.append(FaceResult(name="Unknown Person", is_known=False))
            logger.info("Face: Unknown Person detected (no match in database)")
    except Exception as exc:
        logger.error("Face recognition error: %s", exc)
        results.append(FaceResult(name="Unknown Person", is_known=False))
    finally:
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except OSError:
                pass

    return results


def draw_face_labels(frame: "np.ndarray", faces: list[FaceResult]) -> None:
    """Draw face recognition labels on the frame."""
    y_offset = 30
    for face in faces:
        color = (0, 255, 0) if face.is_known else (0, 0, 255)
        label = f"{'Known' if face.is_known else 'Unknown'}: {face.name}"
        cv2.putText(
            frame,
            label,
            (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )
        y_offset += 30
