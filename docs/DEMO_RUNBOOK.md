# TokenShield — Multi-Software GUI Security Demonstration Runbook
### Real Attack Software · Zero Terminal Commands · Real-Time AI Defense

> **Core Philosophy:** All attacks are executed via dedicated software applications and Graphical User Interfaces (Locust Web UI, Postman Runner, Apache JMeter, OWASP ZAP, and Red Team Attacker Studio). No commands are typed in the terminal during the demonstration. Everything is captured, scored by the 8 signals, mitigated by the 7 defense layers, and visualized live on the Vesper-Class Cyber Command Center.

---

## 🖥️ Screen Setup for Demonstration

Arrange your browser windows or dual-display:
- **Display 1 (Defense View):** `http://localhost:7777` — TokenShield Cyber Command Center (War Room)
- **Display 2 (Attack Software):** Open your choice of attack GUI:
  - **Option A (All-in-One GUI):** Attacker Studio at `http://localhost:7777/attacker-studio`
  - **Option B (DDoS & Load GUI):** Locust Dashboard at `http://localhost:8089`
  - **Option C (API & Session GUI):** Postman Desktop App with Runner
  - **Option D (Penetration Testing GUI):** OWASP ZAP Scanner
  - **Option E (Enterprise Stress GUI):** Apache JMeter GUI

---

## 🚀 Pre-Flight Services (Running in Background)

Both servers run continuously in the background:
1. **TokenShield AI Security Engine:** `http://127.0.0.1:7777` (Healthy, ML Inferencers Loaded)
2. **NeoVault Digital Banking Platform:** `http://127.0.0.1:5001` (Active, DB Initialized)

To start the Locust Web GUI server (one-time launcher):
```bash
./venv/bin/locust -f simulation/locustfile_demo.py --host http://localhost:5001
```
*(Once started, all interaction is done strictly in the browser at `http://localhost:8089`)*

---

## 🛡️ Software Attack 1: Red Team Attacker Studio (Browser GUI)
**URL:** `http://localhost:7777/attacker-studio`  
**What it demonstrates:** Signals 1, 2, 3, 4, 5, 6 and all 7 Defense Layers with live packet inspector.

### Tab 1: Stolen Token Replay (Signals 1 & 3 — Session Hijacking)
1. In the Attacker Studio, open the **Token Replayer** tab.
2. Click **"Auto-Fetch Active Browser Token"** (or paste any token from NeoVault).
3. The Origin IP defaults to a known Tor Exit Node (`185.220.101.5`) and spoofed User-Agent (`Mozilla/5.0 Unauthorized Client`).
4. Click the red button: **`▶ TRANSMIT STOLEN SESSION`**.
5. **Watch the Result:**
   - **Attacker Studio Packet Log:** Shows `HTTP 403: BLOCKED BY TOKENSHIELD (Threat Detected)`.
   - **Command Center Dashboard:** Signal 1 spikes to `0.85`, Signal 3 spikes to `0.90`.
   - **Threat Map:** Red arc traces from Frankfurt/Tor to Mumbai Core.
   - **Layer 6 (Session Integrity):** Flips to `CRITICAL` and auto-revokes session token.

### Tab 2: Automated Volumetric Flood (Signal 2 — Request Velocity)
1. Switch to the **DDoS Swarm** tab.
2. Select target: `/api/banking/transfer` or `/api/banking/accounts`.
3. Click **`▶ LAUNCH VOLUMETRIC FLOOD`**.
4. The button turns red and shows `⏹ STOP VOLUMETRIC FLOOD`. The monitor shows packets flooding at 40 req/s.
5. **Watch the Result:**
   - **Command Center Dashboard:** Signal 2 (Velocity Tracker) climbs from `0.20 → 0.50 → 0.85 → 0.95`.
   - **Layer 4 (Network & Velocity Defense):** Flags volumetric anomaly.
   - Click **`⏹ STOP VOLUMETRIC FLOOD`** when done.

