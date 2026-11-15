"""
TokenShield — Mitigation Step 6: Coordinated Attack Detection & Quarantine
==========================================================================
Paper specification:
Checks whether incoming attack is part of a distributed / coordinated campaign:
  - Tracks attacks per CIDR /24 subnet over a 5-minute sliding window in Redis.
  - If >= 3 attacks from the same subnet within 5 minutes, triggers Subnet Quarantine.
  - Adds the entire subnet (e.g., 198.51.100.0/24) to the edge firewall / Redis blocklist.
"""

import time
import logging
import ipaddress
from typing import Tuple, Dict, Any

log = logging.getLogger("ts.mitigation.step6")

try:
    import redis
    _redis = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    _redis.ping()
    _HAS_REDIS = True
except Exception:
    _HAS_REDIS = False
    _redis = None

_LOCAL_SUBNET_TRACKER = {}  # subnet -> list of timestamps


def check_and_quarantine_coordinated_attack(
    ip: str,
    threshold: int = 3,
    window_sec: int = 300,
    quarantine_ttl_sec: int = 86400
) -> Tuple[bool, str]:
    """
    Returns (is_coordinated: bool, detail_message: str).
    """
    if not ip or ip in ("127.0.0.1", "localhost", "::1"):
        return False, "Localhost IP skipped"

    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback:
            return False, f"Private IP {ip} skipped"
        subnet = str(ipaddress.ip_network(f"{ip}/24", strict=False))
    except Exception:
        return False, "Invalid IP format"

    now = time.time()

    if _HAS_REDIS and _redis:
        try:
            rkey = f"ts:subnet_attacks:{subnet}"
            pipe = _redis.pipeline()
            pipe.zadd(rkey, {f"{ip}:{now}": now})
            pipe.zremrangebyscore(rkey, 0, now - window_sec)
            pipe.zcard(rkey)
            pipe.expire(rkey, window_sec * 2)
            results = pipe.execute()
            count = results[2]

            if count >= threshold:
                # Quarantine entire subnet
                qkey = f"ts:quarantine:subnet:{subnet}"
                _redis.setex(qkey, quarantine_ttl_sec, f"coordinated_{count}_attacks")
                # Also add to blocklist
                _redis.setex(f"blocked_subnet:{subnet}", quarantine_ttl_sec, "auto")
                return True, f"Quarantined subnet {subnet} ({count} attacks in {window_sec}s)"

            return False, f"Subnet {subnet} attack count: {count}/{threshold}"
        except Exception as e:
            log.debug(f"Redis coordinated check error: {e}")

    # In-memory fallback
    timestamps = _LOCAL_SUBNET_TRACKER.setdefault(subnet, [])
    timestamps = [t for t in timestamps if now - t <= window_sec]
    timestamps.append(now)
    _LOCAL_SUBNET_TRACKER[subnet] = timestamps

    if len(timestamps) >= threshold:
        return True, f"Quarantined subnet {subnet} ({len(timestamps)} attacks in {window_sec}s)"

    return False, f"Subnet {subnet} attack count: {len(timestamps)}/{threshold}"
