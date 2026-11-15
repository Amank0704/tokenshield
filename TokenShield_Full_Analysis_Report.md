# TokenShield / NeoVault — Comprehensive Codebase & Architecture Analysis Report

> **Project Name:** TokenShield — AI-Powered Session Security & NeoVault Banking System  
> **Repository Path:** `/Users/yashpachhade/tokenshield`  
> **Report Version:** 3.5  
> **Date:** July 30, 2026  

---

## 1. Executive Summary

**TokenShield** is an enterprise-grade, AI-driven session security and threat mitigation engine designed to protect modern web applications and digital banking platforms (represented by **NeoVault / Alpha Bank**). Unlike traditional Web Application Firewalls (WAFs) or static IP rate limiters, TokenShield evaluates request risk continuously in real time using a **7-Signal Real-Time Threat Analysis Pipeline**.

When a high-risk or malicious request is detected (anomaly score $\ge 0.85$), TokenShield triggers an automated, multi-tiered **8-Step Progressive Mitigation Pipeline** that isolates the session in sub-millisecond speeds, updates Redis blocklists, reloads Nginx edge rules atomically, bans device fingerprints, locks user accounts behind mandatory TOTP 2FA, and notifies security administrators via Server-Sent Events (SSE) and email alerts.

---

## 2. Infrastructure & System Topology

The system is fully containerized using Docker Compose, creating a isolated subnetwork (`172.20.0.0/24`) with strict role separation.

```
+-----------------------------------------------------------------------------------+
|                                 Client Traffic                                    |
+-----------------------------------------------------------------------------------+
                                          | (Port 80)
                                          v
+-----------------------------------------------------------------------------------+
|                         Nginx Proxy / WAF (172.20.0.3:80)                          |
+-----------------------------------------------------------------------------------+
                                          | (Reverse Proxy)
                                          v
+-----------------------------------------------------------------------------------+
|                     TokenShield Flask Server (172.20.0.2:5001)                    |
+-----------------------------------------------------------------------------------+
                    |                                           |
         (O(1) Redis Check)                            (DB Read/Write)
                    v                                           v
+-----------------------+                       +-----------------------+
|  Redis Cache / State  |                       |    SQLite Database    |
| (172.20.0.4:6379)     |                       |    (tokenshield.db)   |
+-----------------------+                       +-----------------------+
```

### Container Services (`docker-compose.yml`)

1. **`nginx-proxy` (`172.20.0.3:80`)**:
   - Acts as the primary network edge proxy.
   - Dynamically loads `blocked_ips.conf` to drop malicious traffic before it reaches Flask.
2. **`flask-server` (`172.20.0.2:5001`)**:
   - Houses the core Flask application, REST APIs, security engine, and banking backend.
3. **`redis-cache` (`172.20.0.4:6379`)**:
   - In-memory data store for $O(1)$ token blocklists (`ts:block:*`), IP velocity tracking (`ts:vel:*`), device fingerprint bans (`ts:fp:*`), and geo-session records (`ts:geo:*`).
4. **Traffic Simulation & Attack Containers**:
   - `user1` (Alice), `user2` (Bob), `user3` (Carol): Generate normal background user activity via `simulation/traffic_simulator.py`.
   - `attacker` (`172.20.0.99`): Simulates offensive attack vectors (Moscow, Beijing, Lagos, Bucharest hacker profiles) via `simulation/attacker.py`.
   - `jmeter-load` (`172.20.0.20:8080`): Executes load testing benchmarks via Apache JMeter.
   - `zap-attacker` (`172.20.0.98:8090`): Automated vulnerability scanning with OWASP ZAP.

---

## 3. Core TokenShield Security Engine Architecture

### The 7-Signal Threat Analysis Pipeline (`app/middleware/detection.py`)

For every incoming HTTP request passing through Flask's `@app.before_request` hook, TokenShield aggregates seven distinct behavioral and contextual signals to compute an overall **Anomaly Score** ($S \in [0.0, 1.0]$):

$$S = \min\left( \sum_{i=1}^{7} s_i, \, 1.0 \right)$$

