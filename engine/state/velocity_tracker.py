"""
TokenShield — Signal 2: Request Velocity & Burst Tracker
=========================================================
Thread-safe sliding-window tracker measuring request rates and burst surges
for both client IP and session token.

Tracks:
  - Rolling 60-second request volume (RPM)
  - Short-window 5-second burst rate (RPS)
  - Anomaly scoring aligned with TokenShield's 8-signal architecture
"""

import time
import threading
from collections import defaultdict, deque
from typing import Tuple, Dict, Any


class VelocityTracker:
    def __init__(self, window_seconds: float = 60.0, burst_window_seconds: float = 5.0):
        self.window_seconds = window_seconds
        self.burst_window_seconds = burst_window_seconds
        self._ip_history: Dict[str, deque] = defaultdict(deque)
        self._sess_history: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def record_and_score(self, ip: str, session_id: str = "") -> Tuple[float, Dict[str, Any]]:
        now = time.monotonic()
        cutoff_full = now - self.window_seconds
        cutoff_burst = now - self.burst_window_seconds

        with self._lock:
            # 1. Update IP history
            dq_ip = self._ip_history[ip]
            while dq_ip and dq_ip[0] < cutoff_full:
                dq_ip.popleft()
            dq_ip.append(now)
            ip_count = len(dq_ip)
            ip_burst = sum(1 for t in dq_ip if t >= cutoff_burst)

            # 2. Update Session history
            sess_count = 0
            sess_burst = 0
            if session_id and session_id != "anonymous":
                dq_sess = self._sess_history[session_id]
                while dq_sess and dq_sess[0] < cutoff_full:
                    dq_sess.popleft()
                dq_sess.append(now)
                sess_count = len(dq_sess)
                sess_burst = sum(1 for t in dq_sess if t >= cutoff_burst)

        # Calculate Burst RPS (Requests per second over last 5 seconds)
        burst_rps = max(ip_burst / max(self.burst_window_seconds, 1.0),
                        sess_burst / max(self.burst_window_seconds, 1.0))

        # Score determination based on RPM & burst rate
        effective_rpm = max(ip_count, sess_count)

        if effective_rpm >= 200 or burst_rps >= 25.0:
            score = 0.95
            level = "critical_flood"
        elif effective_rpm >= 100 or burst_rps >= 15.0:
            score = 0.75
            level = "high_velocity"
        elif effective_rpm >= 50 or burst_rps >= 8.0:
            score = 0.50
            level = "elevated_rate"
        elif effective_rpm >= 20 or burst_rps >= 4.0:
            score = 0.30
            level = "moderate_traffic"
        elif effective_rpm >= 10:
            score = 0.15
            level = "normal_active"
        else:
            score = 0.0
            level = "nominal"

        metadata = {
            "rpm": effective_rpm,
            "ip_rpm": ip_count,
            "session_rpm": sess_count,
            "burst_rps": round(burst_rps, 2),
            "window_seconds": self.window_seconds,
            "velocity_level": level
        }

        return float(round(score, 4)), metadata

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "tracked_ips": len(self._ip_history),
                "tracked_sessions": len(self._sess_history),
                "window_seconds": self.window_seconds
            }

    def clear(self):
        with self._lock:
            self._ip_history.clear()
            self._sess_history.clear()


# Global Singleton instance
_GLOBAL_TRACKER = VelocityTracker()

def get_velocity_tracker() -> VelocityTracker:
    return _GLOBAL_TRACKER
