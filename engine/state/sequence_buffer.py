"""
TokenShield — Sliding Window Sequence Buffer (Signal 8)
========================================================
Maintains the last N requests for each session/IP in Redis (or in-memory LRU fallback).
Extracts the 6-dim representation for the LSTM Autoencoder.
"""

import time
import json
import logging
from typing import List, Optional
import numpy as np

log = logging.getLogger("ts.sequence_buffer")

try:
    import redis
    _redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    _redis_client.ping()
    _HAS_REDIS = True
except Exception:
    _HAS_REDIS = False
    _redis_client = None

# In-memory LRU cache fallback: session_id -> list of [t, v0, v1, v2, v3, v4, v5]
_LOCAL_CACHE = {}
_MAX_LOCAL_SESSIONS = 10000


class SequenceBuffer:
    def __init__(self, window_size: int = 10, ttl_seconds: int = 3600):
        self.window_size = window_size
        self.ttl = ttl_seconds

    def record_request(self, session_key: str, req_vector: np.ndarray) -> None:
        """
        req_vector: 6-dim float array: [category, method_risk, status_risk, sql, xss, sensitive]
        """
        now = time.time()
        val = [now] + [float(x) for x in req_vector[:6]]
        val_str = json.dumps(val)

        if _HAS_REDIS and _redis_client:
            try:
                rkey = f"ts:seq:{session_key}"
                pipe = _redis_client.pipeline()
                pipe.rpush(rkey, val_str)
                pipe.ltrim(rkey, -self.window_size, -1)
                pipe.expire(rkey, self.ttl)
                pipe.execute()
                return
            except Exception as e:
                log.debug(f"Redis sequence buffer write error: {e}")

        # Local fallback
        if len(_LOCAL_CACHE) > _MAX_LOCAL_SESSIONS:
            _LOCAL_CACHE.clear()
        if session_key not in _LOCAL_CACHE:
            _LOCAL_CACHE[session_key] = []
        _LOCAL_CACHE[session_key].append(val)
        if len(_LOCAL_CACHE[session_key]) > self.window_size:
            _LOCAL_CACHE[session_key] = _LOCAL_CACHE[session_key][-self.window_size:]

    def get_sequence(self, session_key: str) -> np.ndarray:
        """
        Returns np.ndarray of shape (len, 6).
        """
        raw_items = []
        if _HAS_REDIS and _redis_client:
            try:
                rkey = f"ts:seq:{session_key}"
                raw_items = _redis_client.lrange(rkey, 0, -1)
            except Exception as e:
                log.debug(f"Redis sequence buffer read error: {e}")

        if not raw_items and session_key in _LOCAL_CACHE:
            local_items = _LOCAL_CACHE[session_key]
            if local_items:
                return np.array([item[1:7] for item in local_items], dtype=np.float32)
            return np.zeros((1, 6), dtype=np.float32)

        if not raw_items:
            return np.zeros((1, 6), dtype=np.float32)

        parsed = []
        for item in raw_items:
            try:
                arr = json.loads(item)
                parsed.append(arr[1:7])
            except Exception:
                pass

        if not parsed:
            return np.zeros((1, 6), dtype=np.float32)

        return np.array(parsed, dtype=np.float32)
