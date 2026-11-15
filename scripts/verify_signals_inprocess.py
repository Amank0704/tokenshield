"""
TokenShield — In-Process 8-Signal & Layer Automated Verification Suite
======================================================================
Tests all 8 signals, 7 defense layers, and ML ensemble directly
using the Flask test_client (deterministic, 0 network dependency).
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.server_flask import app

def run_suite():
    print("\n" + "═" * 70)
    print("  🛡️  TokenShield 8-Signal & Layer Verification Suite (In-Process)")
    print("═" * 70 + "\n")

    client = app.test_client()

    # Health check
    res = client.get("/health")
    h = res.get_json()
    print(f"[*] Engine Status: {h.get('status').upper()} (v{h.get('version')})")
    print(f"    Isolation Forest : {h.get('models', {}).get('isolation_forest', {}).get('status')}")
    print(f"    Meta-Classifier  : {h.get('models', {}).get('meta_classifier', {}).get('status')}")
    print(f"    LSTM Autoencoder : {h.get('models', {}).get('lstm_autoencoder', {}).get('status')}\n")

    results = []
    ts = int(time.time() * 1000)

    def test(name, payload, signal_key, expected_min, desc):
        print(f"▶ Testing {name} ({desc})...", end=" ")
        r = client.post("/api/v1/analyze", json=payload)
        data = r.get_json() or {}
        val = data.get("signals", {}).get(signal_key, 0.0)
        action = data.get("action", "allow")
        score = data.get("threat_score", 0.0)
        if val >= expected_min:
            print(f"✅ PASS (Signal: {val:.2f} >= {expected_min:.2f} | Action: {action.upper()} | Score: {score:.2f})")
            return True
        else:
            print(f"⚠️ LOW (Signal: {val:.2f} < {expected_min:.2f} | Action: {action.upper()})")
            return False

    # S1: IP Reputation
    tor_ip = f"185.220.101.{(ts % 240) + 10}"
    results.append(test("Signal 1: IP Reputation", {"session_id": f"s1_{ts}", "ip": tor_ip, "path": "/"}, "ip_reputation", 0.70, f"Tor Node {tor_ip}"))

    # S2: Velocity Burst
    v_ip = f"172.16.50.{(ts % 200) + 10}"
    v_sess = f"s2_{ts}"
    for _ in range(25):
        client.post("/api/v1/analyze", json={"session_id": v_sess, "ip": v_ip, "path": "/api/dashboard/stats"})
    results.append(test("Signal 2: Request Velocity", {"session_id": v_sess, "ip": v_ip, "path": "/api/dashboard/stats"}, "request_velocity", 0.25, "Burst 26 rapid requests"))

    # S3: Session Consistency
    drift_sess = f"s3_{ts}"
    client.post("/api/v1/analyze", json={"session_id": drift_sess, "ip": "103.21.58.1", "user_agent": "Mozilla/5.0 Clean", "path": "/"})
    results.append(test("Signal 3: Session Drift", {"session_id": drift_sess, "ip": "185.220.101.5", "user_agent": "curl/7.68 Hijacker", "path": "/"}, "session_consistency", 0.80, "IP + UA Hijack Drift"))

    # S4: Payload Analysis
    results.append(test("Signal 4: Payload Inspection", {"session_id": f"s4_{ts}", "ip": "127.0.0.1", "path": "/api/banking/search", "payload": "' OR '1'='1' UNION SELECT username,password FROM users--"}, "payload_analysis", 0.85, "SQLi Union Extraction"))

    # S5: Behavioral Biometrics
    results.append(test("Signal 5: Bot Biometrics", {"session_id": f"s5_{ts}", "user_id": "alice@neovault.com", "ip": "127.0.0.1", "path": "/", "biometrics": {"typing_wpm": 285.0, "typing_rhythm_cv": 0.001, "mouse_velocity_mean": 0.0, "mouse_velocity_cv": 0.0, "idle_time_ratio": 0.0}}, "behavioral_biometrics", 0.80, "Machine Speed 285 WPM Bot"))

    # S6: Impossible Travel (Mumbai -> Amsterdam in 0.5s)
    geo_sess = f"s6_{ts}"
    client.post("/api/v1/analyze", json={"session_id": geo_sess, "ip": "103.21.58.1", "path": "/"})
    time.sleep(0.05)
    results.append(test("Signal 6: Impossible Travel", {"session_id": geo_sess, "ip": "185.107.80.12", "path": "/"}, "geographic_impossibility", 0.80, "Mumbai -> Amsterdam in 50ms"))

    # S7: Endpoint Risk
    results.append(test("Signal 7: Endpoint Risk", {"session_id": f"s7_{ts}", "ip": "127.0.0.1", "path": "/api/banking/transfer/execute", "method": "POST"}, "endpoint_risk", 0.35, "POST /api/banking/transfer/execute"))

    # S8: Sequential Behavior
    results.append(test("Signal 8: Sequential Anomaly", {"session_id": f"s8_{ts}", "ip": "127.0.0.1", "path": "/api/banking/transfer", "method": "POST"}, "sequential_behavior", 0.50, "Unannounced Jump to Transfer"))

    # 7-Layer Defense Check
    print("▶ Testing 7-Layer Defense Evaluation...", end=" ")
    l_res = client.get("/api/v1/layers")
    l_data = l_res.get_json() or {}
    layers = l_data.get("layers", [])
    if len(layers) == 7:
        print(f"✅ PASS (All 7 Defense Layers Active)")
        results.append(True)
    else:
        print(f"❌ FAIL ({len(layers)}/7 Layers Active)")
        results.append(False)

    passed = sum(1 for r in results if r)
    total = len(results)
    print("\n" + "═" * 70)
    print(f"  VERIFICATION RESULT: {passed}/{total} Checks Passed")
    print("═" * 70 + "\n")
    return passed == total

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
