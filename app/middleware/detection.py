"""
TokenShield Detection Middleware
================================

Central request interception and anomaly scoring pipeline.

Responsibilities:
- Extract request/session/device telemetry
- Run the real TokenShield AI engine first
- Fall back to eight local detection signals if the engine is unavailable
- Normalize all eight signals into one canonical schema
- Persist detection results
- Maintain latest live detection state for the dashboard
- Detect session-token replay / hijacking
- Revoke compromised sessions
- Revoke all active sessions belonging to a compromised account
- Block compromised tokens when Redis is available
- Contain compromised device fingerprints when available
- Hard-lock the affected account until administrative unlock
- Forward detailed anomaly information to the simulation dashboard
"""

import hashlib
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

import requests
from flask import g, request

from app.extensions import db
from app.models import BehaviorLog, Session


logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

ENGINE_URL = os.getenv(
    "TOKENSHIELD_ENGINE_URL",
    "http://127.0.0.1:7777",
)

ENGINE_TIMEOUT = float(
    os.getenv(
        "TOKENSHIELD_ENGINE_TIMEOUT",
        "5.0",
    )
)

ANOMALY_WEBHOOK = os.getenv(
    "TOKENSHIELD_ANOMALY_WEBHOOK",
    "http://127.0.0.1:5001/api/simulation/engine-anomaly",
)

ANOMALY_THRESHOLD = float(
    os.getenv(
        "TOKENSHIELD_ANOMALY_THRESHOLD",
        "0.85",
    )
)

REPLAY_CONTEXT_PATH = os.getenv(
    "TOKENSHIELD_REPLAY_PATH",
    "/api/security/session-check",
)

# Number of seconds used for request-velocity analysis.
VELOCITY_WINDOW_SECONDS = float(
    os.getenv(
        "TOKENSHIELD_VELOCITY_WINDOW",
        "10.0",
    )
)

# Maximum number of timestamps retained per session.
VELOCITY_HISTORY_LIMIT = int(
    os.getenv(
        "TOKENSHIELD_VELOCITY_HISTORY_LIMIT",
        "100",
    )
)


# ============================================================================
# PATH EXCLUSIONS
# ============================================================================

EXCLUDED_PATHS = {
    "/health",
    "/favicon.ico",
    "/api/simulation/live-comparison",
    "/api/simulation/current",
    "/api/simulation/history",
    "/api/simulation/status",
}


# ============================================================================
# RUNTIME STATE
# ============================================================================

_LATEST_DETECTION = {}

_DETECTION_LOCK = threading.RLock()

# Persistent process-level request history.
#
# Unlike Flask `g`, this survives across requests and therefore allows
# velocity detection to actually observe request bursts.
_VELOCITY_HISTORY = defaultdict(
    deque,
)

_VELOCITY_LOCK = threading.Lock()

# Prevent repeated mitigation for the same database session.
_MITIGATED_SESSIONS = set()


# ============================================================================
# GENERIC HELPERS
# ============================================================================

def _utc_now():
    """
    Return timezone-aware UTC time.
    """
    return datetime.now(timezone.utc)


def _utc_naive_now():
    """
    Return UTC datetime without timezone information.

    The existing TokenShield SQLAlchemy models use naive DateTime columns
    for several fields.
    """
    return datetime.utcnow()


def _safe_float(
    value,
    default=0.0,
):
    """
    Safely convert a value to float.
    """
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def _safe_json(
    value,
    default=None,
):
    """
    Safely decode JSON.
    """
    if value is None:
        return default

    if isinstance(
        value,
        (
            dict,
            list,
        ),
    ):
        return value

    try:
        return json.loads(value)
    except Exception:
        return default


def _request_ip():
    """
    Obtain the best available client IP.

    X-Forwarded-For is useful when deployed behind a trusted reverse proxy.
    During local development Flask remote_addr is used.
    """
    forwarded = request.headers.get(
        "X-Forwarded-For",
    )

    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get(
        "X-Real-IP",
    )

    if real_ip:
        return real_ip.strip()

    return request.remote_addr or "127.0.0.1"


def _request_user_agent():
    """
    Return the current request User-Agent.
    """
    return request.headers.get(
        "User-Agent",
        "Unknown User-Agent",
    )


def _request_raw_token():
    """
    Extract the raw bearer token.

    The raw token is never persisted.
    """
    auth_header = request.headers.get(
        "Authorization",
        "",
    )

    if not auth_header.startswith(
        "Bearer ",
    ):
        return None

    token = auth_header[
        7:
    ].strip()

    return token or None


def _request_device_fingerprint():
    """
    Return the browser/device fingerprint supplied by the client.
    """
    return request.headers.get(
        "X-Device-Fingerprint",
        "",
    ).strip()


def _request_biometrics():
    """
    Read aggregate behavioral telemetry from the browser.

    Expected header:

        X-TS-Biometrics: {...}

    Raw keystrokes are never processed or persisted.
    """
    raw = request.headers.get(
        "X-TS-Biometrics",
    )

    if not raw:
        return {}

    data = _safe_json(
        raw,
        {},
    )

    if isinstance(
        data,
        dict,
    ):
        return data

    return {}