### Tab 3: SQL Injection Fuzzer (Signal 4 — Payload Analysis)
1. Switch to the **SQL Injection** tab.
2. Select from the Exploit Presets:
   - `' UNION SELECT username, password FROM users--` (Credential Extraction)
   - `' OR '1'='1' --` (Authentication Bypass)
   - `1001'; DROP TABLE transactions; --` (Destructive DDL)
3. Click **`💉 DISPATCH INJECTION EXPLOIT`**.
4. **Watch the Result:**
   - **Attacker Studio:** Shows `SQLi BLOCKED (CVE-2026-1842 Pattern Caught)`.
   - **Command Center:** Signal 4 hits `0.90`. Layer 5 (Application & API Firewall) triggers mitigation.

### Tab 4: Headless Bot Takeover (Signal 5 — Behavioral Biometrics)
1. Switch to the **Bot Biometrics** tab.
2. The bot is configured with machine-speed telemetry: `285 WPM typing`, `0.0 px/s mouse velocity`.
3. Target account: `alice@neovault.com`.
4. Click **`🤖 LAUNCH BOT AUTOMATION ATTACK`**.
5. **Watch the Result:**
   - **Attacker Studio:** Shows `Decision: BLOCK | S5 Biometrics: 1.00`.
   - **Command Center:** Signal 5 flags severe deviation from Alice's 54 WPM human baseline.

### Tab 5: Supersonic Geographic Transit (Signal 6 — Impossible Travel)
1. Switch to the **Impossible Travel** tab.
2. Displays Leg 1 (Mumbai `103.21.58.1`) and Leg 2 (Amsterdam `185.107.80.12` in under 500ms).
3. Click **`🗺️ DISPATCH SUPERSONIC SESSION JUMP`**.
4. **Watch the Result:**
   - **Attacker Studio:** Shows `Verdict: BLOCK | S6 Geo Score: 0.95 (Mach 39,000 Travel)`.
   - **Command Center:** Haversine impossible travel alert displays on threat feed.

---

## 🦗 Software Attack 2: Locust Web Dashboard (GUI Bot Swarm)
**URL:** `http://localhost:8089`  
**Tool:** Locust Graphical Load Testing Platform  
**File:** `simulation/locustfile_demo.py`

### How to Execute:
1. Open your browser to `http://localhost:8089`.
2. In the Locust GUI form:
   - **Number of users:** Enter `50`
   - **Ramp-up rate:** Enter `10`
   - **Host:** Keep `http://localhost:5001`
3. Click the green button: **`Start swarming`**.
4. **Observe in Locust GUI:**
   - Live RPS graph climbing to 50–100 requests/sec.
   - Response time charts, failure ratios, and endpoint breakdown tables update dynamically.
5. **Observe in TokenShield War Room (`http://localhost:7777`):**
   - Live requests per second counter surges.
   - Signal 2 (Velocity Tracker) alerts trigger across multiple concurrent IPs.
   - Edge rate limiters engage and return `403 Blocked` for excessive bursts.
6. Click **`Stop`** in the Locust UI to end the swarm.

---

## 📬 Software Attack 3: Postman Collection Runner (GUI API Testing)
**Tool:** Postman Desktop App  
**Collection File:** `postman/TokenShield_Attacks_Postman_Collection.json`

### How to Execute:
1. Open Postman.
2. Click **Import** (top left) and select `/Users/yashpachhade/tokenshield/postman/TokenShield_Attacks_Postman_Collection.json`.
3. You will see the **TokenShield Attack Suite** containing:
   - `01 - Legitimate Customer Login`
   - `02 - Stolen Token Replay (Tor IP)`
   - `03 - SQL Injection (Search Endpoint)`
   - `04 - High-Velocity Burst (DDoS)`
   - `05 - Workflow Bypass (Direct Transfer Jump)`
