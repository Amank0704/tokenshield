"""
TokenShield — Bot Account Takeover Simulation
=============================================
Simulates an automated headless script or bot attempting an account takeover.
Sends telemetry with machine-speed typing (285 WPM), zero mouse movement,
and zero idle ratio against the target user's established baseline.

Usage:
  python simulation/bot_attacker.py [user_id]
"""

import sys
import time
import requests

ENGINE_URL = "http://127.0.0.1:7777"


def run_bot_attack(user_id: str = "alice@neovault.com"):
    print("\n" + "═" * 70)
    print("  🛡️  Signal 5 Demonstration: Automated Bot Biometrics Attack")
    print("═" * 70)

    print(f"\n[*] Target Account: {user_id}")
    print("[*] Simulating automated headless bot script attempting funds transfer...")

    bot_biometrics = {
        "typing_wpm": 285.0,         # Inhuman: 285 words per minute
        "typing_rhythm_cv": 0.0012,  # Machine-perfect cadence
        "mouse_velocity_mean": 0.0,  # Zero mouse movement (headless environment)
        "mouse_velocity_cv": 0.0,
        "idle_time_ratio": 0.0       # Zero pauses or reading latency
    }

    session_id = f"bot_hijack_{int(time.time())}"

    res = requests.post(f"{ENGINE_URL}/api/v1/analyze", json={
        "session_id": session_id,
        "user_id": user_id,
        "ip": "198.51.100.42",
        "path": "/api/banking/transfer/execute",
        "method": "POST",
        "biometrics": bot_biometrics,
        "payload": {"amount": 50000, "to_account": "BOT-PAYEE-01"}
    }, timeout=4.0)

    if res.status_code == 200:
        d = res.json()
        s5 = d["signals"]["behavioral_biometrics"]
        print(f"\n  Result       : {d['action'].upper()} (Threat Score: {d['threat_score']:.2f})")
        print(f"  Signal 5     : {s5:.2f} (Behavioral Biometrics Anomaly)")
        print(f"  Mitigation   : {'ENACTED (8 Steps Executed)' if d.get('mitigation_enacted') else 'None'}")
        print(f"  AI Narrative : \"{d.get('explanation', {}).get('narrative')}\"")
    else:
        print(f"  Failed: HTTP {res.status_code} {res.text}")

    print("\n[+] Bot Attack Simulation Complete.\n")


if __name__ == "__main__":
    uid = sys.argv[1] if len(sys.argv) > 1 else "alice@neovault.com"
    run_bot_attack(uid)
