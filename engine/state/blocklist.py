"""
TokenShield — Unified Distributed Blocklist (Redis + In-Memory Fallback)
========================================================================
Manages real-time revoking and querying of compromised session tokens,
blacklisted IP addresses, and banned device fingerprints.
"""

import time
import logging
import threading
from typing import Dict, Any, Optional

log = logging.getLogger("ts.state.blocklist")

_LOCAL_TOKEN_BLOCKS: Dict[str, float] = {}   # token_hash -> expiry_ts
_LOCAL_IP_BLOCKS: Dict[str, float] = {}      # ip -> expiry_ts
_LOCAL_FP_BLOCKS: Dict[str, float] = {}      # fingerprint -> expiry_ts
_LOCK = threading.Lock()

_REDIS_CLIENT = None
_HAS_REDIS = None


def _get_redis():
    global _REDIS_CLIENT, _HAS_REDIS
    if _HAS_REDIS is False:
        return None
    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT

    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, db=0, socket_timeout=0.3, decode_responses=True)
        r.ping()
        _REDIS_CLIENT = r
        _HAS_REDIS = True
        log.info("Connected to Redis for distributed blocklist.")
        return _REDIS_CLIENT
    except Exception:
        _HAS_REDIS = False
        _REDIS_CLIENT = None
        log.info("Redis not detected — operating in high-performance local memory mode.")
        return None


def revoke_token(token_hash: str, ttl_seconds: int = 86400) -> Dict[str, Any]:
    """
    Revokes a session token immediately.
    """
    if not token_hash:
        return {"revoked": False, "method": "none", "reason": "empty_token"}

    r = _get_redis()
    if r:
        try:
            r.setex(f"ts:block:{token_hash}", ttl_seconds, "revoked")
            return {"revoked": True, "method": "redis", "token": f"{token_hash[:12]}..."}
        except Exception as e:
            log.debug(f"Redis revoke fallback: {e}")

    now = time.time()
    with _LOCK:
        _LOCAL_TOKEN_BLOCKS[token_hash] = now + ttl_seconds

    return {"revoked": True, "method": "local_memory", "token": f"{token_hash[:12]}..."}


def is_token_revoked(token_hash: str) -> bool:
    if not token_hash:
        return False

    r = _get_redis()
    if r:
        try:
            return bool(r.exists(f"ts:block:{token_hash}"))
        except Exception:
            pass

    now = time.time()
    with _LOCK:
        exp = _LOCAL_TOKEN_BLOCKS.get(token_hash)
        if exp is not None:
            if exp > now:
                return True
            del _LOCAL_TOKEN_BLOCKS[token_hash]
    return False


def block_ip(ip: str, ttl_seconds: int = 86400) -> Dict[str, Any]:
    """
    Blocks an IP address in the edge cache.
    """
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return {"blocked": False, "method": "ignored_loopback", "ip": ip}

    r = _get_redis()
    if r:
        try:
            r.setex(f"blocked_ip:{ip}", ttl_seconds, "auto")
            return {"blocked": True, "method": "redis", "ip": ip}
        except Exception as e:
            log.debug(f"Redis IP block fallback: {e}")

    now = time.time()
    with _LOCK:
        _LOCAL_IP_BLOCKS[ip] = now + ttl_seconds

    return {"blocked": True, "method": "local_memory", "ip": ip}


def is_ip_blocked(ip: str) -> bool:
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return False

    r = _get_redis()
    if r:
        try:
            return bool(r.exists(f"blocked_ip:{ip}"))
        except Exception:
            pass

    now = time.time()
    with _LOCK:
        exp = _LOCAL_IP_BLOCKS.get(ip)
        if exp is not None:
            if exp > now:
                return True
            del _LOCAL_IP_BLOCKS[ip]
    return False


def ban_fingerprint(fp_hash: str, ttl_seconds: int = 259200) -> Dict[str, Any]:
    if not fp_hash:
        return {"banned": False, "method": "none"}

    r = _get_redis()
    if r:
        try:
            r.setex(f"ts:fp:{fp_hash}", ttl_seconds, "banned")
            return {"banned": True, "method": "redis", "fingerprint": fp_hash[:12]}
        except Exception:
            pass

    now = time.time()
    with _LOCK:
        _LOCAL_FP_BLOCKS[fp_hash] = now + ttl_seconds

    return {"banned": True, "method": "local_memory", "fingerprint": fp_hash[:12]}


def unblock_ip(ip: str) -> bool:
    """Removes an IP from the blocklist (Redis and local memory)."""
    if not ip:
        return False
    r = _get_redis()
    if r:
        try:
            r.delete(f"blocked_ip:{ip}")
        except Exception:
            pass
    with _LOCK:
        if ip in _LOCAL_IP_BLOCKS:
            del _LOCAL_IP_BLOCKS[ip]
    return True


def clear_blocks():
    """Clears all in-memory blocks (useful for demo runs)."""
    with _LOCK:
        _LOCAL_TOKEN_BLOCKS.clear()
        _LOCAL_IP_BLOCKS.clear()
        _LOCAL_FP_BLOCKS.clear()

