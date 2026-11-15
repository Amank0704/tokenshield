"""
TokenShield — Compound Multi-Vector Attack Simulator
=====================================================
Exercises all 8 signals, all 7 hierarchical defense layers,
and all 3 machine learning models simultaneously.
"""

import sys
import time
import requests

ENGINE_URL = "http://127.0.0.1:7777"


def run_compound_attack():
    print("\n" + "═" * 72)
    print("  🛡️  TokenShield Compound Multi-Vector Stress Test (All 8 Signals)")
    print("═" * 72)

    session_id = f"compound_session_{int(time.time())}"

    # Step 1: Pre-seed legitimate session in Mumbai to enable Haversine Geo displacement
    print("\n[Phase 1] Establishing initial session origin: Mumbai Banking Node (103.21.58.1)...")
    requests.post(f"{ENGINE_URL}/api/v1/analyze", json={
        "session_id": session_id,
        "user_id": "alice@neovault.com",
        "ip": "103.21.58.1",
        "path": "/api/banking/accounts",
        "method": "GET"
    }, timeout=2.0)

    ts = int(time.time())
    attacker_tor_ip = f"185.220.101.{(ts % 240) + 10}"

    # Step 2: Build velocity on the active session
    print(f"[Phase 2] Simulating high transaction velocity on session {session_id[:16]}...")
    for _ in range(25):
        requests.post(f"{ENGINE_URL}/api/v1/analyze", json={
            "session_id": session_id,
            "user_id": "alice@neovault.com",
            "ip": "103.21.58.1",
            "path": "/api/banking/accounts",
            "method": "GET"
        }, timeout=2.0)

    # Step 3: Launch Multi-Vector Attack Payload
    print("[Phase 3] Launching Compound Attack Request (Tor + SQLi + Bot Biometrics + Geo Jump)...")
    time.sleep(0.5)

    compound_payload = {
        "session_id": session_id,
        "user_id": "alice@neovault.com",
        "ip": attacker_tor_ip,  # S1: Tor Exit Node (Germany) & S6: Impossible travel from Mumbai
        "user_agent": "sqlmap/1.8.2#stable (Automated Scanner)",  # S3: UA drift
        "device_fingerprint": "SPOOFED_FP_ATTACKER_99",            # S3: Fingerprint drift
        "path": "/api/banking/transfer/execute",                  # S7: Sensitive endpoint & S8: Sequence jump
        "method": "POST",
        "payload": {                                              # S4: SQL Injection
            "to_account": "HACKER-101' UNION SELECT credit_card_num, cvv FROM cards--",
            "amount": 999999
        },
        "biometrics": {                                           # S5: Bot-speed biometrics
            "typing_wpm": 290.0,
            "typing_rhythm_cv": 0.0015,
            "mouse_velocity_mean": 0.0,
            "mouse_velocity_cv": 0.0,
            "idle_time_ratio": 0.0
        }
    }

    t0 = time.perf_counter()
    res = requests.post(f"{ENGINE_URL}/api/v1/analyze", json=compound_payload, timeout=5.0)
    latency = (time.perf_counter() - t0) * 1000

    if res.status_code != 200:
        print(f"❌ Error ({res.status_code}): {res.text}")
        return

    data = res.json()
    signals = data.get("signals", {})

    print("\n" + "─" * 72)
    print(f"  ENGINE DECISION       : {data['action'].upper()} (Level: {data['threat_level'].upper()})")
    print(f"  COMPOSITE THREAT SCORE: {data['threat_score']:.4f} / 1.0000")
    print(f"  INTERNAL ENGINE TIME  : {latency:.2f} ms")
    print(f"  MITIGATION PIPELINE   : {'ENACTED (8 Steps Executed)' if data.get('mitigation_enacted') else 'None'}")
    print("─" * 72)

    print("\n  [8-SIGNAL BREAKDOWN]")
    for k, v in signals.items():
        bar = "█" * int(v * 28) + "░" * (28 - int(v * 28))
        tag = "🔴 CRITICAL" if v >= 0.70 else ("🟡 ALERT" if v >= 0.35 else "🟢 CLEAR")
        print(f"    {k:<26} [{bar}] {v:.2f}  {tag}")

    print("\n  [MACHINE LEARNING ENSEMBLE]")
    print(f"    Isolation Forest Anomaly   : {'FLAGGED' if data.get('isolation_forest_anomaly') else 'NOMINAL'}")
    print(f"    Meta-Classifier Probability: {data.get('meta_classifier_probability', 0.0):.4f}")

    if data.get("explanation", {}).get("narrative"):
        print(f"\n  [DYNAMIC THREAT INTELLIGENCE]")
        print(f"    \"{data['explanation']['narrative']}\"")

    print("\n" + "═" * 72 + "\n")


if __name__ == "__main__":
    run_compound_attack()
