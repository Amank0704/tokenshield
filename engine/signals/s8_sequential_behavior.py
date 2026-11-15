"""
TokenShield — Signal 8: Sequential Request Behavior
====================================================
Paper weight: 0.35
Evaluates whether current user request path follows normal session workflow
or represents an anomalous jump (e.g., jump directly to money transfer or admin endpoints).
Uses LSTM Autoencoder reconstruction error on the sliding sequence buffer.
"""

import re
from typing import Tuple, Dict, Any
import numpy as np

from engine.state.sequence_buffer import SequenceBuffer
from engine.ml.inference.lstm_infer import LSTMInferencer

# Priority order matters: specific routes first, generic wrappers last
PATH_CATEGORIES = [
    ("transfer", 5), ("pay", 5), ("transaction", 5),
    ("admin", 6), ("password", 6), ("settings", 7),
    ("statement", 4), ("account", 3), ("profile", 3),
    ("dashboard", 2), ("home", 2),
    ("auth", 1), ("login", 1),
    ("api", 8), ("static", 0), ("images", 0), ("css", 0), ("js", 0)
]
N_CATEGORIES = 10

SQL_RE = re.compile(r"select\s|union\s|drop\s|exec\s|'--|sleep\s*\(", re.I)
XSS_RE = re.compile(r"<script|javascript:|onerror=|alert\s*\(", re.I)
SENS_RE = re.compile(r"admin|transfer|payment|credential|password|delete", re.I)

METHOD_MAP = {"GET": 0.0, "POST": 0.5, "PUT": 0.6, "DELETE": 0.8, "PATCH": 0.5}

# Minimum number of requests that must be in the sliding sequence buffer before
# the LSTM autoencoder's raw reconstruction-error score is trusted. With very
# few requests recorded (e.g. immediately after login, when the dashboard
# fires several requests in parallel via Promise.all()/setInterval), the model
# has not seen enough sequence context to reconstruct reliably and tends to
# report a near-maximal anomaly score for completely normal traffic. Below
# this length we rely solely on the explicit heuristic checks further down
# (direct sensitive-endpoint / deep-category jump), which are already tuned
# conservatively (capped at 0.70-0.85), instead of trusting the raw model.
MIN_SEQ_LEN_FOR_MODEL = 4

# The PCA fallback model backing this signal was trained on a dataset with
# almost no variance (observed p99 reconstruction error ~1e-6), meaning it
# never saw realistic, heterogeneous traffic (mixed GET/POST, mixed endpoint
# categories arriving close together). As a result its raw reconstruction
# error spikes unpredictably for completely ordinary live traffic, in a way
# no single threshold value can reliably separate from a genuine anomaly.
# Rather than trusting that raw, poorly-calibrated model score to single-
# handedly reach a "block"-level score, its contribution is capped here to a
# moderate ceiling. The explicit heuristic checks below (direct jump to a
# sensitive endpoint, or a deep-category jump early in a session) remain
# fully authoritative and uncapped, since they are deterministic and already
# tuned correctly.
MAX_MODEL_ONLY_SCORE = 0.30


class Signal8SequentialBehavior:
    def __init__(self, window_size: int = 10):
        self.buffer = SequenceBuffer(window_size=window_size)
        self.inferencer = LSTMInferencer.get()
        self.window_size = window_size

    def extract_request_vector(self, path: str, method: str, status_code: int = 200) -> np.ndarray:
        v = np.zeros(6, dtype=np.float32)
        p_lower = path.lower()
        cat = 9
        for k, idx in PATH_CATEGORIES:
            if k in p_lower:
                cat = idx
                break
        v[0] = cat / N_CATEGORIES
        v[1] = METHOD_MAP.get(method.upper(), 0.3)
        v[2] = 0.0 if status_code < 400 else (0.5 if status_code < 500 else 1.0)
        v[3] = 1.0 if SQL_RE.search(path) else 0.0
        v[4] = 1.0 if XSS_RE.search(path) else 0.0
        v[5] = 0.8 if SENS_RE.search(path) else 0.0
        return v

    def evaluate(self, session_key: str, path: str, method: str, status_code: int = 200) -> Tuple[float, Dict[str, Any]]:
        req_vec = self.extract_request_vector(path, method, status_code)
        self.buffer.record_request(session_key, req_vec)
        seq = self.buffer.get_sequence(session_key)

        if len(seq) >= MIN_SEQ_LEN_FOR_MODEL:
            score, is_anom = self.inferencer.predict(seq)
            raw_recon_error = self.inferencer.score_sequence(seq)
            # Cap the raw, poorly-calibrated model score (see MAX_MODEL_ONLY_SCORE
            # comment above) so it can't alone push this signal into block/critical
            # territory. The heuristic checks below can still raise the score higher
            # when they detect an actual known-bad pattern.
            if score > MAX_MODEL_ONLY_SCORE:
                score = MAX_MODEL_ONLY_SCORE
                is_anom = False
        else:
            # Not enough sequence context yet for the model to score reliably —
            # defer entirely to the explicit heuristic checks below.
            score, is_anom = 0.0, False
            raw_recon_error = 0.0

        details = {
            "window_size": len(seq),
            "is_anomaly": is_anom,
            "raw_recon_error": raw_recon_error,
            "threshold": self.inferencer.threshold,
            "category_idx": int(req_vec[0] * N_CATEGORIES),
            "sensitive_endpoint": bool(req_vec[5] > 0),
        }
        if len(seq) < MIN_SEQ_LEN_FOR_MODEL:
            details["status"] = "sequence_warmup_model_skipped"

        # Boost score if session directly jumps to endpoints without visiting home/login sequence first
        cat_idx = int(round(req_vec[0] * N_CATEGORIES))
        if len(seq) <= 3:
            if req_vec[5] > 0: # sensitive endpoint (transfer, admin, pay)
                score = max(score, 0.85)
                is_anom = True
                details["is_anomaly"] = True
                details["direct_sensitive_jump"] = True
            elif cat_idx in [3, 4, 5, 6]: # account, statement, transfer, admin
                score = max(score, 0.70)
                is_anom = True
                details["is_anomaly"] = True
                details["direct_deep_jump"] = True

        return float(np.clip(score, 0.0, 1.0)), details