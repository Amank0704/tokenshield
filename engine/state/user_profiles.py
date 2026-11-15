"""
TokenShield — User Biometric Behavioral Profiles
=================================================
Maintains running statistical baselines (mean, variance, sample count)
for each user's behavioral biometrics using Welford's algorithm and EWMA.
Stored in Redis with in-memory fallback.
"""

import json
import logging
import math
from typing import Dict, Any, Optional

log = logging.getLogger("ts.user_profiles")

try:
    import redis
    _redis = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    _redis.ping()
    _HAS_REDIS = True
except Exception:
    _HAS_REDIS = False
    _redis = None

from pathlib import Path

_CACHE_FILE = Path(__file__).resolve().parent / "profiles_cache.json"
_LOCAL_PROFILES = {}

if _CACHE_FILE.exists():
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as _f:
            _LOCAL_PROFILES = json.load(_f)
    except Exception as _e:
        log.warning(f"Failed to load profiles cache: {_e}")

METRIC_KEYS = [
    "typing_wpm",
    "typing_rhythm_cv",
    "mouse_velocity_mean",
    "mouse_velocity_cv",
    "idle_time_ratio"
]


class UserProfileStore:
    def __init__(self, ttl_seconds: int = 86400 * 30):
        self.ttl = ttl_seconds

    def _get_key(self, user_id: str) -> str:
        return f"ts:profile:bio:{user_id}"

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        if _HAS_REDIS and _redis:
            try:
                raw = _redis.get(self._get_key(user_id))
                if raw:
                    return json.loads(raw)
            except Exception as e:
                log.debug(f"Redis get profile error: {e}")

        return _LOCAL_PROFILES.get(user_id)

    def update_profile(self, user_id: str, new_metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Updates user profile with new observation using Welford's online algorithm.
        """
        profile = self.get_profile(user_id) or {
            "user_id": user_id,
            "sample_count": 0,
            "metrics": {
                k: {"count": 0, "mean": 0.0, "M2": 0.0, "variance": 1.0}
                for k in METRIC_KEYS
            }
        }

        profile["sample_count"] += 1

        for k in METRIC_KEYS:
            if k in new_metrics and new_metrics[k] is not None:
                x = float(new_metrics[k])
                m_stat = profile["metrics"].setdefault(k, {"count": 0, "mean": 0.0, "M2": 0.0, "variance": 1.0})
                m_stat["count"] += 1
                count = m_stat["count"]
                delta = x - m_stat["mean"]
                m_stat["mean"] += delta / count
                delta2 = x - m_stat["mean"]
                m_stat["M2"] += delta * delta2
                if count >= 2:
                    m_stat["variance"] = max(m_stat["M2"] / (count - 1), 1e-4)
                else:
                    m_stat["variance"] = 1.0

        if _HAS_REDIS and _redis:
            try:
                _redis.setex(self._get_key(user_id), self.ttl, json.dumps(profile))
            except Exception as e:
                log.debug(f"Redis save profile error: {e}")

        _LOCAL_PROFILES[user_id] = profile
        try:
            with open(_CACHE_FILE, "w", encoding="utf-8") as _f:
                json.dump(_LOCAL_PROFILES, _f, indent=2)
        except Exception as _e:
            log.debug(f"Failed to persist profiles cache: {_e}")
        return profile