def _token_hash(raw_token):
    """
    Generate the SHA-256 representation used by the Session.token column.
    """
    if not raw_token:
        return None

    return hashlib.sha256(
        raw_token.encode(
            "utf-8",
        ),
    ).hexdigest()


# ============================================================================
# SESSION RESOLUTION
# ============================================================================

def _get_session_from_request():
    """
    Resolve the authenticated TokenShield session.

    Session.token stores the SHA-256 hash of the actual JWT.
    """

    # ------------------------------------------------------------------
    # Existing request context
    # ------------------------------------------------------------------

    session_obj = getattr(
        g,
        "session",
        None,
    )

    if isinstance(
        session_obj,
        Session,
    ):
        return session_obj

    session_obj = getattr(
        g,
        "tokenshield_session",
        None,
    )

    if isinstance(
        session_obj,
        Session,
    ):
        return session_obj

    # ------------------------------------------------------------------
    # Existing session ID
    # ------------------------------------------------------------------

    session_id = getattr(
        g,
        "session_id",
        None,
    )

    if session_id:
        try:
            return Session.query.filter_by(
                token=session_id,
            ).first()
        except Exception:
            logger.exception(
                "Unable to resolve session from g.session_id",
            )

    # ------------------------------------------------------------------
    # Bearer token
    # ------------------------------------------------------------------

    raw_token = _request_raw_token()

    if raw_token:
        try:
            token_hash = _token_hash(
                raw_token,
            )

            return Session.query.filter_by(
                token=token_hash,
            ).first()

        except Exception:
            logger.exception(
                "Unable to resolve TokenShield session from bearer token",
            )

    return None


# ============================================================================
# SIGNAL 1 — IP REPUTATION
# ============================================================================

def _score_ip_reputation(
    session,
):
    """
    Signal 1: IP reputation.

    The local fallback remains conservative and does not pretend to have
    access to an external threat-intelligence provider.
    """

    ip = _request_ip()

    suspicious_ips = {
        "0.0.0.0",
        "255.255.255.255",
    }

    if ip in suspicious_ips:
        return (
            1.0,
            [
                "suspicious_ip",
            ],
        )

    return (
        0.05,
        [],
    )


# ============================================================================
# SIGNAL 2 — REQUEST VELOCITY
# ============================================================================

def _score_request_velocity(
    session,
):
    """
    Signal 2: request velocity.

    Maintains process-level request history per session so repeated requests
    across separate Flask requests can actually be measured.
    """

    if not session:
        return (
            0.05,
            [],
        )

    session_key = str(
        getattr(
            session,
            "id",
            "",
        ),
    )

    if not session_key:
        return (
            0.05,
            [],
        )

    now = time.time()

    with _VELOCITY_LOCK:

        history = _VELOCITY_HISTORY[
            session_key
        ]

        history.append(
            now,
        )

        cutoff = (
            now
            - VELOCITY_WINDOW_SECONDS
        )

        while (
            history
            and history[0] < cutoff
        ):
            history.popleft()

        while len(history) > VELOCITY_HISTORY_LIMIT:
            history.popleft()

        count = len(history)

    if count >= 50:
        return (
            1.0,
            [
                (
                    "request_velocity_high:"
                    f"{count}/{int(VELOCITY_WINDOW_SECONDS)}s"
                ),
            ],
        )

    if count >= 30:
        return (
            0.80,
            [
                (
                    "request_velocity_elevated:"
                    f"{count}/{int(VELOCITY_WINDOW_SECONDS)}s"
                ),
            ],
        )

    if count >= 15:
        return (
            0.50,
            [
                (
                    "request_velocity_watch:"
                    f"{count}/{int(VELOCITY_WINDOW_SECONDS)}s"
                ),
            ],
        )

    return (
        0.05,
        [],
    )


# ============================================================================
# SIGNAL 3 — SESSION CONSISTENCY
# ============================================================================

def _score_session_consistency(
    session,
):
    """
    Signal 3: session consistency.

    Compares current request identity against the identity associated with
    the original authenticated session.

    This is the primary local replay/hijacking detector.
    """

    if not session:
        return (
            0.10,
            [],
        )

    score = 0.05

    reasons = []

    current_ip = _request_ip()

    current_ua = _request_user_agent()

    current_fp = _request_device_fingerprint()

    baseline_ip = getattr(
        session,
        "ip_address",
        None,
    )

    baseline_ua = getattr(
        session,
        "user_agent",
        None,
    )

    baseline_fp = getattr(
        session,
        "device_fingerprint",
        None,
    )

    # ------------------------------------------------------------------
    # IP mismatch
    # ------------------------------------------------------------------

    if (
        baseline_ip
        and current_ip != baseline_ip
    ):
        score = max(
            score,
            0.90,
        )

        reasons.append(
            (
                "ip_changed:"
                f"{baseline_ip}→{current_ip}"
            ),
        )

    # ------------------------------------------------------------------
    # User-Agent mismatch
    # ------------------------------------------------------------------

    if (
        baseline_ua
        and current_ua != baseline_ua
    ):
        score = max(
            score,
            0.85,
        )

        reasons.append(
            "user_agent_changed",
        )

    # ------------------------------------------------------------------
    # Device fingerprint mismatch
    # ------------------------------------------------------------------

    if (
        baseline_fp
        and current_fp
        and current_fp != baseline_fp
    ):
        score = max(
            score,
            0.95,
        )

        reasons.append(
            "device_fingerprint_changed",
        )

    # ------------------------------------------------------------------
    # Partial device information
    #
    # If the baseline has a fingerprint but the request suddenly stops
    # providing it, treat that as suspicious rather than silently ignoring it.
    # ------------------------------------------------------------------

    if (
        baseline_fp
        and not current_fp
    ):
        score = max(
            score,
            0.70,
        )

        reasons.append(
            "device_fingerprint_missing",
        )

    return (
        score,
        reasons,
    )


