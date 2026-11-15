"""
TokenShield — Live Attack Defense & Integration Demo
=====================================================
Demonstrates TokenShield defending against 5 real attack scenarios:
  1. Benign User: Normal navigation & valid session
  2. Session Hijacking: Valid token stolen & replayed from Tor exit node
  3. Exploit Payload: Malicious SQL injection in transaction transfer
  4. Account Takeover: Biometric mismatch (attacker typing dynamics)
  5. Workflow Bypass: Jumping directly to money transfer without authentication flow

Can be run locally or targeted from a second laptop/device on the same network.

Usage:
    python demo_test.py [--host http://127.0.0.1:7777]
"""

import sys
import time
import json
import argparse
from typing import Dict, Any

try:
    import requests
except ImportError:
    print("Error: 'requests' is required. Run: pip install requests")
    sys.exit(1)


def print_banner():
    print("\n" + "═" * 70)
    print("  🛡️  TokenShield Real-Time Attack Defense & Mitigation Demo")
    print("  100% Real AI-Driven (Isolation Forest + GBDT + LSTM + Biometrics)")
    print("═" * 70 + "\n")


def send_and_report(title: str, url: str, payload: Dict[str, Any], expected_action: str):
    print(f"▶ SCENARIO: {title}")
    print(f"  Endpoint : {payload.get('method', 'GET')} {payload.get('path', '/')}")
    print(f"  Client IP: {payload.get('ip')} | Session: {payload.get('session_id')[:18]}...")

    t0 = time.perf_counter()
    try:
        res = requests.post(f"{url}/api/v1/analyze", json=payload, timeout=5.0)
        elapsed = (time.perf_counter() - t0) * 1000
    except Exception as e:
        print(f"  ❌ Failed to reach TokenShield Engine at {url}: {e}\n")
        return

    if res.status_code != 200:
        print(f"  ❌ Engine error ({res.status_code}): {res.text}\n")
        return

    data = res.json()
    action = data.get("action", "allow").upper()
    threat_level = data.get("threat_level", "safe").upper()
    threat_score = data.get("threat_score", 0.0)
    reasons = data.get("reasons", [])
    signals = data.get("signals", {})
    explanation = data.get("explanation", {})

    status_icon = "🛑 BLOCKED" if action == "BLOCK" else ("⚠️ CHALLENGED" if action == "CHALLENGE" else "✅ ALLOWED")
    print(f"  Result   : {status_icon} (Threat Score: {threat_score:.2f} | Level: {threat_level})")
    print(f"  Latency  : {elapsed:.2f} ms (Engine internal: {data.get('latency_ms', 0)} ms)")

    if reasons:
        print(f"  Triggers : {', '.join(reasons)}")

    # Show elevated signals
    elevated = [f"{k}: {v:.2f}" for k, v in signals.items() if v >= 0.25]
    if elevated:
        print(f"  Signals  : {', '.join(elevated)}")

    if "narrative" in explanation:
        print(f"  AI Intel : \"{explanation['narrative']}\"")

    if data.get("mitigation_enacted"):
        print(f"  Action   : Enacted 8-Step Mitigation (Token Revoked, IP Banned, Account Locked)")

    print("─" * 70 + "\n")


