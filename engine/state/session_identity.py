"""
TokenShield — Session Identity Tracker (Signal 3)
====================================================
Tracks the last-seen IP address and User-Agent for each session_id.
On each request, compares the incoming IP/UA against what was last seen
for that same session_id. A mismatch means the same token/session is
suddenly being used from a different client context — the classic
stolen-token signature.

Storage: Redis if available (shared across processes/restarts),
falling back to an in-memory dict otherwise. Same fallback pattern
as engine/state/sequence_buffer.py.
"""

import time
import json
import logging
from typing import Optional, Tuple

log = logging.getLogger("ts.session_identity")

try:
    import redis
    _redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    _redis_client.ping()
    _HAS_REDIS = True
except Exception:
    _HAS_REDIS = False
    _redis_client = None

# In-memory fallback: session_id -> {"ip": str, "ua": str, "ts": float}
_LOCAL_CACHE = {}
_MAX_LOCAL_SESSIONS = 10000


class SessionIdentityTracker:
    """
    Signal 3: Session Consistency.

    score = 0.0   -> same IP and same UA as last seen for this session (or first sighting)
    score = 0.55  -> IP changed, UA unchanged
    score = 0.35  -> UA changed, IP unchanged
    score = 0.75  -> both IP and UA changed (strongest signal of token theft)

    These weights feed into the existing s3_score slot in engine/main.py,
    which is then multiplied by the 0.30 signal weight in the composite
    threat_score formula.
    """

    KEY_PREFIX = "ts:sess_id:"
    TTL_SECONDS = 86400  # 24h, matches sequence_buffer.py convention

    def _redis_key(self, session_id: str) -> str:
        return f"{self.KEY_PREFIX}{session_id}"

    def _load(self, session_id: str) -> Optional[dict]:
        if _HAS_REDIS:
            try:
                raw = _redis_client.get(self._redis_key(session_id))
                return json.loads(raw) if raw else None
            except Exception as e:
                log.warning(f"redis read failed, falling back to local cache: {e}")
        return _LOCAL_CACHE.get(session_id)

    def _save(self, session_id: str, ip: str, ua: str) -> None:
        record = {"ip": ip, "ua": ua, "ts": time.time()}
        if _HAS_REDIS:
            try:
                _redis_client.setex(
                    self._redis_key(session_id),
                    self.TTL_SECONDS,
                    json.dumps(record),
                )
                return
            except Exception as e:
                log.warning(f"redis write failed, falling back to local cache: {e}")

        if len(_LOCAL_CACHE) >= _MAX_LOCAL_SESSIONS and session_id not in _LOCAL_CACHE:
            oldest_key = min(_LOCAL_CACHE, key=lambda k: _LOCAL_CACHE[k]["ts"])
            _LOCAL_CACHE.pop(oldest_key, None)
        _LOCAL_CACHE[session_id] = record

    def evaluate(self, session_id: str, ip: str, user_agent: str) -> Tuple[float, list]:
        """
        Returns (score, reasons). Always updates the stored identity
        AFTER scoring, so the next request compares against this one.
        """
        ua = user_agent or ""
        prior = self._load(session_id)

        if prior is None:
            self._save(session_id, ip, ua)
            return 0.0, []

        ip_changed = prior.get("ip") != ip
        ua_changed = prior.get("ua") != ua

        reasons = []
        if ip_changed:
            reasons.append("session_ip_changed")
        if ua_changed:
            reasons.append("session_ua_changed")

        if ip_changed and ua_changed:
            score = 0.75
        elif ip_changed:
            score = 0.55
        elif ua_changed:
            score = 0.35
        else:
            score = 0.0

        self._save(session_id, ip, ua)
        return score, reasons


_tracker_singleton: Optional[SessionIdentityTracker] = None


def get_tracker() -> SessionIdentityTracker:
    global _tracker_singleton
    if _tracker_singleton is None:
        _tracker_singleton = SessionIdentityTracker()
    return _tracker_singleton