# ============================================================================
# SIGNAL 4 — PAYLOAD ANALYSIS
# ============================================================================

def _score_payload_analysis():
    """
    Signal 4: payload analysis.

    Sensitive values such as passwords are deliberately not inspected.
    Inspects:
      - Request path for suspicious fragments
      - Request body (JSON) for SQL injection, XSS, and path traversal patterns
      - Content size anomaly
    """

    score = 0.05

    reasons = []

    content_length = (
        request.content_length
        or 0
    )

    if content_length > 5_000_000:
        score = 0.90

        reasons.append(
            "oversized_payload",
        )

    suspicious_path_fragments = (
        "../",
        "..\\",
        "<script",
        "javascript:",
    )

    path_lower = request.path.lower()

    for fragment in suspicious_path_fragments:

        if fragment in path_lower:

            score = max(
                score,
                0.85,
            )

            reasons.append(
                f"suspicious_path:{fragment}",
            )

    # ── Body inspection for SQLi / XSS / path traversal ────────────────────
    import re as _re

    try:
        if request.content_type and "json" in request.content_type.lower():
            body_raw = request.get_data(as_text=True, cache=True) or ""
            body_lower = body_raw.lower()

            # SQL injection patterns
            sqli_patterns = [
                r"select\s+",
                r"\bunion\s+select\b",
                r"\binsert\s+into\b",
                r"drop\s+table",
                r"'--",
                r"or\s+'?1'?\s*=\s*'?1",
                r"'\s+or\s+'",
                r";\s*-{2}",
            ]
            for pat in sqli_patterns:
                if _re.search(pat, body_lower):
                    score = max(score, 0.90)
                    reasons.append("sql_injection_in_body")
                    break

            # XSS patterns
            xss_patterns = [
                r"<script",
                r"javascript\s*:",
                r"onerror\s*=",
                r"alert\s*\(",
                r"document\.cookie",
                r"document\.location",
            ]
            for pat in xss_patterns:
                if _re.search(pat, body_lower):
                    score = max(score, 0.80)
                    reasons.append("xss_payload_in_body")
                    break

            # Path traversal in body
            if "../" in body_lower or "%2e%2e" in body_lower:
                score = max(score, 0.85)
                reasons.append("path_traversal_in_body")

    except Exception:
        pass  # Never break request flow due to inspection error
    # ────────────────────────────────────────────────────────────────────────

    return (
        score,
        reasons,
    )



# ============================================================================
# SIGNAL 5 — BEHAVIORAL BIOMETRICS
# ============================================================================

def _score_behavioral_biometrics(
    session,
):
    """
    Signal 5: behavioral biometrics.

    Uses aggregate browser telemetry:

    - typing WPM
    - click rate
    - mouse speed
    - idle ratio

    No raw keystrokes are stored.
    """

    biometrics = _request_biometrics()

    if not biometrics:
        return (
            0.05,
            [],
        )

    score = 0.05

    reasons = []

    typing_wpm = _safe_float(
        biometrics.get(
            "typing_wpm",
        ),
    )

    click_rate = _safe_float(
        biometrics.get(
            "click_rate",
        ),
    )

    mouse_speed = _safe_float(
        biometrics.get(
            "mouse_speed",
        ),
    )

    idle_ratio = _safe_float(
        biometrics.get(
            "idle_ratio",
        ),
    )

    if typing_wpm > 180:
        score = max(
            score,
            0.70,
        )

        reasons.append(
            "typing_rate_unusual",
        )

    if click_rate > 15:
        score = max(
            score,
            0.70,
        )

        reasons.append(
            "click_rate_unusual",
        )

    if mouse_speed > 5000:
        score = max(
            score,
            0.65,
        )

        reasons.append(
            "mouse_speed_unusual",
        )

    if idle_ratio < 0.01:
        score = max(
            score,
            0.55,
        )

        reasons.append(
            "low_idle_ratio",
        )

    return (
        score,
        reasons,
    )


# ============================================================================
# SIGNAL 6 — GEOGRAPHIC IMPOSSIBILITY
# ============================================================================

def _score_geographic_impossibility(
    session,
):
    """
    Signal 6: geographic impossibility.

    The real geographic model can be provided by the standalone engine.
    Without trustworthy geographic coordinates in the local request, the
    fallback remains neutral rather than inventing a location.
    """

    return (
        0.05,
        [],
    )


# ============================================================================
# SIGNAL 7 — ENDPOINT RISK
# ============================================================================

