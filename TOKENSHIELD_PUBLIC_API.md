# TokenShield Public API — Banking Integration Reference
**Version:** 2.0.0  
**Base URL:** `http://your-tokenshield-engine:7777`  
**Protocol:** REST/HTTP over JSON  
**Auth:** `X-API-Key: ts_live_<your_key>` header on all requests

---

## Overview

TokenShield is an AI-powered session security engine that any banking platform can integrate in under an hour. It inspects every payment/API request and returns a real-time threat score using 8 behavioral signals and a 3-model ML ensemble (Isolation Forest + LSTM Autoencoder + Meta-Classifier).

```
Your Banking Platform          TokenShield Engine
─────────────────────          ──────────────────
User logs in         ────────► POST /api/v1/register-session
                               (establishes geo/device baseline)

User makes payment   ────────► POST /api/v1/analyze
                     ◄──────── { action: "block", threat_score: 0.97 }
Reject payment       ◄────────
```

---

## Authentication

All endpoints require an API key in the request header:

```
X-API-Key: ts_live_abc123xyz789
```

> **Note:** In the current open-source self-hosted version, the API key is accepted but not enforced (engine trusts all local traffic). Managed cloud deployments enforce key validation per-tenant.

---

## Core Endpoints

### 1. `POST /api/v1/analyze` — Inspect a Request

**The primary integration method.** Call this on every sensitive banking action (login, transfer, account change, export).

#### Request Body

```json
{
  "session_id":        "string — unique session token or ID (required)",
  "user_id":           "string — user email or ID (optional but recommended)",
  "ip":                "string — real client IP address (required)",
  "path":              "string — endpoint path being accessed e.g. /api/payments/wire",
  "method":            "string — HTTP method: GET, POST, PUT, DELETE",
  "payload":           "object — request body/parameters (for payload analysis)",
  "biometrics":        "object — behavioral telemetry (optional, from JS collector)",
  "user_agent":        "string — client User-Agent header value",
  "device_fingerprint": "string — device fingerprint hash (from frontend collector)",
  "headers":           "object — additional headers to pass for context"
}
```

**Biometrics sub-object (from JS collector):**
```json
{
  "typing_wpm":          68.5,
  "typing_rhythm_cv":    0.18,
  "mouse_velocity_mean": 450.0,
  "mouse_velocity_cv":   0.32,
  "idle_time_ratio":     0.24,
  "keypress_dwell_ms":   87.5,
  "scroll_velocity":     320.0
}
```

#### Response Body

```json
{
  "threat_score":              0.94,
  "threat_level":              "critical",
  "action":                    "block",
  "is_threat":                 true,
  "signals": {
    "ip_reputation":            0.85,
    "request_velocity":         0.20,
    "session_consistency":      0.75,
    "payload_analysis":         0.95,
    "behavioral_biometrics":    0.91,
    "geographic_impossibility": 1.00,
    "endpoint_risk":            0.60,
    "sequential_behavior":      0.30
  },
  "reasons": [
    "tor_exit_node",
    "session_ip_mismatch",
    "sql_injection_detected"
  ],
  "isolation_forest_anomaly":  true,
  "meta_classifier_probability": 0.9722,
  "mitigation_enacted":        true,
  "latency_ms":                3.8,
  "explanation": {
    "narrative": "Request originated from a known Tor exit node (185.220.101.5) with a session token belonging to a Mumbai-registered user. SQL injection payload detected in query field. Bot-level biometric pattern detected (285 WPM, zero mouse motion). All signals exceed threshold — attack blocked and mitigated."
  }
}
```

#### Action Values

| `action`    | Meaning                                           | Recommended Integration Response              |
|-------------|---------------------------------------------------|-----------------------------------------------|
| `"allow"`   | Request is legitimate — safe to proceed           | Process payment normally                      |
| `"challenge"` | Suspicious but not definitive — step-up required | Trigger OTP/2FA/CAPTCHA before proceeding     |
| `"block"`   | Attack confirmed — reject immediately             | Reject request, log incident, notify user     |

#### Threat Levels

| `threat_level` | Score Range | Description                           |
|----------------|-------------|---------------------------------------|
| `"safe"`       | 0.00–0.29   | Normal traffic                        |
| `"low"`        | 0.30–0.49   | Minor anomaly, no action needed       |
| `"medium"`     | 0.50–0.69   | Suspicious — monitor closely          |
| `"high"`       | 0.70–0.84   | Attack likely — challenge mode        |
| `"critical"`   | 0.85–1.00   | Attack confirmed — block immediately  |

