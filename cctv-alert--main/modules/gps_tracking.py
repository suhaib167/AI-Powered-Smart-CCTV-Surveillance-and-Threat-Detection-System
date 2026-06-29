"""GPS location helpers for alert geotagging."""

from __future__ import annotations

from dataclasses import dataclass

import config
from modules.logger import logger


@dataclass
class GPSCoordinates:
    """Latitude/longitude pair with maps link."""

    latitude: float
    longitude: float

    @property
    def maps_link(self) -> str:
        return f"https://maps.google.com/?q={self.latitude},{self.longitude}"


def get_current_location() -> GPSCoordinates:
    """
    Return current GPS coordinates.

    Uses environment defaults until a hardware GPS source is integrated.
    """
    try:
        lat = config.DEFAULT_LATITUDE
        lon = config.DEFAULT_LONGITUDE
        logger.debug("GPS location: %s, %s", lat, lon)
        return GPSCoordinates(latitude=lat, longitude=lon)
    except Exception as exc:
        logger.error("GPS lookup failed: %s", exc)
        return GPSCoordinates(
            latitude=config.DEFAULT_LATITUDE,
            longitude=config.DEFAULT_LONGITUDE,
        )