| Signal | Name | Weight Cap | Source Module | Logic & Mechanics |
| :--- | :--- | :---: | :--- | :--- |
| **Signal 1** | IP Reputation | `0.25` | `app/middleware/ip_reputation.py` | Scores IP against Tor exit node lists, hostile botnet CIDRs, datacenter hosting ranges (AWS/DO/Hetzner), and optional live IPinfo.io API lookups. |
| **Signal 2** | Request Velocity | `0.30` | `app/middleware/velocity.py` | Redis `INCR` sliding window over 60s. Scores: $\ge200$ req $\rightarrow 0.30$, $\ge100 \rightarrow 0.20$, $\ge50 \rightarrow 0.10$, $\ge20 \rightarrow 0.05$. |
| **Signal 3** | Session Consistency | `0.30` | `app/middleware/detection.py` | Compares current IP address and User-Agent header against the session creation metadata. IP change adds `0.20`, UA change adds `0.10`. |
| **Signal 4** | Payload Analysis | `0.40` | `app/middleware/detection.py` | Regex inspection of URL, query params, and JSON body for SQL Injection (`UNION SELECT`, `DROP TABLE`) and XSS (`<script>`, `onerror=`). |
| **Signal 5** | Behavioral Biometrics | `0.25` | `app/middleware/detection.py` | Analyzes mouse movement velocity, typing cadences, and scroll dynamics captured by client-side telemetry. |
| **Signal 6** | Geographic Impossibility | `0.35` | `app/middleware/geo.py` | Computes Haversine great-circle distance between current and previous IP locations. Flags travel exceeding commercial aviation speed ($900\text{ km/h}$). |
| **Signal 7** | Endpoint Pattern Risk | `0.20` | `app/middleware/detection.py` | Adds risk weight for sensitive endpoints (`/api/auth/login`, `/api/banking/transfer`, `/api/admin`, `/api/security`). |

### Threat Level Classification

$$\text{Threat Level} = \begin{cases} 
\text{Critical} & \text{if } S \ge 0.85 \\
\text{High} & \text{if } 0.70 \le S < 0.85 \\
\text{Medium} & \text{if } 0.50 \le S < 0.70 \\
\text{Low} & \text{if } 0.30 \le S < 0.50 \\
\text{Safe} & \text{if } S < 0.30 
\end{cases}$$

---

## 4. Multi-Layer Automated Mitigation Pipeline

When an anomaly score reaches or exceeds the critical threshold ($S \ge 0.85$), TokenShield executes an asynchronous 8-step mitigation workflow managed by `app/middleware/mitigation_timeline.py`:

1. **Step 1: O(1) Redis Token Revocation** — Sets `ts:block:<token_hash>` in Redis to invalidate session immediately.
2. **Step 2: Redis IP Block** — Writes `blocked_ip:<ip>` key (TTL 24 hours).
3. **Step 3: Nginx Edge Block** — Writes `deny <ip>;` to `/app/nginx/blocked_ips.conf` and reloads Nginx within 5 seconds.
4. **Step 4: Device Fingerprint Ban** — Sets `ts:fp:<fingerprint_hash>` (TTL 72 hours) blocking the physical browser device across all sessions.
5. **Step 5: Account 2FA Lockout** — Sets `failed_login_attempts = 99` (Soft Lock) or `is_active = False` (Hard Lock).
6. **Step 6: Coordinated Attack Check** — Scans database for matching IP/fingerprint patterns across multiple accounts.
7. **Step 7: Automated SMTP Email Alerts** — Dispatches security notification emails to account owners.
8. **Step 8: Live Dashboard SSE Push** — Streams step latency metrics and event details to the admin command center UI via Server-Sent Events.

---

## 5. Database Schema & Data Models (`app/models.py`)

TokenShield utilizes SQLAlchemy ORM with SQLite (production-configurable to PostgreSQL).

### Core Entities & Relationships

- **`User`**: System account credentials, password hash, admin status, failed login attempt counter, TOTP secret/enabled flags, and Google OAuth metadata.
- **`Session`**: Active JWT session tokens (SHA-256 hashed), IP address, User-Agent, real-time anomaly score, suspicious flag, revocation reason, and timestamp.
- **`BehaviorLog`**: Granular per-request action logs containing endpoint, HTTP method, client IP, time gap, and raw JSON fingerprint metadata.
- **`IncidentLog`**: High-severity threat events, anomaly scores, remediation actions taken, IP/UA details, and resolution timestamps.
- **`BankAccount`**: NeoVault banking accounts (checking, savings), currency, balance, account status (active, frozen), and customer user ID.
- **`Transaction`**: Fund transfers and bill payments with reference numbers, status (completed, pending, blocked), and TokenShield block reasons.
- **`Card`**: Credit and debit card numbers (masked), networks (Visa/Mastercard), expiry dates, hashed CVVs, and card status.