#### The 8 Signals

| Signal                     | What It Detects                                           |
|----------------------------|-----------------------------------------------------------|
| `ip_reputation`            | Tor exit nodes, hostile ASNs, known botnet IPs           |
| `request_velocity`         | Rate abuse — requests/minute sliding window              |
| `session_consistency`      | Device, UA, or IP changed mid-session (takeover)         |
| `payload_analysis`         | SQL injection, XSS, command injection in request body    |
| `behavioral_biometrics`    | Bot typing (>180 WPM), zero mouse motion, robotic rhythm |
| `geographic_impossibility` | Haversine travel speed exceeds physical possibility      |
| `endpoint_risk`            | High-value endpoint targeting (bulk export, admin)       |
| `sequential_behavior`      | Credential stuffing, account enumeration patterns        |

---

### 2. `POST /api/v1/register-session` — Register Session on Login

Call this **immediately after the user successfully authenticates** to establish their legitimate baseline.

#### Request Body

```json
{
  "session_id":        "string — session token or UUID (required)",
  "user_id":           "string — user identifier (required)",
  "ip":                "string — client IP at login time (required)",
  "user_agent":        "string — browser User-Agent at login",
  "device_fingerprint": "string — device fingerprint hash"
}
```

#### Response

```json
{
  "success": true,
  "session_id": "sess_abc123",
  "registered_at": 1720000000.0
}
```

---

### 3. `POST /api/v1/revoke-session` — Revoke Compromised Session

Immediately blacklists a session — all future `analyze` calls with this session_id will return `action: "block"` with `threat_score: 1.0`.

#### Request Body

```json
{
  "session_id": "string — session to revoke (required)"
}
```

#### Response

```json
{
  "success": true,
  "session_id": "sess_abc123",
  "status": "revoked"
}
```

---

### 4. `GET /api/v1/session/{session_id}/score` — Get Session Threat Score

Returns current threat level and signals for any registered session. Useful for risk dashboards.

#### Response

```json
{
  "session_id":    "sess_abc123",
  "user_id":       "user@bank.com",
  "ip":            "203.0.113.100",
  "threat_score":  0.12,
  "threat_level":  "safe",
  "last_seen":     1720000100.0
}
```

---

### 5. `POST /api/v1/biometric-update` — Update Biometric Baseline

Send background behavioral telemetry during normal usage to improve accuracy of the user's baseline model.

#### Request Body

```json
{
  "user_id": "string — user identifier",
  "metrics": {
    "typing_wpm":          68.5,
    "typing_rhythm_cv":    0.18,
    "mouse_velocity_mean": 450.0,
    "mouse_velocity_cv":   0.32,
    "idle_time_ratio":     0.24
  }
}
```

---

### 6. `GET /api/v1/incidents` — List Security Incidents

Returns recent security incidents for audit and SIEM integration.

**Query Parameters:**
- `limit` — max results (default 50)

#### Response

```json
{
  "total_incidents": 14,
  "returned": 5,
  "incidents": [
    {
      "incident_id": "inc_1720000123456",
      "timestamp": 1720000123.456,
      "iso_time": "2024-07-03T12:15:23Z",
      "threat_score": 0.97,
      "threat_level": "critical",
      "ip": "185.220.101.5",
      "session_id": "stolen_session_abc",
      "user_id": "victim@bank.com",
      "path": "/api/banking/transfer",
      "signals": { "ip_reputation": 0.85, "geographic_impossibility": 1.0 },
      "reasons": ["tor_exit_node", "geo_impossible_travel"]
    }
  ]
}
```

---

### 7. `GET /api/v1/incidents/latest/report` — Full Forensic Report

Structured forensic audit report for the most recent incident. Includes attack timeline, threat actor profile, geo data, executive summary.

---

### 8. `GET /api/v1/stats` — Engine Operational Stats

Returns real-time operational metrics.

#### Response

```json
{
  "total_inspections":      4821,
  "allowed_count":          4788,
  "blocked_count":          24,
  "challenged_count":       9,
  "active_sessions_tracked": 12,
  "total_incidents_recorded": 24,
  "performance": {
    "avg_latency_ms": 3.8,
    "p95_latency_ms": 8.2
  }
}
```

---

### 9. `GET /api/v1/layers` — Defense Layer Status