def _score_endpoint_risk():
    """
    Signal 7: endpoint risk.
    """

    score = 0.05

    reasons = []

    method = request.method.upper()

    path = request.path.lower()

    high_value_paths = (
        "/transfer",
        "/payment",
        "/withdraw",
        "/admin",
        "/security",
        "/account",
    )

    for fragment in high_value_paths:

        if fragment in path:

            score = max(
                score,
                0.55,
            )

            reasons.append(
                f"high_value_endpoint:{fragment}",
            )

            break

    if method in {
        "DELETE",
        "PUT",
        "PATCH",
    }:
        score = max(
            score,
            0.45,
        )

        reasons.append(
            f"state_changing_method:{method}",
        )

    return (
        score,
        reasons,
    )


# ============================================================================
# SIGNAL 8 — SEQUENTIAL BEHAVIOR
# ============================================================================

def _score_sequential_behavior(
    session,
):
    """
    Signal 8: sequential behavior.

    The standalone AI engine provides the richer sequence model. The local
    fallback remains conservative because it must not manufacture behavioral
    history.
    """

    return (
        0.05,
        [],
    )


# ============================================================================
# SIGNAL NORMALIZATION
# ============================================================================

def _normalize_signals(
    raw,
):
    """
    Normalize all engine/local results into exactly eight canonical signals.
    """

    raw = raw or {}

    return {
        "ip_reputation": round(
            _safe_float(
                raw.get(
                    "ip_reputation",
                ),
            ),
            4,
        ),

        "request_velocity": round(
            _safe_float(
                raw.get(
                    "request_velocity",
                ),
            ),
            4,
        ),

        "session_consistency": round(
            _safe_float(
                raw.get(
                    "session_consistency",
                ),
            ),
            4,
        ),

        "payload_analysis": round(
            _safe_float(
                raw.get(
                    "payload_analysis",
                ),
            ),
            4,
        ),

        "behavioral_biometrics": round(
            _safe_float(
                raw.get(
                    "behavioral_biometrics",
                ),
            ),
            4,
        ),

        "geographic_impossibility": round(
            _safe_float(
                raw.get(
                    "geographic_impossibility",
                ),
            ),
            4,
        ),

        "endpoint_risk": round(
            _safe_float(
                raw.get(
                    "endpoint_risk",
                    raw.get(
                        "endpoint_pattern",
                    ),
                ),
            ),
            4,
        ),

        "sequential_behavior": round(
            _safe_float(
                raw.get(
                    "sequential_behavior",
                ),
            ),
            4,
        ),
    }


# ============================================================================
# REAL TOKENSHIELD ENGINE
# ============================================================================

def _engine_detection(
    session,
):
    """
    Ask the standalone TokenShield AI engine for the current request.

    Returns None when the engine is unavailable or returns an unusable
    response. This allows the local eight-signal fallback to run.
    """

    if not session:
        return None

    try:

        from sdk.python.tokenshield_sdk import (
            TokenShieldClient,
        )

        client = TokenShieldClient(
            engine_url=ENGINE_URL,
            timeout=ENGINE_TIMEOUT,
        )

        decision = client.inspect_flask_request(
            request,
            session_id=str(
                getattr(
                    session,
                    "token",
                    session.id,
                ),
            ),
            user_id=str(
                getattr(
                    session,
                    "user_id",
                    "",
                ),
            ),
        )

        if not decision:
            return None

        reasons = list(
            getattr(
                decision,
                "reasons",
                [],
            )
            or []
        )

        # Engine connectivity failure is not treated as a safe result.
        if any(
            str(reason).startswith(
                "engine_unreachable_",
            )
            for reason in reasons
        ):
            return None

        signals = _normalize_signals(
            getattr(
                decision,
                "signals",
                {},
            ),
        )

        threat_score = _safe_float(
            getattr(
                decision,
                "threat_score",
                0.0,
            ),
        )

        return {
            "signals": signals,

            "reasons": reasons,

            "total": round(
                threat_score,
                4,
            ),

            "threat_level": (
                getattr(
                    decision,
                    "threat_level",
                    None,
                )
                or "safe"
            ),

            "is_threat": bool(
                getattr(
                    decision,
                    "should_block",
                    False,
                )
            ),

            "is_suspicious": (
                threat_score >= 0.30
            ),

            "ip": _request_ip(),

            "explanation": (
                getattr(
                    decision,
                    "explanation",
                    {},
                )
                or {}
            ),

            "engine_mode": "api_live",

            "engine_latency_ms": round(
                _safe_float(
                    getattr(
                        decision,
                        "latency_ms",
                        0.0,
                    ),
                ),
                2,
            ),

            "model": {
                "isolation_forest_anomaly": getattr(
                    decision,
                    "isolation_forest_anomaly",
                    None,
                ),

                "meta_classifier_probability": getattr(
                    decision,
                    "meta_classifier_probability",
                    None,
                ),
            },
        }

    except Exception as exc:

        logger.warning(
            (
                "TokenShield AI engine unavailable; "
                "using local fallback: %s"
            ),
            exc,
        )

        return None


# ============================================================================
# LOCAL EIGHT-SIGNAL DETECTION
# ============================================================================