### Performance Indexing
- `idx_session_user_active`: `(user_id, is_active)`
- `idx_behavior_session_time`: `(session_id, timestamp)`
- `idx_incident_severity_time`: `(severity, timestamp)`
- `idx_transaction_account_time`: `(from_account_id, timestamp)`

---

## 6. Comprehensive File-by-File Analysis

### Core Application & Server Files

| File Path | Lines | Size | Purpose & Primary Responsibilities |
| :--- | :---: | :---: | :--- |
| `run.py` | 42 | 1.26 KB | **Application Entry Point.** Initializes Flask app via `create_app()`, prints startup banner with localhost URL references, and launches threaded HTTP server on port 5001. |
| `config.py` | 90 | 2.91 KB | **Configuration Manager.** Parses `.env` variables and sets up `DevelopmentConfig`, `ProductionConfig`, and `TestingConfig` classes (JWT settings, Bcrypt rounds, anomaly thresholds). |
| `app/__init__.py` | 132 | 6.16 KB | **Flask App Factory.** Registers CORS headers, database extension (`db.init_app`), health endpoint (`/health`), detection middleware hook, and all 9 core blueprints. |
| `app/models.py` | 309 | 13.69 KB | **Database ORM Models.** Defines schema for `User`, `Session`, `BehaviorLog`, `IncidentLog`, `BankAccount`, `Transaction`, and `Card` models along with custom index definitions. |
| `app/extensions.py` | 7 | 58 B | **Extension Registry.** Instantiates `SQLAlchemy` object (`db = SQLAlchemy()`). |
| `app/utils.py` | 120 | 3.82 KB | **Utility Functions.** Provides JWT token generation (`generate_token`), token SHA-256 hashing (`hash_token`), client IP extraction (`get_client_ip`), and `@token_required` / `@admin_required` decorators. |
| `app/google_auth.py` | 210 | 7.28 KB | **Google OAuth Handler.** Implements Google Sign-In verification route (`/api/auth/google/verify`) and client ID configuration endpoints. |
| `app/email_service.py` | 310 | 11.91 KB | **Email Alert Service.** Configures Flask-Mail for dispatching security incident notifications, 2FA recovery codes, and threat alerts to users. |

### Detection Middleware Layer (`app/middleware/`)

| File Path | Lines | Size | Purpose & Primary Responsibilities |
| :--- | :---: | :---: | :--- |
| `detection.py` | 468 | 17.29 KB | **Master Detection Engine.** Houses `_run_detection()`, aggregates 7 threat signals, persists scores to DB without overwriting high attack simulator scores, and triggers background thread mitigation. |
| `velocity.py` | 224 | 7.41 KB | **Redis Velocity & Blocklist Tracker.** Tracks request rates per IP in a 60s sliding window using Redis `INCR`/`EXPIRE`. Manages instant token revocation blocklist (`ts:block:*`). |
| `geo.py` | 346 | 12.46 KB | **Geographic Impossibility Scorer.** Calculates Haversine distance and travel velocity between consecutive requests. Flags impossible travel speeds ($>900\text{ km/h}$). |
| `ip_reputation.py` | 370 | 12.44 KB | **IP Threat Intelligence.** Evaluates IP addresses against compiled offline CIDR tables for Tor exit nodes, hostile botnets, and cloud datacenters, with optional live IPinfo.io lookup fallback. |
| `fingerprint.py` | 199 | 6.79 KB | **Device Fingerprint Ban System.** Checks `X-Device-Fingerprint` headers against Redis ban keys (`ts:fp:*`), allowing device-level banning across multiple user accounts and IP changes. |
| `account_lock.py` | 259 | 8.29 KB | **2FA Account Lock Manager.** Applies Soft Locks (`failed_login_attempts=99`) or Hard Locks (`is_active=False`) to user accounts upon critical threat detection. |
| `nginx_block.py` | 239 | 7.60 KB | **Nginx Edge Block Synchronizer.** Atomically updates `/app/nginx/blocked_ips.conf` with `deny <ip>;` rules so Nginx reloads dynamically. |
| `mitigation_timeline.py` | 147 | 5.46 KB | **Mitigation Timeline Recorder.** Tracks status, target system, and latency of each step (1–8) and streams live events to dashboard UI queues via SSE. |
| `redis_client.py` | 95 | 2.85 KB | **Redis Connection Wrapper.** Provides thread-safe access to Redis with automatic fallback to in-memory structures if Redis is offline. |

### API Routes & Blueprints