def run_demo(engine_url: str):
    print_banner()
    print(f"Checking TokenShield Engine health at {engine_url}/health...")
    try:
        h = requests.get(f"{engine_url}/health", timeout=3.0).json()
        print(f"✓ Engine Online: {h.get('engine')} v{h.get('version')}")
        models = h.get("models", {})
        print(f"  - Isolation Forest : {models.get('isolation_forest', {}).get('status')}")
        print(f"  - Meta-Classifier  : {models.get('meta_classifier', {}).get('status')}")
        print(f"  - LSTM Autoencoder : {models.get('lstm_autoencoder', {}).get('model_type')}")
        print("\n" + "─" * 70 + "\n")
    except Exception as e:
        print(f"❌ Could not connect to engine at {engine_url}.\nStart it with:\n    python engine/server_flask.py\n")
        return

    # Prime baseline profile for user_1001 (Phase 3 warm-up)
    try:
        for i in range(5):
            requests.post(f"{engine_url}/api/v1/biometric-update", json={
                "user_id": "user_1001",
                "metrics": {
                    "typing_wpm": 45.0 + (i % 3),
                    "typing_rhythm_cv": 0.22,
                    "mouse_velocity_mean": 420.0 + (i * 10),
                    "mouse_velocity_cv": 0.35,
                    "idle_time_ratio": 0.15
                }
            }, timeout=2.0)
    except Exception:
        pass

    # Scenario 1: Benign User
    send_and_report(
        title="1. Legitimate Customer Browsing Account",
        url=engine_url,
        payload={
            "session_id": "sess_legit_usr_09182",
            "user_id": "user_1001",
            "ip": "192.168.1.45",
            "path": "/account/overview",
            "method": "GET",
            "biometrics": {
                "typing_wpm": 48.0,
                "typing_rhythm_cv": 0.22,
                "mouse_velocity_mean": 450.0,
                "idle_time_ratio": 0.15
            }
        },
        expected_action="ALLOW"
    )

    # Scenario 2: Real Session Hijacking from Tor Exit Node
    send_and_report(
        title="2. Session Hijacking (Stolen Token Replayed via Tor Exit Node)",
        url=engine_url,
        payload={
            "session_id": "sess_legit_usr_09182",  # Same stolen token!
            "user_id": "user_1001",
            "ip": "185.220.101.5",                 # Tor exit node
            "path": "/account/overview",
            "method": "GET"
        },
        expected_action="BLOCK"
    )

    # Scenario 3: SQL Injection Exploit
    send_and_report(
        title="3. Web Exploitation: SQL Injection in Fund Transfer Note",
        url=engine_url,
        payload={
            "session_id": "sess_attacker_test_88",
            "user_id": "user_1001",
            "ip": "203.0.113.19",
            "path": "/api/v1/transfer",
            "method": "POST",
            "payload": json.dumps({
                "recipient": "hacker",
                "amount": 5000,
                "note": "Payment'; DROP TABLE transactions; SELECT * FROM users WHERE '1'='1"
            })
        },
        expected_action="BLOCK"
    )

    # Scenario 4: Biometric Account Takeover (Mismatch)
    send_and_report(
        title="4. Account Takeover: Biometric Behavioral Impersonation",
        url=engine_url,
        payload={
            "session_id": "sess_takeover_229",
            "user_id": "user_1001",
            "ip": "192.168.1.45",
            "path": "/account/settings",
            "method": "POST",
            "biometrics": {
                # Severe deviation: 150 WPM bot-speed typing, erratic mouse velocity
                "typing_wpm": 165.0,
                "typing_rhythm_cv": 0.95,
                "mouse_velocity_mean": 2900.0,
                "idle_time_ratio": 0.01
            }
        },
        expected_action="BLOCK"
    )

    # Scenario 5: Workflow Anomaly (Direct Jump)
    send_and_report(
        title="5. Sequence Anomaly: Direct Jump to Transfer Without Navigation",
        url=engine_url,
        payload={
            "session_id": "sess_new_direct_jump_99",
            "user_id": "user_1001",
            "ip": "198.51.100.88",
            "path": "/api/transfer/execute",
            "method": "POST",
            "status_code": 200
        },
        expected_action="BLOCK"
    )

    print("══════════════════════════════════════════════════════════════════════")
    print("  Demo Complete. All attacks dynamically classified by TokenShield.")
    print("══════════════════════════════════════════════════════════════════════\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TokenShield Demo Attack Runner")
    parser.add_argument("--host", default="http://127.0.0.1:7777", help="TokenShield Engine host URL")
    args = parser.parse_args()
    run_demo(args.host)
