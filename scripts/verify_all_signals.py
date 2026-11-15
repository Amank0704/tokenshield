"""
TokenShield — Complete 8-Signal & Layer Automated Verification Suite
====================================================================
Tests every single signal individually, the 7 defense layers,
and the complete ML inference ensemble.
"""

import sys
import time
import requests

ENGINE_URL = "http://127.0.0.1:7777"


def verify_signal(name: str, payload: dict, signal_key: str, expected_min: float, desc: str):
    print(f"▶ Testing {name} ({desc})...", end=" ")
    try:
        res = requests.post(f"{ENGINE_URL}/api/v1/analyze", json=payload, timeout=4.0)
        if res.status_code not in (200, 403):
            print(f"❌ FAIL (HTTP {res.status_code})")
            return False

        data = res.json()
        val = data.get("signals", {}).get(signal_key, 0.0)
        if val >= expected_min:
            print(f"✅ PASS (Score: {val:.2f} >= {expected_min:.2f})")
            return True
        else:
            print(f"⚠️ LOW (Score: {val:.2f} < {expected_min:.2f})")
            return False
    except Exception as e:
        print(f"❌ ERROR ({e})")
        return False


def run_full_verification():
    print("\n" + "═" * 70)
    print("  🛡️  TokenShield 8-Signal & Layer Verification Suite")
    print("═" * 70 + "\n")

    # Health check
    try:
        h = requests.get(f"{ENGINE_URL}/health", timeout=2.0).json()
        print(f"[*] Engine Status: {h.get('status').upper()} (v{h.get('version')})")
        print(f"    Isolation Forest : {h.get('models', {}).get('isolation_forest', {}).get('status')}")
        print(f"    Meta-Classifier  : {h.get('models', {}).get('meta_classifier', {}).get('status')}")
        print(f"    LSTM Autoencoder : {h.get('models', {}).get('lstm_autoencoder', {}).get('status')}\n")
    except Exception as e:
        print(f"❌ Could not connect to TokenShield engine at {ENGINE_URL}: {e}")
        print("   Make sure './venv/bin/python engine/server_flask.py' is running.")
        sys.exit(1)

    results = []
    ts = int(time.time() * 1000)

    # 1. Signal 1: IP Reputation (Tor Node in 185.220.100.0/22)
    tor_ip = f"185.220.101.{(ts % 240) + 10}"
    s1 = verify_signal(
        "Signal 1: IP Reputation",
        {"session_id": f"sess_s1_{ts}", "ip": tor_ip, "path": "/"},
        "ip_reputation",
        0.80,
        "Tor Exit Node Range"
    )
    results.append(("Signal 1 (IP Reputation)", s1))

    # 2. Signal 2: Request Velocity
    v_ip = f"198.51.100.{(ts % 240) + 10}"
    sess_v = f"sess_v_{ts}"
    for _ in range(25):
        requests.post(f"{ENGINE_URL}/api/v1/analyze", json={"session_id": sess_v, "ip": v_ip, "path": "/"})
    s2 = verify_signal(
        "Signal 2: Request Velocity",
        {"session_id": sess_v, "ip": v_ip, "path": "/"},
        "request_velocity",
        0.30,
        "26 Requests in Burst"
    )
    results.append(("Signal 2 (Request Velocity)", s2))

    # 3. Signal 3: Session Consistency
    sess_id = f"sess_drift_{ts}"
    orig_ip = f"10.1.{(ts % 200) + 1}.1"
    drift_ip = f"10.1.{(ts % 200) + 1}.2"
    requests.post(f"{ENGINE_URL}/api/v1/register-session", json={"session_id": sess_id, "ip": orig_ip, "user_agent": "Chrome/120"})
    s3 = verify_signal(
        "Signal 3: Session Consistency",
        {"session_id": sess_id, "ip": drift_ip, "user_agent": "curl/7.88", "path": "/"},
        "session_consistency",
        0.85,
        "IP and User-Agent Drift"
    )
    results.append(("Signal 3 (Session Consistency)", s3))

    # 4. Signal 4: Payload Analysis
    s4 = verify_signal(
        "Signal 4: Payload Analysis",
        {"session_id": f"sess_s4_{ts}", "ip": "127.0.0.1", "path": "/api/banking/search", "payload": "1' UNION SELECT username,password FROM users--"},
        "payload_analysis",
        0.85,
        "SQL Injection Query"
    )
    results.append(("Signal 4 (Payload Analysis)", s4))

    # 5. Signal 5: Behavioral Biometrics
    s5 = verify_signal(
        "Signal 5: Behavioral Biometrics",
        {"session_id": f"sess_s5_{ts}", "user_id": "alice@neovault.com", "ip": "127.0.0.1", "path": "/", "biometrics": {
            "typing_wpm": 280.0, "typing_rhythm_cv": 0.001, "mouse_velocity_mean": 0.0, "mouse_velocity_cv": 0.0, "idle_time_ratio": 0.0
        }},
        "behavioral_biometrics",
        0.80,
        "Inhuman Bot Dynamics"
    )
    results.append(("Signal 5 (Behavioral Biometrics)", s5))

    # 6. Signal 6: Geographic Impossibility
    geo_sess = f"geo_sess_{ts}"
    requests.post(f"{ENGINE_URL}/api/v1/analyze", json={"session_id": geo_sess, "ip": "103.21.58.1", "path": "/"})
    time.sleep(0.5)
    dest_ip = f"185.107.80.{(ts % 240) + 10}"
    s6 = verify_signal(
        "Signal 6: Geographic Impossibility",
        {"session_id": geo_sess, "ip": dest_ip, "path": "/"},
        "geographic_impossibility",
        0.85,
        "Mumbai → Amsterdam in 0.5s"
    )
    results.append(("Signal 6 (Geographic Impossibility)", s6))

    # 7. Signal 7: Endpoint Risk
    s7 = verify_signal(
        "Signal 7: Endpoint Risk",
        {"session_id": f"sess_s7_{ts}", "ip": "127.0.0.1", "path": "/api/banking/transfer/execute"},
        "endpoint_risk",
        0.35,
        "High-Value Financial Transfer"
    )
    results.append(("Signal 7 (Endpoint Risk)", s7))

    # 8. Signal 8: Sequential Behavior
    s8 = verify_signal(
        "Signal 8: Sequential Behavior",
        {"session_id": f"s8_sess_{ts}", "ip": "127.0.0.1", "path": "/api/banking/transfer/execute", "method": "POST"},
        "sequential_behavior",
        0.75,
        "Direct Workflow Jump"
    )
    results.append(("Signal 8 (Sequential Behavior)", s8))

    # 7-Layer Defense Check
    print("\n[*] Checking 7-Layer Hierarchical Defense...")
    try:
        layers = requests.get(f"{ENGINE_URL}/api/v1/layers", timeout=2.0).json().get("layers", [])
        print(f"    Total Layers Registered: {len(layers)}/7")
        for l in layers:
            print(f"    - Layer {l['id']}: {l['name']} [{l['status']}]")
        layers_ok = len(layers) == 7
    except Exception as e:
        print(f"❌ Layer registry check failed: {e}")
        layers_ok = False

    # Summary
    print("\n" + "═" * 70)
    passed_count = sum(1 for _, ok in results if ok)
    print(f"  VERIFICATION RESULT: {passed_count}/{len(results)} Signals Passed (Layers: {'PASS' if layers_ok else 'FAIL'})")
    print("═" * 70 + "\n")


if __name__ == "__main__":
    run_full_verification()