4. Right-click the collection → Click **Run collection**.
5. Select **Iterations: 20**, **Delay: 100ms**.
6. Click the blue button: **`Run TokenShield Attack Suite`**.
7. **Observe in Postman Runner:**
   - Real-time response status table showing 200 OK for legitimate login and 403 Forbidden for all attacks.
8. **Observe in TokenShield War Room:**
   - Simultaneous hits on Signals 1, 3, 4, 7, and 8.

---

## ⚡ Software Attack 4: Apache JMeter GUI
**Tool:** Apache JMeter Desktop Application  
**Test Plan File:** `jmeter/neovault_load_test.jmx`

### How to Execute:
1. Open JMeter application.
2. Click **File → Open** and select:
   `/Users/yashpachhade/tokenshield/jmeter/neovault_load_test.jmx`
3. In the tree view on the left, you will see 5 configured Thread Groups:
   - `🏦 TG1 — Legitimate Banking Traffic (Baseline)`
   - `💥 TG2 — DDoS Volumetric Flood (Signal 2)`
   - `💉 TG3 — SQL Injection Fuzzer (Signal 4)`
   - `🎭 TG4 — Token Replay / Session Hijack (Signals 1 & 3)`
   - `🔀 TG5 — Workflow Bypass Attack (Signal 8)`
4. Click on **View Results Tree** or **Summary Report** in the left sidebar.
5. Click the green **Play (▶)** button on the top toolbar.
6. **Observe in JMeter GUI:**
   - Real-time HTTP request sampling with color-coded responses (Green = legitimate, Red = intercepted by TokenShield).
7. **Observe in TokenShield War Room:**
   - Complete multi-signal activation showing 8/8 signals engaged.

---

## 🕷️ Software Attack 5: OWASP ZAP (Automated Pen-Testing GUI)
**Tool:** OWASP ZAP (Zed Attack Proxy)  
**Target:** `http://localhost:5001`  
**Configuration:** `zap/automation.yaml`

### How to Execute:
1. Launch OWASP ZAP.
2. In the "Automated Scan" box, enter `http://localhost:5001`.
3. Click **Attack**.
4. **Observe in ZAP GUI:**
   - ZAP Spider crawls all banking endpoints.
   - Active Scanner launches automated fuzzers including SQLi, XSS, and directory traversal against `/api/banking/search`.
5. **Observe in TokenShield War Room:**
   - Signal 4 (Payload Analysis) and Signal 7 (Endpoint Risk) catch fuzzing attempts.
   - Attackers are blocked at Layer 5 (API Firewall) without touching the database.

---

## 📊 Summary of Signals & GUI Tools

| Signal | Threat Type | Primary GUI Tool | Detection Mechanism |
|---|---|---|---|
| **Signal 1** | Tor / Hostile ASN | Attacker Studio (Tab 1) / Postman | CIDR Range Matching (185.220.0.0/22) |
| **Signal 2** | Request Velocity / DDoS | Locust Web UI (:8089) / Attacker Studio (Tab 2) | Sliding 60s & 5s Burst Window Tracker |
| **Signal 3** | Session Hijack / Drift | Attacker Studio (Tab 1) / Postman | IP + User-Agent + Fingerprint Deviation |
| **Signal 4** | SQL Injection & XSS | Attacker Studio (Tab 3) / OWASP ZAP | AST & Regex Regex Payload Inspection |
| **Signal 5** | Bot Biometrics | Attacker Studio (Tab 4) | Welford Statistical Variance vs Human Baseline |
| **Signal 6** | Impossible Travel | Attacker Studio (Tab 5) | Haversine Supersonic Velocity Formula |
| **Signal 7** | Sensitive Endpoint Risk | JMeter (TG5) / Attacker Studio | High-Risk Transactional Route Classification |
| **Signal 8** | Sequential Bypass | JMeter (TG5) / Locust WorkflowBypass | Markov Chain & LSTM Sequence Autoencoder |