def _run_detection(
    session=None,
):
    """
    Run the real AI engine first.

    If unavailable, run all eight local detection signals.
    """

    # ------------------------------------------------------------------
    # REAL AI ENGINE
    # ------------------------------------------------------------------

    live = _engine_detection(
        session,
    )

    if live is not None:
        return live

    # ------------------------------------------------------------------
    # LOCAL FALLBACK
    # ------------------------------------------------------------------

    scores = {}

    reasons = []

    signal_calls = [
        (
            "ip_reputation",
            lambda: _score_ip_reputation(
                session,
            ),
        ),

        (
            "request_velocity",
            lambda: _score_request_velocity(
                session,
            ),
        ),

        (
            "session_consistency",
            lambda: _score_session_consistency(
                session,
            ),
        ),

        (
            "payload_analysis",
            _score_payload_analysis,
        ),

        (
            "behavioral_biometrics",
            lambda: _score_behavioral_biometrics(
                session,
            ),
        ),

        (
            "geographic_impossibility",
            lambda: _score_geographic_impossibility(
                session,
            ),
        ),

        (
            "endpoint_risk",
            _score_endpoint_risk,
        ),

        (
            "sequential_behavior",
            lambda: _score_sequential_behavior(
                session,
            ),
        ),
    ]

    for name, function in signal_calls:

        try:

            score, signal_reasons = function()

        except Exception as exc:

            logger.exception(
                "TokenShield signal %s failed: %s",
                name,
                exc,
            )

            score = 0.0

            signal_reasons = []

        scores[name] = round(
            _safe_float(
                score,
            ),
            4,
        )

        reasons.extend(
            signal_reasons or [],
        )

    # ------------------------------------------------------------------
    # WEIGHTS
    # ------------------------------------------------------------------

    weights = {
        "ip_reputation": 0.12,
        "request_velocity": 0.10,
        "session_consistency": 0.20,
        "payload_analysis": 0.10,
        "behavioral_biometrics": 0.18,
        "geographic_impossibility": 0.10,
        "endpoint_risk": 0.10,
        "sequential_behavior": 0.10,
    }

    total = sum(
        scores[name] * weights[name]
        for name in weights
    )

    # ------------------------------------------------------------------
    # HIGH-CONFIDENCE ATTACK OVERRIDE
    # ------------------------------------------------------------------
    # Individual high-confidence anomalies (SQLi, XSS, banned device, Tor,
    # impossible travel, bot biometrics) elevate threat score to prevent dilution.
    critical_signals = [
        scores.get("session_consistency", 0.0),
        scores.get("payload_analysis", 0.0),
        scores.get("geographic_impossibility", 0.0),
        scores.get("ip_reputation", 0.0),
        scores.get("behavioral_biometrics", 0.0),
        scores.get("sequential_behavior", 0.0),
    ]
    max_critical = max(critical_signals) if critical_signals else 0.0

    if max_critical >= 0.80:
        total = max(
            total,
            max_critical * 0.95,
        )

    total = min(
        1.0,
        max(
            0.0,
            total,
        ),
    )

    # ------------------------------------------------------------------
    # THREAT LEVEL
    # ------------------------------------------------------------------

    if total >= ANOMALY_THRESHOLD:

        threat_level = "critical"

    elif total >= 0.70:

        threat_level = "high"

    elif total >= 0.50:

        threat_level = "medium"

    elif total >= 0.30:

        threat_level = "low"

    else:

        threat_level = "safe"

    return {
        "signals": _normalize_signals(
            scores,
        ),

        "reasons": reasons,

        "total": round(
            total,
            4,
        ),

        "threat_level": threat_level,

        "is_threat": (
            total >= ANOMALY_THRESHOLD
        ),

        "is_suspicious": (
            total >= 0.30
        ),

        "ip": _request_ip(),

        "explanation": {
            "source": "local_fallback",
            "reasons": reasons,
        },

        "engine_mode": "local_fallback",

        "engine_latency_ms": 0.0,

        "model": {},
    }


# ============================================================================
# PERSISTENCE
# ============================================================================

