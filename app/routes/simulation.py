"""
TokenShield Simulation Routes
=============================
Provides real-time host resource telemetry (psutil), network simulation
phases, side-by-side session comparison, and mitigation state tracking
for the TokenShield Simulation Dashboard.

All metrics are real (psutil); no artificial or random spikes are generated.
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, session as flask_session

from app.extensions import db
from app.models import BehaviorLog, IncidentLog, Session, User
from simulation.network_controller import (
    resource_monitor,
    gns3_controller,
    trigger_attack_phase,
    trigger_mitigation_phase,
    reset_simulation,
    PHASE_NORMAL,
    PHASE_UNDER_ATTACK,
    PHASE_POST_MITIGATION,
)

logger = logging.getLogger(__name__)

simulation_bp = Blueprint(
    "simulation",
    __name__,
    url_prefix="/api/simulation",
)

# Configuration
ENGINE_URL = os.getenv("TOKENSHIELD_ENGINE_URL", "http://127.0.0.1:7777")
ANOMALY_THRESHOLD = float(os.getenv("TOKENSHIELD_ANOMALY_THRESHOLD", "0.85"))

# Runtime incident memory for live comparison
_LATEST_ANOMALY = None
_ATTACK_HISTORY = []      # list of raw engine incidents (latest first)
_MAX_ATTACK_HISTORY = 50

# Per-attack before/during/after telemetry records (newest first)
# Each entry: { id, attack_type, severity, threat_score, ip, started_at,
#               before: {ts, cpu, ram_pct, ram_gb}, during: {...}, after: {...} }
_ATTACK_TELEMETRY = []
_MAX_TELEMETRY = 50


def _utc_now():
    return datetime.now(timezone.utc)


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _json_value(value):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    return str(value)


def _hash_token(raw_token):
    if not raw_token:
        return None
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _request_raw_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token
    for cookie_name in ("access_token", "token", "session_token"):
        token = request.cookies.get(cookie_name)
        if token:
            return token
    return None


# ============================================================================
# HOST RESOURCE TELEMETRY (psutil) — Public endpoints for simulation dashboard
# ============================================================================

@simulation_bp.route("/current", methods=["GET"])
def get_current():
    """Returns current real host resource snapshot (psutil)."""
    snapshot = resource_monitor.current()
    if not snapshot:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "phase": resource_monitor._phase,
            "cpu_percent": cpu,
            "ram_percent": ram,
            "net_sent_kb": 0.0,
            "net_recv_kb": 0.0,
            "connections": len(psutil.net_connections(kind="inet")),
        }
    return jsonify({"success": True, "snapshot": snapshot}), 200


@simulation_bp.route("/history", methods=["GET"])
def get_history():
    """Returns last N psutil snapshots for line charts."""
    try:
        n = min(int(request.args.get("n", 60)), 120)
    except (TypeError, ValueError):
        n = 60
    snapshots = resource_monitor.history(n)
    if not snapshots:
        curr = resource_monitor.current()
        if curr:
            snapshots = [curr]
    return jsonify({
        "success": True,
        "count": len(snapshots),
        "snapshots": snapshots,
    }), 200


@simulation_bp.route("/comparison", methods=["GET"])
def get_comparison():
    """Returns Before / During / After phase averages."""
    comparison = resource_monitor.comparison()
    return jsonify({"success": True, "comparison": comparison}), 200


@simulation_bp.route("/topology", methods=["GET"])
def get_topology():
    """Returns GNS3 topology structure."""
    topology = gns3_controller.get_topology()
    return jsonify({"success": True, "topology": topology}), 200


@simulation_bp.route("/status", methods=["GET"])
def get_status():
    """Returns overall simulation status & health."""
    snapshot = resource_monitor.current()
    phase = resource_monitor._phase
    return jsonify({
        "success": True,
        "status": {
            "phase": phase,
            "gns3_connected": gns3_controller.connected,
            "monitor_running": resource_monitor._running,
            "phase_timestamps": resource_monitor.phase_timestamps(),
            "current_snapshot": snapshot,
            "latest_anomaly": _LATEST_ANOMALY,
        }
    }), 200


@simulation_bp.route("/stats-summary", methods=["GET"])
def get_stats_summary():
    """
    Returns real database statistics for the simulation dashboard.
    No auth required so operational dashboard views stay in sync.
    """
    active_sessions = Session.query.filter_by(is_active=True).count()
    total_sessions = Session.query.count()

    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    incidents_24h = IncidentLog.query.filter(IncidentLog.timestamp >= cutoff_24h).count()
    total_incidents = IncidentLog.query.count()

    cutoff_1h = datetime.utcnow() - timedelta(hours=1)
    recent_incidents = IncidentLog.query.filter(
        IncidentLog.timestamp >= cutoff_1h,
        IncidentLog.anomaly_score > 0
    ).all()

    avg_anomaly = 0.0
    if recent_incidents:
        scores = [i.anomaly_score for i in recent_incidents if i.anomaly_score]
        if scores:
            avg_anomaly = round(sum(scores) / len(scores), 4)

    return jsonify({
        "success": True,
        "stats": {
            "sessions": {
                "active": active_sessions,
                "total": total_sessions
            },
            "incidents": {
                "recent_24h": incidents_24h,
                "total": total_incidents
            },
            "avg_anomaly_score": avg_anomaly
        }
    }), 200


@simulation_bp.route("/incidents", methods=["GET"])
def get_simulation_incidents():
    """
    Returns recent incident feed from real database logs.
    """
    limit = min(int(request.args.get("limit", 20)), 100)
    logs = (
        IncidentLog.query
        .order_by(IncidentLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return jsonify({
        "success": True,
        "incidents": [log.to_dict() for log in logs]
    }), 200


# ============================================================================
# LIVE SESSION COMPARISON (Legitimate User vs Attacker)
# ============================================================================

@simulation_bp.route("/live-comparison", methods=["GET"])
def get_live_comparison():
    """
    Returns side-by-side telemetry of Legitimate User vs Detected Attacker.
    No strict auth is required so presenter dashboards can poll seamlessly.
    """
    global _LATEST_ANOMALY

    # 1. Resolve legitimate user profile
    legit_profile = {
        "user": "alice_demo",
        "ip": "127.0.0.1 (Authorized MacBook)",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "fingerprint": "fp_macbook_alice_982b",
        "location": "Authorized Home / Office (Pune, IN)",
        "status": "ACTIVE",
        "token_status": "Authenticated",
        "active": True,
        "typing_wpm": 63.4,
        "avg_key_hold_ms": 96.2,
        "mouse_speed": "224 px/s",
        "anomaly_score": 0.02,
        "signals": {
            "ip_reputation": 0.0,
            "request_velocity": 0.0,
            "session_consistency": 0.0,
            "payload_analysis": 0.0,
            "behavioral_biometrics": 0.02,
            "geographic_impossibility": 0.0,
            "endpoint_risk": 0.0,
            "sequential_behavior": 0.01,
        }
    }

    # Pull real active session from DB if available
    try:
        alice = User.query.filter_by(username="alice_demo").first()
        target_user = alice or User.query.filter_by(is_admin=False).first()
        if target_user:
            active_sess = (
                Session.query
                .filter_by(user_id=target_user.id)
                .order_by(Session.created_at.desc())
                .first()
            )
            if active_sess:
                legit_profile["user"] = target_user.username
                if active_sess.ip_address:
                    legit_profile["ip"] = f"{active_sess.ip_address} (Registered MacBook)"
                if active_sess.user_agent:
                    legit_profile["user_agent"] = active_sess.user_agent
                if hasattr(active_sess, "device_fingerprint") and active_sess.device_fingerprint:
                    legit_profile["fingerprint"] = active_sess.device_fingerprint
                legit_profile["active"] = bool(active_sess.is_active)
                legit_profile["status"] = "ACTIVE" if active_sess.is_active else "REVOKED"
                legit_profile["token_status"] = "Authenticated" if active_sess.is_active else "REVOKED BY TOKENSHIELD"
                if active_sess.anomaly_score is not None:
                    legit_profile["anomaly_score"] = float(active_sess.anomaly_score)

                # Real behavioral telemetry from BehaviorLog
                last_log = (
                    BehaviorLog.query
                    .filter_by(session_id=active_sess.id)
                    .order_by(BehaviorLog.id.desc())
                    .first()
                )
                if last_log and last_log.fingerprint_data:
                    try:
                        fp_data = json.loads(last_log.fingerprint_data)
                        if isinstance(fp_data, dict):
                            bio = fp_data.get("biometrics") or fp_data
                            if bio.get("typing_wpm"):
                                legit_profile["typing_wpm"] = round(float(bio["typing_wpm"]), 1)
                            if bio.get("keypress_dwell_ms") or bio.get("avg_key_hold_ms"):
                                legit_profile["avg_key_hold_ms"] = round(float(bio.get("keypress_dwell_ms") or bio.get("avg_key_hold_ms")), 1)
                            if bio.get("mouse_velocity_mean"):
                                legit_profile["mouse_speed"] = f"{round(float(bio['mouse_velocity_mean']), 1)} px/s"
                    except Exception:
                        pass
    except Exception as exc:
        logger.debug("Could not resolve active session from DB: %s", exc)

    # 2. Resolve attacker profile
    attacker_incident = None

    # Check in-memory webhook payload first
    if _LATEST_ANOMALY and _LATEST_ANOMALY.get("threat_score"):
        attacker_incident = _LATEST_ANOMALY

    # If no in-memory payload, check latest revoked incident from DB
    if not attacker_incident:
        try:
            cutoff = datetime.utcnow() - timedelta(minutes=45)
            inc = (
                IncidentLog.query
                .filter(IncidentLog.timestamp >= cutoff)
                .order_by(IncidentLog.timestamp.desc())
                .first()
            )
            if inc:
                details = {}
                try:
                    details = json.loads(inc.details or "{}")
                except Exception:
                    pass
                score = float(inc.anomaly_score or 0.88)
                level = "critical" if score >= 0.85 else ("high" if score >= 0.7 else "elevated")
                attacker_incident = {
                    "threat_score": score,
                    "threat_level": level,
                    "ip": inc.ip_address or "192.168.31.210",
                    "user_id": str(inc.session_id or "alice_demo"),
                    "signals": details.get("signals", {}),
                    "reasons": details.get("reasons", [
                        "ip_changed", "device_fingerprint_mismatch",
                        "missing_behavioral_biometrics", "sequential_jump"
                    ]),
                    "timestamp": inc.timestamp.isoformat() if inc.timestamp else datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.debug("Could not load incident from DB: %s", exc)

    attacker_profile = None
    is_anomaly = False

    if attacker_incident and attacker_incident.get("threat_score"):
        score = float(attacker_incident.get("threat_score", 0.90))
        if score >= 0.70:
            is_anomaly = True
            sigs = attacker_incident.get("signals", {})
            atk_bio = attacker_incident.get("biometrics") or {}
            atk_wpm = float(atk_bio.get("typing_wpm", 0.0))
            atk_hold = float(atk_bio.get("keypress_dwell_ms", atk_bio.get("avg_key_hold_ms", 0.0)))
            atk_mouse_v = float(atk_bio.get("mouse_velocity_mean", 0.0))
            atk_mouse_str = f"{atk_mouse_v:.1f} px/s" if atk_mouse_v > 0 else "0 px/s (Zero Motion Bot)"
            atk_ua = attacker_incident.get("user_agent") or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
            atk_ip = attacker_incident.get("ip", "192.168.31.210")
            atk_fp = attacker_incident.get("device_fingerprint") or "fp_unregistered_attacker"

            attacker_profile = {
                "user": f"{attacker_incident.get('user_id', 'alice_demo')} (Stolen Token)",
                "ip": f"{atk_ip} (Unauthorized Remote Device)",
                "user_agent": atk_ua,
                "fingerprint": atk_fp,
                "location": "Different Network / Subnet Discrepancy",
                "status": f"🚨 ANOMALY DETECTED ({attacker_incident.get('threat_level', 'CRITICAL').upper()})",
                "token_status": "TOKEN REVOKED",
                "active": False,
                "threat_score": score,
                "anomaly_score": score,
                "typing_wpm": atk_wpm,
                "avg_key_hold_ms": atk_hold,
                "mouse_speed": atk_mouse_str,
                "reasons": attacker_incident.get("reasons", []),
                "timestamp": attacker_incident.get("timestamp"),
                "signals": {
                    "ip_reputation": round(float(sigs.get("ip_reputation", 0.0)), 4),
                    "request_velocity": round(float(sigs.get("request_velocity", 0.0)), 4),
                    "session_consistency": round(float(sigs.get("session_consistency", 0.0)), 4),
                    "payload_analysis": round(float(sigs.get("payload_analysis", 0.0)), 4),
                    "behavioral_biometrics": round(float(sigs.get("behavioral_biometrics", 0.0)), 4),
                    "geographic_impossibility": round(float(sigs.get("geographic_impossibility", 0.0)), 4),
                    "endpoint_risk": round(float(sigs.get("endpoint_risk", sigs.get("endpoint_pattern", 0.0))), 4),
                    "sequential_behavior": round(float(sigs.get("sequential_behavior", 0.0)), 4),
                },
            }

    return jsonify({
        "success": True,
        "anomaly_present": is_anomaly,
        "detected": is_anomaly,
        "threshold": ANOMALY_THRESHOLD,
        "anomaly_score": attacker_profile.get("threat_score") if attacker_profile else legit_profile.get("anomaly_score", 0.0),
        "legitimate": legit_profile,
        "attacker": attacker_profile,
        "phase": resource_monitor._phase,
    }), 200


# ============================================================================
# WEBHOOK FOR ENGINE / DETECTION ANOMALY
# ============================================================================

@simulation_bp.route("/engine-anomaly", methods=["POST"])
def engine_anomaly():
    """
    Called automatically by TokenShield engine or middleware when a threat is detected.
    Flips simulation phase to under_attack, captures before/during/after CPU+RAM telemetry
    with accurate timestamps, and stores the full record for the simulation dashboard.
    """
    global _LATEST_ANOMALY, _ATTACK_TELEMETRY
    import threading, psutil

    data = request.get_json(force=True, silent=True) or {}

    # ── Snapshot BEFORE (last normal snapshot) ────────────────────────────────
    before_snap = resource_monitor.current() or {}
    before_mem  = psutil.virtual_memory()
    before_rec = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cpu_percent": round(before_snap.get("cpu_percent", psutil.cpu_percent(interval=None)), 1),
        "ram_percent": round(before_snap.get("ram_percent", before_mem.percent), 1),
        "ram_used_gb": round(before_snap.get("ram_used_gb", (before_mem.total - before_mem.available) / 1024**3), 2),
        "ram_total_gb": round(before_snap.get("ram_total_gb", before_mem.total / 1024**3), 1),
    }

    # ── Trigger attack telemetry lifecycle ───────────────────────────────────
    trigger_attack_phase()

    # ── Build incident record ─────────────────────────────────────────────────
    inc_id = data.get("incident_id", f"inc_{int(time.time()*1000)}")
    attack_rec = {
        "id": inc_id,
        "attack_type": (data.get("reasons") or ["unknown"])[0],
        "severity": data.get("threat_level", "critical"),
        "threat_score": round(float(data.get("threat_score", 0.92)), 4),
        "ip": data.get("ip", request.remote_addr),
        "user_id": data.get("user_id"),
        "signals": data.get("signals", {}),
        "started_at": datetime.utcnow().isoformat() + "Z",
        "before": before_rec,
        "during": None,   # filled by background thread
        "after":  None,   # filled by background thread
    }

    _LATEST_ANOMALY = {
        "timestamp": datetime.utcnow().isoformat(),
        "incident_id": inc_id,
        "threat_score": data.get("threat_score", 0.92),
        "threat_level": data.get("threat_level", "critical"),
        "ip": data.get("ip", request.remote_addr),
        "session_id": data.get("session_id"),
        "user_id": data.get("user_id"),
        "signals": data.get("signals", {}),
        "reasons": data.get("reasons", ["ip_changed", "missing_biometrics"]),
        "threshold": ANOMALY_THRESHOLD,
    }

    _ATTACK_HISTORY.insert(0, _LATEST_ANOMALY)
    del _ATTACK_HISTORY[_MAX_ATTACK_HISTORY:]

    _ATTACK_TELEMETRY.insert(0, attack_rec)
    del _ATTACK_TELEMETRY[_MAX_TELEMETRY:]

    # ── Background: capture DURING then AFTER snapshots ──────────────────────
    def _capture_later():
        # During — peak attack phase (~2s in)
        time.sleep(2.5)
        snap_d = resource_monitor.current() or {}
        mem_d  = psutil.virtual_memory()
        attack_rec["during"] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cpu_percent": round(snap_d.get("cpu_percent", psutil.cpu_percent(interval=None)), 1),
            "ram_percent": round(snap_d.get("ram_percent", mem_d.percent), 1),
            "ram_used_gb": round(snap_d.get("ram_used_gb", (mem_d.total - mem_d.available) / 1024**3), 2),
            "ram_total_gb": round(snap_d.get("ram_total_gb", mem_d.total / 1024**3), 1),
        }
        # After — post-mitigation (~7s total)
        time.sleep(5)
        snap_a = resource_monitor.current() or {}
        mem_a  = psutil.virtual_memory()
        attack_rec["after"] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cpu_percent": round(snap_a.get("cpu_percent", psutil.cpu_percent(interval=None)), 1),
            "ram_percent": round(snap_a.get("ram_percent", mem_a.percent), 1),
            "ram_used_gb": round(snap_a.get("ram_used_gb", (mem_a.total - mem_a.available) / 1024**3), 2),
            "ram_total_gb": round(snap_a.get("ram_total_gb", mem_a.total / 1024**3), 1),
        }

    threading.Thread(target=_capture_later, daemon=True).start()

    return jsonify({
        "success": True,
        "phase": PHASE_UNDER_ATTACK,
        "stored": True,
        "incident_id": inc_id,
    }), 200


@simulation_bp.route("/attack-history", methods=["GET"])
def get_attack_history():
    """
    Returns per-attack before/during/after CPU & RAM telemetry with accurate timestamps.
    Used by the simulation dashboard Attack History panel.
    """
    limit = min(int(request.args.get("limit", 20)), _MAX_TELEMETRY)
    records = _ATTACK_TELEMETRY[:limit]
    return jsonify({"success": True, "count": len(records), "attacks": records}), 200




# ============================================================================
# SIMULATION CONTROLS (Phase Switching & Reset)
# ============================================================================

@simulation_bp.route("/start-attack", methods=["POST"])
def start_attack():
    trigger_attack_phase()
    return jsonify({
        "success": True,
        "phase": PHASE_UNDER_ATTACK,
        "timestamp": datetime.utcnow().isoformat(),
    }), 200


@simulation_bp.route("/mitigate", methods=["POST"])
def mitigate():
    trigger_mitigation_phase()
    return jsonify({
        "success": True,
        "phase": PHASE_POST_MITIGATION,
        "timestamp": datetime.utcnow().isoformat(),
    }), 200


@simulation_bp.route("/reset", methods=["POST"])
def reset():
    global _LATEST_ANOMALY
    reset_simulation()
    _LATEST_ANOMALY = None

    # Re-enable demo users so the demonstration can be re-run cleanly
    try:
        alice = User.query.filter_by(username="alice_demo").first()
        if alice:
            alice.is_active = True
            alice.failed_login_attempts = 0
            if hasattr(alice, "requires_2fa"):
                alice.requires_2fa = False
            db.session.commit()
    except Exception as exc:
        logger.debug("Failed to unlock alice_demo during reset: %s", exc)

    return jsonify({
        "success": True,
        "phase": PHASE_NORMAL,
        "timestamp": datetime.utcnow().isoformat(),
    }), 200


@simulation_bp.route("/run-attack", methods=["POST"])
def run_attack():
    """
    Triggers simulated attack scenario and sets phase to under_attack.
    """
    trigger_attack_phase()
    global _LATEST_ANOMALY
    _LATEST_ANOMALY = {
        "timestamp": datetime.utcnow().isoformat(),
        "threat_score": 0.93,
        "threat_level": "critical",
        "ip": "192.168.31.210",
        "signals": {
            "ip_reputation": 0.10,
            "request_velocity": 0.25,
            "session_consistency": 0.90,
            "payload_analysis": 0.0,
            "behavioral_biometrics": 1.0,
            "geographic_impossibility": 0.85,
            "endpoint_risk": 0.40,
            "sequential_behavior": 0.70,
        },
        "reasons": [
            "ip_changed:192.168.31.194→192.168.31.210",
            "device_fingerprint_mismatch",
            "behavioral_biometrics_missing",
            "sequential_jump:direct_to_transfer",
        ],
        "threshold": ANOMALY_THRESHOLD,
    }
    return jsonify({
        "success": True,
        "phase": PHASE_UNDER_ATTACK,
        "anomaly_score": 0.93,
        "detected": True,
    }), 200


@simulation_bp.route("/one-computer-replay", methods=["POST"])
def one_computer_replay():
    """Compatibility handler for controlled replay."""
    return run_attack()
