"""
TokenShield — Seed Legitimate Biometric Profile
===============================================
Establishes a normal, human baseline for 'alice@neovault.com'
so that Signal 5 (Behavioral Biometrics) has an established profile (>=20 samples)
against which to detect bot takeovers or typing anomalies.
"""

import sys
import random
import requests

ENGINE_URL = "http://127.0.0.1:7777"


def seed_baseline(user_id: str = "alice@neovault.com", count: int = 25):
    print(f"[*] Seeding {count} legitimate biometric samples for user '{user_id}'...")
    successes = 0

    for i in range(count):
        # Realistic human typing dynamics (WPM: 48-62, rhythm CV: 0.28-0.38, mouse speed: 350-500)
        sample = {
            "typing_wpm": round(random.gauss(54.0, 5.0), 2),
            "typing_rhythm_cv": round(random.gauss(0.33, 0.04), 4),
            "mouse_velocity_mean": round(random.gauss(420.0, 45.0), 2),
            "mouse_velocity_cv": round(random.gauss(0.42, 0.05), 4),
            "idle_time_ratio": round(random.gauss(0.22, 0.03), 4)
        }

        try:
            res = requests.post(f"{ENGINE_URL}/api/v1/biometric-update", json={
                "user_id": user_id,
                "metrics": sample
            }, timeout=2.0)

            if res.status_code == 200:
                successes += 1
                data = res.json()
                print(f"  Sample {i+1:02d}/{count}: WPM={sample['typing_wpm']} | Collected={data.get('samples_collected')} | Warmup={'COMPLETE' if data.get('warmup_complete') else 'Building'}")
            else:
                print(f"  Sample {i+1:02d} failed: HTTP {res.status_code}")
        except Exception as e:
            print(f"  Error contacting engine at {ENGINE_URL}: {e}")
            break

    print(f"\n[+] Finished. {successes}/{count} samples registered in UserProfileStore.")


if __name__ == "__main__":
    uid = sys.argv[1] if len(sys.argv) > 1 else "alice@neovault.com"
    seed_baseline(uid)
