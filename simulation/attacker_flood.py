"""
TokenShield — Industrial DDoS & HTTP Volumetric Flood Simulation (Locust)
========================================================================
Generates high-concurrency Layer 7 HTTP flood against NeoVault endpoints
to trigger Signal 2 (Request Velocity & Burst Tracker) and Layer 4 Defense.

Usage:
  # Headless automated attack:
  locust -f simulation/attacker_flood.py --host http://localhost:7777 --headless -u 40 -r 8 -t 45s

  # With Locust Web UI:
  locust -f simulation/attacker_flood.py --host http://localhost:7777
  Open browser at: http://localhost:8089
"""

import random
from locust import HttpUser, task, between


class VolumetricAttacker(HttpUser):
    # Extremely aggressive delay between 10ms and 50ms per user to simulate automated flood
    wait_time = between(0.01, 0.05)

    def on_start(self):
        self.session_id = f"flood_bot_{random.randint(1000, 9999)}"
        self.attacker_ip = f"198.51.100.{random.randint(10, 250)}"

    @task(4)
    def flood_search(self):
        """Simulate high-frequency API search queries"""
        self.client.post("/api/v1/analyze", json={
            "session_id": self.session_id,
            "ip": self.attacker_ip,
            "path": "/api/banking/search",
            "method": "POST",
            "payload": {"query": f"tx_id_{random.randint(10000, 99999)}"}
        }, name="[FLOOD] /api/banking/search")

    @task(3)
    def flood_transfer_probe(self):
        """High-risk endpoint probes"""
        self.client.post("/api/v1/analyze", json={
            "session_id": self.session_id,
            "ip": self.attacker_ip,
            "path": "/api/banking/transfer/execute",
            "method": "POST",
            "payload": {"amount": random.randint(100, 5000), "to_account": "ACC-999"}
        }, name="[FLOOD] /api/banking/transfer/execute")

    @task(1)
    def probe_admin(self):
        """Reconnaissance scraping"""
        self.client.post("/api/v1/analyze", json={
            "session_id": self.session_id,
            "ip": self.attacker_ip,
            "path": "/api/admin/users",
            "method": "GET"
        }, name="[RECON] /api/admin/users")