def _persist_results(
    session,
    result,
):
    """
    Persist the detection result to BehaviorLog and update dashboard state.

    Compatible with the current BehaviorLog model:
    - timestamp
    - action_type
    - ip_address
    - user_agent
    - fingerprint_data
    """

    if not session:
        return None

    try:

        # --------------------------------------------------------------
        # Browser telemetry
        # --------------------------------------------------------------

        bio = _request_biometrics()

        device_fp = _request_device_fingerprint()

        timestamp = _utc_now().isoformat()

        fingerprint_data = {
            "ip": _request_ip(),

            "user_agent": _request_user_agent(),

            "device_fingerprint": device_fp,

            "biometrics": bio,

            "signals": result.get(
                "signals",
                {},
            ),

            "reasons": result.get(
                "reasons",
                [],
            ),

            "total": result.get(
                "total",
                0.0,
            ),

            "threat_level": result.get(
                "threat_level",
                "safe",
            ),

            "engine_mode": result.get(
                "engine_mode",
            ),

            "engine_latency_ms": result.get(
                "engine_latency_ms",
                0.0,
            ),

            "path": request.path,

            "method": request.method,

            "timestamp": timestamp,
        }

        # --------------------------------------------------------------
        # BehaviorLog
        #
        # IMPORTANT:
        # The current model requires action_type and ip_address.
        # It also uses timestamp rather than created_at.
        # --------------------------------------------------------------

        behavior = BehaviorLog(
            session_id=session.id,

            timestamp=_utc_naive_now(),

            action_type=(
                "anomaly_detection"
                if result.get(
                    "is_threat",
                    False,
                )
                else "request"
            ),

            ip_address=_request_ip(),

            user_agent=_request_user_agent(),

            endpoint=request.path,

            request_method=request.method,

            fingerprint_data=json.dumps(
                fingerprint_data,
                default=str,
            ),
        )

        db.session.add(
            behavior,
        )

        db.session.commit()

        # --------------------------------------------------------------
        # Latest live dashboard state
        # --------------------------------------------------------------

        with _DETECTION_LOCK:

            _LATEST_DETECTION[
                str(session.id)
            ] = {
                "timestamp": timestamp,

                "session_id": session.id,

                "user_id": str(
                    getattr(
                        session,
                        "user_id",
                        "",
                    ),
                ),

                "ip": result.get(
                    "ip",
                ),

                "user_agent": _request_user_agent(),

                "device_fingerprint": device_fp,

                "biometrics": bio,

                "signals": result.get(
                    "signals",
                    {},
                ),

                "reasons": result.get(
                    "reasons",
                    [],
                ),

                "total": result.get(
                    "total",
                    0.0,
                ),

                "threat_level": result.get(
                    "threat_level",
                    "safe",
                ),

                "is_threat": bool(
                    result.get(
                        "is_threat",
                        False,
                    ),
                ),

                "is_suspicious": bool(
                    result.get(
                        "is_suspicious",
                        False,
                    ),
                ),

                "engine_mode": result.get(
                    "engine_mode",
                ),

                "engine_latency_ms": result.get(
                    "engine_latency_ms",
                    0.0,
                ),

                "explanation": result.get(
                    "explanation",
                    {},
                ),

                "model": result.get(
                    "model",
                    {},
                ),

                "path": request.path,

                "method": request.method,
            }

        return behavior

    except Exception as exc:

        logger.exception(
            (
                "Failed to persist TokenShield "
                "detection result: %s"
            ),
            exc,
        )

        try:
            db.session.rollback()
        except Exception:
            pass

        return None


# ============================================================================
# LATEST DETECTION
# ============================================================================

def get_latest_detection(
    session_id,
):
    """
    Return the latest detection state for a session.
    """

    with _DETECTION_LOCK:

        value = _LATEST_DETECTION.get(
            str(session_id),
        )

        if not value:
            return None

        return dict(
            value,
        )


# ============================================================================
# ANOMALY WEBHOOK
# ============================================================================

def _send_anomaly_webhook(
    payload,
):
    """
    Send anomaly information asynchronously to the simulation dashboard.
    """

    def _worker():
        try:
            # 1. Direct in-process notification (guaranteed zero latency & no socket error)
            try:
                import app.routes.simulation as sim_mod
                sim_mod.trigger_attack_phase()
                sim_mod._LATEST_ANOMALY = payload
                sim_mod._ATTACK_HISTORY.insert(0, payload)
            except Exception as e:
                logger.debug("In-process simulation notify exception: %s", e)

            # 2. HTTP Webhook notification
            requests.post(
                ANOMALY_WEBHOOK,
                json=payload,
                timeout=2,
            )
        except Exception as exc:
            logger.warning(
                "TokenShield anomaly webhook failed: %s",
                exc,
            )

    thread = threading.Thread(
        target=_worker,
        daemon=True,
        name="tokenshield-anomaly-webhook",
    )

    thread.start()


# ============================================================================
# SESSION REVOCATION
# ============================================================================

def _revoke_all_user_sessions(
    session,
    reason,
):
    """
    Revoke every active session belonging to the affected user.

    This is important for the replay demonstration:

        legitimate session
                  +
        replayed session
                  ↓
        security incident
                  ↓
        all active sessions revoked

    Returns the number of sessions revoked.
    """

    if not session:
        return 0

    try:

        active_sessions = (
            Session.query
            .filter_by(
                user_id=session.user_id,
                is_active=True,
            )
            .all()
        )

        revoked_count = 0

        now = _utc_naive_now()

        for user_session in active_sessions:

            user_session.is_active = False

            user_session.revoked_at = now

            user_session.revoked_reason = reason

            user_session.is_suspicious = True

            current_score = _safe_float(
                user_session.anomaly_score,
            )

            incident_score = _safe_float(
                getattr(
                    session,
                    "anomaly_score",
                    0.0,
                ),
            )

            user_session.anomaly_score = max(
                current_score,
                incident_score,
            )

            revoked_count += 1

        db.session.commit()

        return revoked_count

    except Exception as exc:

        logger.exception(
            (
                "Failed to revoke all active sessions "
                "for user %s: %s"
            ),
            getattr(
                session,
                "user_id",
                None,
            ),
            exc,
        )

        try:
            db.session.rollback()
        except Exception:
            pass

        return 0


