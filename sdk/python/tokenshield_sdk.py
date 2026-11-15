"""
TokenShield Python SDK  v2.0.0
==============================
Integrate TokenShield real-time AI threat defense and zero-trust session
verification into any Python web application (Flask, FastAPI, Django, etc.)
in under 10 lines of code.

Banking Platform Integration:
    from tokenshield_sdk import TokenShieldClient

    ts = TokenShieldClient(
        engine_url="http://your-engine:7777",
        api_key="ts_live_abc123"
    )

    # On every payment:
    decision = ts.inspect_request(
        session_id=session_id, ip=client_ip, path="/api/payments/wire",
        method="POST", payload=request_body
    )

    if decision.action == "block":
        return {"error": "Blocked by TokenShield"}, 403
    elif decision.action == "challenge":
        trigger_step_up_auth()

Flask Middleware (auto-wrap all routes):
    from flask import Flask, request, jsonify
    from tokenshield_sdk import TokenShieldClient

    app = Flask(__name__)
    shield = TokenShieldClient(engine_url="http://localhost:7777")

    @app.before_request
    def security_check():
        decision = shield.inspect_flask_request(request)
        if decision.should_block:
            return jsonify({
                "error": "Access Denied by TokenShield",
                "threat_level": decision.threat_level,
                "reasons": decision.reasons
            }), 403

API Reference: See TOKENSHIELD_PUBLIC_API.md
Engine URL:    http://localhost:7777 (default)
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

log = logging.getLogger("tokenshield.sdk")


@dataclass
class TokenShieldDecision:
    threat_score: float
    threat_level: str
    action: str  # "allow", "challenge", "block"
    should_block: bool
    reasons: List[str]
    signals: Dict[str, float]
    latency_ms: float
    explanation: Dict[str, Any]

    @property
    def is_safe(self) -> bool:
        return self.action == "allow"


class TokenShieldClient:
    def __init__(
        self,
        engine_url: str = "http://localhost:7777",
        api_key: Optional[str] = None,
        timeout: float = 0.25,  # 250ms max timeout to never block user UX
        fail_open: bool = True   # If engine is offline, allow traffic and log alert
    ):
        self.engine_url = engine_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.fail_open = fail_open

        if not _HAS_REQUESTS:
            log.warning(
                "Python 'requests' library not found. "
                "Install with: pip install requests"
            )

    def inspect_request(
        self,
        session_id: str,
        ip: str,
        path: str = "/",
        method: str = "GET",
        user_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        payload: Optional[str] = None,
        biometrics: Optional[Dict[str, Any]] = None,
        status_code: int = 200
    ) -> TokenShieldDecision:
        """
        Inspects an arbitrary request against TokenShield's ML threat engine.
        """
        payload_data = {
            "session_id": session_id,
            "user_id": user_id,
            "ip": ip,
            "user_agent": user_agent or "",
            "path": path,
            "method": method,
            "headers": headers or {},
            "payload": payload,
            "biometrics": biometrics,
            "status_code": status_code
        }

        req_headers = {"Content-Type": "application/json"}

        if self.api_key:
            req_headers["X-API-Key"] = self.api_key

        t0 = time.perf_counter()

        try:
            res = requests.post(
                f"{self.engine_url}/api/v1/analyze",
                json=payload_data,
                headers=req_headers,
                timeout=self.timeout
            )

            if res.status_code == 200:
                data = res.json()

                return TokenShieldDecision(
                    threat_score=data["threat_score"],
                    threat_level=data["threat_level"],
                    action=data["action"],
                    should_block=data["action"] == "block",
                    reasons=data["reasons"],
                    signals=data["signals"],
                    latency_ms=data["latency_ms"],
                    explanation=data["explanation"]
                )

            else:
                log.error(
                    f"TokenShield engine returned HTTP "
                    f"{res.status_code}: {res.text}"
                )

        except Exception as e:
            log.error(
                f"Failed to communicate with TokenShield engine: {e}"
            )

        # Fallback if engine is down/unreachable
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if self.fail_open:
            return TokenShieldDecision(
                threat_score=0.0,
                threat_level="safe",
                action="allow",
                should_block=False,
                reasons=["engine_unreachable_fail_open"],
                signals={},
                latency_ms=elapsed_ms,
                explanation={
                    "summary":
                        "Engine offline. Allowed via fail-open policy."
                }
            )

        else:
            return TokenShieldDecision(
                threat_score=1.0,
                threat_level="critical",
                action="block",
                should_block=True,
                reasons=["engine_unreachable_fail_closed"],
                signals={},
                latency_ms=elapsed_ms,
                explanation={
                    "summary":
                        "Engine offline. Blocked via fail-closed policy."
                }
            )

    def inspect_flask_request(
        self,
        flask_req,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> TokenShieldDecision:
        """
        Helper method specifically for Flask apps.

        Automatically extracts:
        - IP address
        - User-Agent
        - request headers
        - request body
        - behavioral biometrics
        - session identifier
        """

        ip = flask_req.headers.get(
            "X-Forwarded-For",
            flask_req.remote_addr
        )

        if ip and "," in ip:
            ip = ip.split(",")[0].strip()

        # Extract biometrics from header
        bio = None

        bio_header = flask_req.headers.get("X-TS-Biometrics")

        if bio_header:
            try:
                bio = json.loads(bio_header)
            except Exception:
                pass

        # Extract body payload
        payload_str = None

        if flask_req.is_json:
            try:
                payload_str = json.dumps(
                    flask_req.get_json(silent=True) or {}
                )
            except Exception:
                pass

        elif flask_req.data:
            try:
                payload_str = flask_req.data.decode(
                    "utf-8",
                    errors="ignore"
                )[:4096]
            except Exception:
                pass

        sid = (
            session_id
            or flask_req.cookies.get("session")
            or flask_req.headers.get("Authorization", "anon")
        )

        return self.inspect_request(
            session_id=sid,
            ip=ip or "127.0.0.1",
            path=flask_req.path,
            method=flask_req.method,
            user_id=user_id,
            user_agent=flask_req.headers.get("User-Agent"),
            headers=dict(flask_req.headers),
            payload=payload_str,
            biometrics=bio
        )

    def register_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        ip: str = "127.0.0.1",
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
    ) -> bool:
        """
        Notifies TokenShield of a new authenticated session creation.

        The device fingerprint and User-Agent are stored with the
        legitimate session baseline so that a later request using the
        same session token from another device can be detected.
        """

        try:
            res = requests.post(
                f"{self.engine_url}/api/v1/register-session",
                json={
                    "session_id": session_id,
                    "user_id": user_id,
                    "ip": ip,
                    "user_agent": user_agent,
                    "device_fingerprint": device_fingerprint,
                },
                headers={
                    "Content-Type": "application/json"
                },
                timeout=self.timeout
            )

            return res.status_code in (200, 201)

        except Exception as e:
            log.debug(
                f"Failed to register session: {e}"
            )
            return False

    def revoke_session(
        self,
        session_id: str
    ) -> bool:
        """
        Immediately blacklists and revokes a session across
        TokenShield and edge caches.
        """

        try:
            res = requests.post(
                f"{self.engine_url}/api/v1/revoke-session",
                json={
                    "session_id": session_id
                },
                headers={
                    "Content-Type": "application/json"
                },
                timeout=self.timeout
            )

            return res.status_code == 200

        except Exception as e:
            log.debug(
                f"Failed to revoke session: {e}"
            )
            return False

    def get_session_score(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves active security posture and threat level
        for a session.
        """

        try:
            res = requests.get(
                f"{self.engine_url}/api/v1/session/{session_id}/score",
                timeout=self.timeout
            )

            return (
                res.json()
                if res.status_code == 200
                else None
            )

        except Exception:
            return None

    def get_stats(
        self
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves global telemetry and latency metrics
        from TokenShield engine.
        """

        try:
            res = requests.get(
                f"{self.engine_url}/api/v1/stats",
                timeout=self.timeout
            )

            return (
                res.json()
                if res.status_code == 200
                else None
            )

        except Exception:
            return None

    def report_biometrics(
        self,
        user_id: str,
        biometrics: Dict[str, Any]
    ) -> bool:
        """
        Sends background biometric telemetry to TokenShield
        to establish/update a user's behavioral baseline during
        warm-up without running threat scoring.
        """

        try:
            res = requests.post(
                f"{self.engine_url}/api/v1/biometric-update",
                json={
                    "user_id": user_id,
                    "metrics": biometrics
                },
                headers={
                    "Content-Type": "application/json"
                },
                timeout=self.timeout
            )

            return res.status_code == 200

        except Exception as e:
            log.debug(
                f"Failed to report biometrics: {e}"
            )
            return False


    # ── Additional convenience methods (v2.0.0) ───────────────────────

    def get_incidents(
        self,
        limit: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        Returns recent security incidents from the engine.
        Useful for SIEM/SOC dashboard integration.
        """
        try:
            hdrs = {"X-API-Key": self.api_key} if self.api_key else {}
            res = requests.get(
                f"{self.engine_url}/api/v1/incidents",
                params={"limit": limit},
                headers=hdrs,
                timeout=self.timeout
            )
            return res.json() if res.status_code == 200 else None
        except Exception:
            return None

    def get_forensic_report(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves a full forensic audit report for the most recent attack.
        Includes threat actor profile, geo, mitigation timeline, executive summary.
        """
        try:
            hdrs = {"X-API-Key": self.api_key} if self.api_key else {}
            res = requests.get(
                f"{self.engine_url}/api/v1/incidents/latest/report",
                headers=hdrs,
                timeout=self.timeout
            )
            return res.json() if res.status_code == 200 else None
        except Exception:
            return None

    def whitelist_ip(self, ip: str) -> bool:
        """
        Whitelists an IP address — bypasses all threat scoring.
        Use for SOC/admin staff IPs. Use with caution.
        """
        try:
            hdrs = {"X-API-Key": self.api_key} if self.api_key else {}
            res = requests.post(
                f"{self.engine_url}/api/v1/admin/whitelist-ip",
                json={"ip": ip},
                headers=hdrs,
                timeout=self.timeout
            )
            return res.status_code == 200
        except Exception:
            return False

    def unlock_user(self, user_id: str) -> bool:
        """
        Unlocks a user account locked by automated mitigation.
        Call from admin panel after verifying user identity.
        """
        try:
            hdrs = {"X-API-Key": self.api_key} if self.api_key else {}
            res = requests.post(
                f"{self.engine_url}/api/v1/admin/unlock/{user_id}",
                headers=hdrs,
                timeout=self.timeout
            )
            return res.status_code == 200
        except Exception:
            return False

    def get_defense_layers(self) -> Optional[Dict[str, Any]]:
        """
        Returns live status of all 7 banking defense layers.
        Use for health dashboards or pre-flight checks.
        """
        try:
            hdrs = {"X-API-Key": self.api_key} if self.api_key else {}
            res = requests.get(
                f"{self.engine_url}/api/v1/layers",
                headers=hdrs,
                timeout=self.timeout
            )
            return res.json() if res.status_code == 200 else None
        except Exception:
            return None

    def is_healthy(self) -> bool:
        """
        Quick liveness check — returns True if engine is online
        and all 3 ML models (Isolation Forest, LSTM, Meta-Classifier) are ready.
        """
        try:
            res = requests.get(
                f"{self.engine_url}/health",
                timeout=self.timeout
            )
            if res.status_code != 200:
                return False
            data = res.json()
            if data.get("status") != "online":
                return False
            models = data.get("models", {})
            return all(m.get("loaded", False) for m in models.values())
        except Exception:
            return False