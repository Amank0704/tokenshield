"""
TokenShield — Signal 6: Geographic Impossibility (Impossible Travel Detector)
=============================================================================
Calculates real physical displacement and equivalent velocity between
subsequent requests within a session.

Physics Thresholds:
  - Commercial aviation cruising velocity: ~800–900 km/h
  - > 900 km/h: IMPOSSIBLE_TRAVEL (Critical Anomaly Score 0.95)
  - > 500 km/h: SUSPICIOUS_TRAVEL (Score 0.65)
  - Inter-country jump in < 300s: SUSPICIOUS_RELOCATION (Score 0.75)
"""

import time
import logging
import threading
from collections import defaultdict
from typing import Tuple, Dict, Any, Optional

from engine.geo.haversine import calculate_travel_velocity
from engine.geo.ip_locator import resolve_ip_location

log = logging.getLogger("ts.geo.travel")

SPEED_IMPOSSIBLE_KMH = 900.0   # Beyond Mach 0.85 commercial flight
SPEED_HIGH_SUSPICIOUS = 600.0  # High-speed transit anomaly


class ImpossibleTravelDetector:
    def __init__(self):
        # session_id -> { "lat": float, "lon": float, "city": str, "country": str, "ip": str, "timestamp": float }
        self._session_anchors: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._lock = threading.Lock()

    def evaluate_travel(self, session_id: str, current_ip: str) -> Tuple[float, Dict[str, Any]]:
        """
        Evaluates physical travel velocity between the previous request and the current request.
        Returns:
            (anomaly_score [0.0, 1.0], metadata_dict)
        """
        if not session_id or session_id == "anonymous":
            loc = resolve_ip_location(current_ip)
            return 0.0, {"verdict": "anonymous_request", "current_location": loc}

        current_loc = resolve_ip_location(current_ip)
        now = time.time()

        with self._lock:
            prev_loc = self._session_anchors.get(session_id)
            # Update anchor for next evaluation
            self._session_anchors[session_id] = {
                "lat": current_loc["lat"],
                "lon": current_loc["lon"],
                "city": current_loc["city"],
                "country": current_loc["country"],
                "code": current_loc["code"],
                "ip": current_ip,
                "timestamp": now
            }

        # First request seen for this session
        if not prev_loc:
            return 0.0, {
                "verdict": "session_initial_anchor",
                "origin": current_loc
            }

        # If identical IP, no physical relocation
        if prev_loc.get("ip") == current_ip:
            return 0.0, {
                "verdict": "same_ip_location",
                "city": current_loc["city"],
                "country": current_loc["country"]
            }

        elapsed_seconds = max(now - prev_loc.get("timestamp", now), 0.5)
        dist_km, speed_kmh = calculate_travel_velocity(
            prev_loc["lat"], prev_loc["lon"],
            current_loc["lat"], current_loc["lon"],
            elapsed_seconds
        )

        details = {
            "from_city": prev_loc["city"],
            "from_country": prev_loc["country"],
            "from_ip": prev_loc["ip"],
            "to_city": current_loc["city"],
            "to_country": current_loc["country"],
            "to_ip": current_ip,
            "distance_km": dist_km,
            "elapsed_seconds": round(elapsed_seconds, 1),
            "speed_kmh": speed_kmh
        }

        # Critical: Impossible speed
        if speed_kmh >= SPEED_IMPOSSIBLE_KMH:
            score = 0.95
            details["verdict"] = "IMPOSSIBLE_TRAVEL"
            details["explanation"] = (
                f"Displacement of {dist_km:,.1f} km from {prev_loc['city']} to {current_loc['city']} "
                f"in {elapsed_seconds:.1f}s requires {speed_kmh:,.1f} km/h (exceeds supersonic threshold)."
            )
            return score, details

        # Inter-country jump in under 5 minutes
        if prev_loc["country"] != current_loc["country"] and elapsed_seconds < 300:
            score = 0.85
            details["verdict"] = "RAPID_BORDER_TRANSIT"
            details["explanation"] = (
                f"Cross-border session relocation ({prev_loc['country']} → {current_loc['country']}) "
                f"within {elapsed_seconds:.1f}s."
            )
            return score, details

        # Suspicious velocity
        if speed_kmh >= SPEED_HIGH_SUSPICIOUS:
            score = 0.65
            details["verdict"] = "SUSPICIOUS_TRANSIT"
            return score, details

        # Moderate relocation
        if dist_km > 500 and elapsed_seconds < 1800:
            score = 0.35
            details["verdict"] = "ELEVATED_RELOCATION"
            return score, details

        return 0.0, {**details, "verdict": "normal_relocation"}


# Global detector
_TRAVEL_DETECTOR = ImpossibleTravelDetector()

def evaluate_impossible_travel(session_id: str, ip: str) -> Tuple[float, Dict[str, Any]]:
    return _TRAVEL_DETECTOR.evaluate_travel(session_id, ip)