# ============================================================================
# MITIGATION
# ============================================================================

def _mitigate(
    session,
    result,
    raw_token=None,
):
    """
    Execute high-confidence containment.

    Mitigation sequence:

        1. Calculate token hash
        2. Revoke compromised session
        3. Revoke all active account sessions
        4. Block compromised token in Redis
        5. Contain device fingerprint
        6. Hard-lock account
        7. Update dashboard state
        8. Publish incident event
    """

    if not session:
        return False

    session_key = str(
        getattr(
            session,
            "id",
            "",
        ),
    )

    # ------------------------------------------------------------------
    # Avoid duplicate mitigation events
    # ------------------------------------------------------------------

    with _DETECTION_LOCK:

        if session_key in _MITIGATED_SESSIONS:

            logger.warning(
                (
                    "TokenShield mitigation already executed "
                    "for session=%s"
                ),
                session_key,
            )

            return False

        _MITIGATED_SESSIONS.add(
            session_key,
        )

    try:

        # --------------------------------------------------------------
        # Token hash
        # --------------------------------------------------------------

        token_hash = _token_hash(
            raw_token,
        )

        client_ip = _request_ip()

        user_agent = _request_user_agent()

        device_fp = _request_device_fingerprint()

        bio_data = _request_biometrics()

        threat_level = result.get(
            "threat_level",
            "critical",
        )

        threat_score = _safe_float(
            result.get(
                "total",
                0.0,
            ),
        )

        revoked_reason = (
            "Security incident: "
            f"{str(threat_level).upper()} "
            "TokenShield anomaly"
        )

        # --------------------------------------------------------------
        # 1. Revoke triggering session
        # --------------------------------------------------------------

        session.is_active = False

        session.revoked_at = _utc_naive_now()

        session.revoked_reason = revoked_reason

        session.anomaly_score = max(
            _safe_float(
                session.anomaly_score,
            ),
            threat_score,
        )

        session.is_suspicious = True

        db.session.commit()

        # --------------------------------------------------------------
        # Incident ID
        # --------------------------------------------------------------

        incident_id = (
            f"{session.user_id}-"
            f"{int(time.time() * 1000)}"
        )

        # --------------------------------------------------------------
        # 2. Revoke ALL active sessions belonging to this account
        # --------------------------------------------------------------

        sessions_revoked = (
            _revoke_all_user_sessions(
                session,
                revoked_reason,
            )
        )

        # --------------------------------------------------------------
        # 3. Redis token blocklist
        # --------------------------------------------------------------

        token_blocked = False

        try:

            from app.middleware.redis_client import (
                get_redis,
            )

            from app.middleware.velocity import (
                BLOCKLIST_PREFIX,
                BLOCKLIST_TTL,
            )

            redis_client = get_redis()

            if (
                redis_client
                and token_hash
            ):

                redis_client.setex(
                    (
                        f"{BLOCKLIST_PREFIX}"
                        f"{token_hash}"
                    ),
                    BLOCKLIST_TTL,
                    "tokenshield_anomaly",
                )

                token_blocked = True

        except Exception as exc:

            logger.warning(
                (
                    "TokenShield token blocklist "
                    "update failed: %s"
                ),
                exc,
            )

        # --------------------------------------------------------------
        # 4. Device fingerprint containment
        # --------------------------------------------------------------

        fingerprint_contained = False

        try:

            from app.middleware.fingerprint import (
                ban_fingerprint,
            )

            if device_fp:

                ban_fingerprint(
                    device_fp,
                    reason=f"TokenShield anomaly: threat_score={threat_score}",
                )

                fingerprint_contained = True

        except Exception as exc:

            logger.warning(
                (
                    "TokenShield fingerprint containment "
                    "failed: %s"
                ),
                exc,
            )

        # --------------------------------------------------------------
        # 5. Account hard lock
        # --------------------------------------------------------------

        account_locked = False

        try:

            from app.middleware.account_lock import (
                hard_lock_account,
            )

            hard_lock_account(
                session.user_id,
                session.id,
                revoked_reason,
            )

            account_locked = True

        except Exception as exc:

            logger.warning(
                (
                    "TokenShield account hard-lock "
                    "failed: %s"
                ),
                exc,
            )

        # --------------------------------------------------------------
        # 5b. Update Simulation Controller Telemetry (Before / During / After)
        # --------------------------------------------------------------
        try:
            from simulation.network_controller import resource_monitor
            resource_monitor.record_attack_event(
                threat_score=threat_score,
                attack_type=revoked_reason or "credential_hijack"
            )
        except Exception as sim_exc:
            logger.debug("Simulation telemetry update error: %s", sim_exc)

        # --------------------------------------------------------------
        # 6. Detailed incident payload
        # --------------------------------------------------------------

        payload = {
            "event": "anomaly_detected",

            "incident_id": incident_id,

            "session_id": str(
                getattr(
                    session,
                    "id",
                    "",
                ),
            ),

            "token_session_reference": str(
                getattr(
                    session,
                    "token",
                    "",
                ),
            ),

            "user_id": str(
                getattr(
                    session,
                    "user_id",
                    "",
                ),
            ),

            "ip": client_ip,

            "user_agent": user_agent,

            "device_fingerprint": device_fp,

            "biometrics": bio_data,

            "path": request.path,

            "method": request.method,

            "signals": _normalize_signals(
                result.get(
                    "signals",
                    {},
                ),
            ),

            "reasons": result.get(
                "reasons",
                [],
            ),

            "threat_score": threat_score,

            "threat_level": threat_level,

            "threshold": ANOMALY_THRESHOLD,

            "engine_mode": result.get(
                "engine_mode",
            ),

            "engine_latency_ms": result.get(
                "engine_latency_ms",
                0.0,
            ),

            "explanation": result.get(
                "explanation",
                {},
            ),

            "model": result.get(
                "model",
                {},
            ),

            "mitigation": {
                "session_revoked": True,

                "sessions_revoked": sessions_revoked,

                "token_invalidated": bool(
                    token_hash,
                ),

                "token_blocked": token_blocked,

                "fingerprint_contained": fingerprint_contained,

                "account_locked": account_locked,

                "requires_admin_unlock": account_locked,
            },
        }

        # --------------------------------------------------------------
        # 7. Update live dashboard state
        # --------------------------------------------------------------

        with _DETECTION_LOCK:

            existing = _LATEST_DETECTION.get(
                str(session.id),
                {},
            )

            _LATEST_DETECTION[
                str(session.id)
            ] = {
                **existing,

                **payload,

                "timestamp": _utc_now().isoformat(),

                "is_threat": True,

                "is_suspicious": True,
            }

        # --------------------------------------------------------------
        # 8. Notify simulation dashboard
        # --------------------------------------------------------------

        _send_anomaly_webhook(
            payload,
        )

        logger.warning(
            (
                "TokenShield MITIGATION: "
                "incident=%s "
                "session=%s "
                "user=%s "
                "score=%.4f "
                "sessions_revoked=%s "
                "account_locked=%s"
            ),
            incident_id,

            getattr(
                session,
                "id",
                None,
            ),

            getattr(
                session,
                "user_id",
                None,
            ),

            threat_score,

            sessions_revoked,

            account_locked,
        )

        return True

    except Exception as exc:

        logger.exception(
            "TokenShield mitigation failed: %s",
            exc,
        )

        # Allow a future request to retry mitigation if the operation failed.
        with _DETECTION_LOCK:
            _MITIGATED_SESSIONS.discard(
                session_key,
            )

        try:
            db.session.rollback()
        except Exception:
            pass

        return False


