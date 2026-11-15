"""
TokenShield — Geographic Mathematics: Haversine Distance & Velocity
====================================================================
Computes great-circle distance between two geographic coordinates on Earth
using spherical trigonometry (Haversine formula), and calculates equivalent
travel velocity in km/h.
"""

import math
from typing import Tuple


EARTH_RADIUS_KM = 6371.0088


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between (lat1, lon1) and (lat2, lon2) in kilometers.
    """
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2.0) ** 2 +
         math.cos(p1) * math.cos(p2) * (math.sin(delta_lon / 2.0) ** 2))
    a = min(1.0, max(0.0, a))  # Clamp for float precision
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_KM * c


def calculate_travel_velocity(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    elapsed_seconds: float
) -> Tuple[float, float]:
    """
    Returns (distance_km, speed_kmh).
    """
    dist_km = haversine_distance_km(lat1, lon1, lat2, lon2)
    safe_elapsed = max(float(elapsed_seconds), 0.5)  # Avoid division by zero
    speed_kmh = (dist_km / safe_elapsed) * 3600.0
    return round(dist_km, 2), round(speed_kmh, 2)
