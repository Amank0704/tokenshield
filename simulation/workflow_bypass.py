"""
TokenShield — Attack Demonstration: Sequential Workflow Bypass (Signal 8)
========================================================================
Demonstrates how an attacker skipping legitimate banking flow directly to
fund transfer is caught by Signal 8 (Sequential Request Behavior & LSTM).
"""

import sys
import time
import requests

ENGINE_URL = "http://127.0.0.1:7777"


def run_workflow_demo():
    print("\n" + "═" * 70)
    print("  🛡️  Signal 8 Demonstration: Sequential Workflow Integrity")
    print("═" * 70)

    # 1. Attacker jumps directly to execute money transfer without visiting home/accounts
    attacker_session = f"stolen_token_{int(time.time())}"
    print(f"\n[!] ATTACKER SCENARIO:")
    print(f"    Session: {attacker_session[:18]}...")
    print(f"    Target: Direct jump to POST /api/banking/transfer/execute")
    print(f"    Prior Navigation: ZERO requests")

    res = requests.post(f"{ENGINE_URL}/api/v1/analyze", json={
        "session_id": attacker_session,
        "user_id": "victim@neovault.com",
        "ip": "91.108.4.1",
        "path": "/api/banking/transfer/execute",
        "method": "POST",
        "status_code": 200,
        "payload": {"amount": 50000, "to_account": "ATTACKER-999"}
    }, timeout=3.0)

    if res.status_code == 200:
        d = res.json()
        s8 = d["signals"]["sequential_behavior"]
        print(f"\n    Result       : {d['action'].upper()} (Threat Score: {d['threat_score']:.2f})")
        print(f"    Signal 8     : {s8:.2f} (Direct Sensitive Jump Flagged)")
        print(f"    Mitigation   : {'ENACTED' if d.get('mitigation_enacted') else 'None'}")
        print(f"    AI Narrative : \"{d.get('explanation', {}).get('narrative')}\"")
    else:
        print(f"    Failed: {res.status_code} {res.text}")

    # 2. Legitimate Customer: Natural banking navigation sequence
    legit_session = f"legit_token_{int(time.time())}"
    print(f"\n" + "─" * 70)
    print(f"[*] LEGITIMATE USER SCENARIO (Sequential Natural Navigation):")

    sequence = [
        ("POST", "/api/auth/login"),
        ("GET",  "/api/dashboard"),
        ("GET",  "/api/banking/accounts"),
        ("GET",  "/api/banking/transactions"),
        ("GET",  "/api/banking/transfer"),
        ("POST", "/api/banking/transfer/execute")
    ]

    for method, path in sequence:
        r = requests.post(f"{ENGINE_URL}/api/v1/analyze", json={
            "session_id": legit_session,
            "user_id": "alice@neovault.com",
            "ip": "103.21.58.1",
            "path": path,
            "method": method,
            "status_code": 200
        }, timeout=2.0)
        d = r.json()
        s8 = d["signals"]["sequential_behavior"]
        print(f"    {method:5} {path:35} → S8: {s8:.2f} | Action: {d['action'].upper()} | Score: {d['threat_score']:.2f}")
        time.sleep(0.1)

    print("\n[+] Sequential Workflow Integrity Test Complete.\n")


if __name__ == "__main__":
    run_workflow_demo()