# ============================================================================
# FLASK MIDDLEWARE INITIALIZATION
# ============================================================================

def init_detection_middleware(
    app,
):
    """
    Install TokenShield detection hooks into Flask.
    """

    @app.before_request
    def tokenshield_before_request():

        path = request.path

        # --------------------------------------------------------------
        # Excluded infrastructure paths
        # --------------------------------------------------------------

        if path == "/health":
            return

        if any(
            path == excluded
            or path.startswith(excluded)
            for excluded in EXCLUDED_PATHS
        ):
            return

        try:

            # ----------------------------------------------------------
            # Resolve authenticated session
            # ----------------------------------------------------------

            session = _get_session_from_request()

            g.tokenshield_detection_session = session

            # Only authenticated sessions are analyzed.
            if not session:
                return

            # ----------------------------------------------------------
            # Never process an already-revoked session.
            # ----------------------------------------------------------

            if hasattr(
                session,
                "is_active",
            ):

                if not session.is_active:
                    return

            # ----------------------------------------------------------
            # Run detection
            # ----------------------------------------------------------

            result = _run_detection(
                session,
            )

            if not result:
                return

            g.tokenshield_detection_result = result

            # ----------------------------------------------------------
            # Persist live detection
            # ----------------------------------------------------------

            _persist_results(
                session,
                result,
            )

            # ----------------------------------------------------------
            # High-confidence anomaly
            # ----------------------------------------------------------

            threat_score = _safe_float(
                result.get(
                    "total",
                    0.0,
                ),
            )

            if threat_score >= ANOMALY_THRESHOLD:

                g.tokenshield_anomaly_detected = True

                _mitigate(
                    session,
                    result,
                    raw_token=_request_raw_token(),
                )

        except Exception as exc:

            # Security monitoring must never crash the entire application.
            logger.exception(
                (
                    "TokenShield detection middleware "
                    "error: %s"
                ),
                exc,
            )

    @app.after_request
    def tokenshield_after_request(
        response,
    ):
        """
        Attach lightweight detection metadata to the response.
        """

        try:

            result = getattr(
                g,
                "tokenshield_detection_result",
                None,
            )

            if result:

                score = _safe_float(
                    result.get(
                        "total",
                        0.0,
                    ),
                )

                response.headers[
                    "X-TokenShield-Score"
                ] = str(
                    score,
                )

                response.headers[
                    "X-TokenShield-Status"
                ] = (
                    "ANOMALY"
                    if score >= ANOMALY_THRESHOLD
                    else "MONITORING"
                )

        except Exception:
            pass

        return response

    logger.info(
        (
            "TokenShield detection middleware initialized "
            "(threshold=%.2f, engine=%s)"
        ),
        ANOMALY_THRESHOLD,
        ENGINE_URL,
    )