Returns live health of all 7 defense layers.

---

### 10. `GET /api/v1/model-info` — ML Model Information

Returns model versions, accuracy benchmarks, and feature dimensions.

#### Response

```json
{
  "engine": "TokenShield Standalone AI Engine",
  "version": "2.0.0",
  "feature_dimension": 40,
  "benchmarks": {
    "dataset_rows": 958534,
    "roc_auc": 0.8943,
    "precision_pct": 98.18,
    "false_positive_rate_pct": 1.05
  }
}
```

---

### 11. `GET /health` — Health Check

Lightweight uptime check. Returns < 10ms.

```json
{
  "status": "online",
  "engine": "TokenShield Standalone AI Security Engine",
  "port": 7777,
  "version": "2.0.0",
  "models": {
    "isolation_forest":     { "loaded": true, "ready": true },
    "meta_classifier":      { "loaded": true, "ready": true },
    "lstm_autoencoder":     { "loaded": true, "ready": true }
  }
}
```

---

## Admin Endpoints

### `POST /api/v1/admin/whitelist-ip`
```json
{ "ip": "203.0.113.100" }
```

### `POST /api/v1/admin/unlock/{user_id}`
Unlocks a user account locked by automated mitigation.

---

## Integration Code Examples

### Python (using SDK)

```python
from sdk.python.tokenshield_sdk import TokenShieldClient

ts = TokenShieldClient(engine_url="http://your-engine:7777")

# On every payment request:
result = ts.inspect_request(
    session_id=request.session_id,
    user_id=current_user.email,
    ip=request.client_ip,
    path=request.path,
    method=request.method,
    payload=request.json,
    biometrics=request.headers.get("X-Biometrics"),
    user_agent=request.user_agent
)

if result["action"] == "block":
    return {"error": "Transaction blocked by security engine"}, 403
elif result["action"] == "challenge":
    trigger_step_up_auth()
else:
    process_payment()
```

### JavaScript / Node.js

```javascript
const axios = require('axios');

async function inspectRequest(sessionId, userId, ip, path, payload) {
  const res = await axios.post('http://your-engine:7777/api/v1/analyze', {
    session_id: sessionId,
    user_id: userId,
    ip: ip,
    path: path,
    method: 'POST',
    payload: payload
  }, {
    headers: { 'X-API-Key': 'ts_live_your_key', 'Content-Type': 'application/json' },
    timeout: 5000
  });

  const { action, threat_score, reasons } = res.data;
  
  if (action === 'block') {
    throw new Error(`Transaction blocked: ${reasons.join(', ')}`);
  }
  return res.data;
}
```

### Flask Middleware (Auto-wrap all routes)

```python
from sdk.python.tokenshield_sdk import TokenShieldClient

ts = TokenShieldClient()

@app.before_request
def security_check():
    result = ts.inspect_flask_request(flask.request)
    if result and result.get("action") == "block":
        return flask.jsonify({"error": "Blocked by TokenShield"}), 403
```

---

## Defense Layer Architecture

```
Layer 1: IP Reputation Gate       — Tor/VPN/Proxy/hostile ASN detection
Layer 2: Device Fingerprint Lock  — Hardware-level device binding
Layer 3: Geographic Impossibility — Haversine physics engine
Layer 4: Request Velocity Control — Real-time sliding window rate limiter
Layer 5: Payload Inspection       — SQL/XSS/injection pattern scanning
Layer 6: Behavioral Biometrics    — Keystroke/mouse/touch ML profiling
Layer 7: AI Ensemble Anomaly      — Isolation Forest + LSTM + Meta-Classifier
```

---

## Latency Budget

| Percentile | Response Time |
|------------|---------------|
| P50        | < 3 ms        |
| P95        | < 10 ms       |
| P99        | < 25 ms       |

---

## Error Codes

| HTTP Code | Meaning                        |
|-----------|--------------------------------|
| 200       | Request analyzed — see action field |
| 400       | Missing required fields        |
| 403       | Account locked or token revoked (fast-path) |
| 500       | Engine internal error          |

---

## Self-Hosting Requirements

```
Python 3.10+
Flask + Flask-CORS
NumPy, scikit-learn, PyTorch (for LSTM)
Redis (optional — for distributed blocklist)
4 GB RAM minimum (ML models loaded)
```

Start engine:
```bash
python engine/server_flask.py
# Listening on http://0.0.0.0:7777
```