| File Path | Lines | Size | Purpose & Primary Responsibilities |
| :--- | :---: | :---: | :--- |
| `app/routes/auth.py` | 461 | 19.08 KB | **Authentication Blueprint (`/api/auth`).** Implements `/login`, `/register`, `/logout`, `/login-2fa`, Google Authenticator TOTP setup (`/totp/setup`, `/totp/confirm`), and session management. |
| `app/banking_routes.py` | 944 | 31.96 KB | **NeoVault Banking Operations (`/api/banking`).** Controls account balances, money transfers (`/transfer`), bill payments (`/pay-bill`), debit/credit cards (`/cards`), and attack status check endpoint. |
| `app/security_routes.py` | 1646 | 63.14 KB | **Security Engine Blueprint (`/api/security`).** Exposes live threat feeds (`/live-feed`), threat maps (`/threat-map-data`), telemetry collection (`/threat-detect`), attacker profiles, and Nginx/Redis controls. |
| `app/routes/admin.py` | 520 | 20.50 KB | **Admin Command Center (`/api/admin`).** Admin stats, active session management, user account locking/unlocking, system logs, and security rule updates. |
| `app/routes/attack_simulator.py` | 807 | 33.63 KB | **Attack Scenario Triggers (`/api/attack`).** Triggers simulated attacks (Token Theft, Brute Force, SQLi, Phishing, Credential Stuffing, MITM, XSS, Privilege Escalation) for live demonstration. |
| `app/routes/simulation.py` | 280 | 11.11 KB | **Simulation State Monitor (`/api/simulation`).** Exposes live network resource usage, container status, and scenario telemetry for the simulation dashboard. |
| `app/main_routes.py` | 115 | 4.43 KB | **Frontend Template Router.** Serves static HTML pages for root index, login, dashboard, admin, and security engine views. |
| `app/dashboard_routes.py` | 145 | 5.05 KB | **Dashboard Data API (`/api/dashboard`).** Exposes metric summaries and trend telemetry tailored for dashboard visualizations. |

### Frontend UI & Telemetry Scripts (`frontend/`)

| File Path | Size | Purpose & Primary Responsibilities |
| :--- | :---: | :--- |
| `frontend/admin.html` | 73.49 KB | **Admin Command Center Dashboard.** Comprehensive security dashboard featuring live incident logs, active sessions, IP block controls, and system health status. |
| `frontend/simulation_dashboard.html` | 64.78 KB | **Live Attack & Mitigation Simulator UI.** Interactive dashboard with 8-step mitigation timeline visualization, hacker location maps, and scenario trigger buttons. |
| `frontend/neovault_dashboard_pro.html` | 46.71 KB | **NeoVault Premium Banking Portal.** Glassmorphism UI displaying account balances, card management, recent transactions, and real-time security warning banners. |
| `frontend/security_engine.html` | 26.25 KB | **Security Engine Diagnostics UI.** Visualizes the 7-signal pipeline scores, ML anomaly thresholds, and live threat feed telemetry. |
| `frontend/dashboard.html` | 24.95 KB | **Standard Banking Dashboard.** User banking overview page showing accounts, transaction histories, and quick transfer forms. |
| `frontend/security_dashboard_user.html` | 24.33 KB | **User Security Settings Portal.** Allows users to view active sessions, revoke suspicious logins, and configure Google Authenticator TOTP 2FA. |
| `frontend/login.html` | 23.35 KB | **Authentication Interface.** Unified login/registration screen supporting password auth, Google OAuth 2.0, and TOTP 2FA step-up prompts. |
| `frontend/neovault_index_pro.html` | 17.35 KB | **NeoVault Landing Page.** Modern marketing landing page showcasing bank features and TokenShield security guarantees. |
| `frontend/index.html` | 1.68 KB | **App Gateway Index.** Lightweight redirection page connecting users to banking or admin portals. |
| `frontend/js/banking-security-monitor.js` | 13.65 KB | **Client Security Monitor.** Polls `/api/banking/attack-status` every 3s to display red alert banners when the system detects an active attack. |
| `frontend/js/app.js` | 11.34 KB | **Core Frontend Application Logic.** Handles authentication tokens, API request headers, session validation, and UI state switches. |
| `frontend/js/fingerprint.js` | 10.44 KB | **Client-Side Telemetry Collector.** Gathers canvas/WebGL hashes, screen metrics, timezone offsets, and mouse movement cadences into `X-Device-Fingerprint` headers. |
| `frontend/css/styles.css` | 17.09 KB | **Global CSS Design System.** Styling definitions for dark mode glassmorphism, animated risk meters, badges, and responsive layouts. |

### Infrastructure & Reverse Proxy (`nginx/`)

| File Path | Size | Purpose & Primary Responsibilities |
| :--- | :---: | :--- |
| `nginx/nginx.conf` | 10.02 KB | **Nginx Configuration File.** Defines upstream Flask routing (`172.20.0.2:5001`), rate-limiting zones (`limit_req_zone`), static asset caching, and includes `include /etc/nginx/blocked_ips.conf;`. |
| `nginx/entrypoint.sh` | 2.91 KB | **Nginx Container Watcher Script.** Monitors `blocked_ips.conf` md5 checksums in a loop and triggers `nginx -s reload` within 5s of new IP additions. |
| `nginx/blocked_ips.conf` | 450 B | **Dynamic IP Blocklist File.** Contains auto-generated `deny <ip>;` statements written by `app/middleware/nginx_block.py`. |

### Database & ML Utility Scripts (`scripts/`)

| File Path | Lines | Size | Purpose & Primary Responsibilities |
| :--- | :---: | :---: | :--- |
| `scripts/train_ml_model.py` | 317 | 13.46 KB | **Isolation Forest Model Trainer.** Trains scikit-learn anomaly detection pipelines on DB logs or synthetic behavioral datasets. Outputs `ml/model.pkl`. |
| `setup_database.py` | 250 | 8.95 KB | **Database Initialization Script.** Seeds database tables with initial demo users (`demo`, `alice`, `bob`, `carol`, `admin`), bank accounts, credit cards, and sample transactions. |
| `scripts/init_db.py` | 110 | 3.74 KB | **Lightweight DB Seeder.** Quick table creation helper for clean environments. |
| `scripts/migrate_google_oauth.py` | 105 | 3.90 KB | **Schema Migration Script.** Adds `google_id`, `avatar_url`, and `auth_provider` columns to existing `users` tables. |
| `scripts/migrate_add_metadata.py` | 55 | 1.84 KB | **Schema Migration Script.** Adds `fingerprint_data` column to `behavior_logs` table. |

### Attack Simulation & Load Testing Suite

| File Path | Size | Purpose & Primary Responsibilities |
| :--- | :---: | :--- |
| `simulation/attacker.py` | 14.32 KB | **Automated Attacker Agent.** Simulates malicious requests cycling through hacker profiles (Moscow, Beijing, Lagos, Bucharest) to trigger TokenShield mitigations. |
| `simulation/traffic_simulator.py` | 14.91 KB | **Normal User Traffic Generator.** Simulates legitimate background activity (logins, balance checks, money transfers) for Alice, Bob, and Carol. |
| `simulation/selenium_browser.py` | 15.87 KB | **Browser Automation Test.** Uses Selenium WebDriver to execute full end-to-end browser journeys and verify UI security warnings. |
| `simulation/network_controller.py` | 13.44 KB | **Resource & Network Monitor.** Monitors CPU, RAM, network bandwidth, and Docker container state to track system performance during attacks. |
| `simulation/locustfile.py` | 12.11 KB | **Locust Load Test Script.** Defines user load test scenarios for high-concurrency API performance benchmarks. |
| `jmeter/neovault_load_test.jmx` | N/A | **Apache JMeter Test Plan.** XML test definition executing multi-threaded stress tests on banking endpoints. |
| `jmeter/entrypoint.sh` | 3.54 KB | **JMeter Execution Script.** Runs JMeter in non-GUI mode inside `jmeter-load` container and generates HTML performance reports. |
| `zap/automation.yaml` | 4.06 KB | **OWASP ZAP Scan Automation.** YAML configuration file defining ZAP spidering and active vulnerability scan policies. |
| `zap/entrypoint.sh` | 6.22 KB | **OWASP ZAP Execution Script.** Drives ZAP vulnerability scans and outputs security audit reports to `/zap/reports`. |

---

## 7. Key Findings & Technical Summary

1. **Production-Ready Multi-Layer Security**: The combination of real-time 7-signal scoring and an 8-step progressive mitigation workflow ensures sub-second isolation of compromised sessions without impacting legitimate users.
2. **Resilient Hybrid Architecture**: TokenShield combines fast in-memory Redis caching ($O(1)$ blocklist lookups) with persistent SQLite database storage, featuring fail-open in-process fallbacks if Redis is temporarily unreachable.
3. **End-to-End Simulation & Verification Capabilities**: Integrated tools—including OWASP ZAP, Apache JMeter, Locust, and automated python attacker bots—provide empirical runtime verification of security policies under realistic threat scenarios.
