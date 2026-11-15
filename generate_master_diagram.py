import os
import math
from PIL import Image, ImageDraw, ImageFont

out_dir = "/Users/yashpachhade/tokenshield/diagrams"
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "master_architecture_diagram.png")

# Canvas dimensions (2K ultra-crisp resolution)
W, H = 2400, 1750
img = Image.new("RGB", (W, H), "#080D16")
draw = ImageDraw.Draw(img)

def get_font(font_type="arial", size=14):
    try:
        if font_type == "bold":
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
        elif font_type == "mono":
            return ImageFont.truetype("/System/Library/Fonts/Courier.dfont", size)
        else:
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

f_hdr = get_font("bold", 34)
f_subhdr = get_font("arial", 18)
f_tier = get_font("bold", 20)
f_box_title = get_font("bold", 16)
f_box_sub = get_font("arial", 13)
f_item_title = get_font("bold", 13)
f_item_desc = get_font("arial", 11)
f_badge = get_font("bold", 11)

def draw_card(x1, y1, x2, y2, bg="#0E1624", border="#1E2C42", radius=10, width=2):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=bg, outline=border, width=width)

def draw_pill(x, y, w, h, text, bg="#16253A", border="#00D4FF", text_color="#00D4FF"):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h//2, fill=bg, outline=border, width=1)
    draw.text((x + w//2, y + h//2), text, fill=text_color, font=f_badge, anchor="mm")

def draw_arrow_down(x, y1, y2, color="#00D4FF", width=3, label=None):
    draw.line([x, y1, x, y2], fill=color, width=width)
    draw.polygon([(x - 6, y2 - 10), (x, y2), (x + 6, y2 - 10)], fill=color)
    if label:
        draw.text((x + 10, (y1 + y2)//2), label, fill=color, font=f_badge, anchor="lm")

def draw_arrow_right(x1, y, x2, color="#00D4FF", width=3, label=None):
    draw.line([x1, y, x2, y], fill=color, width=width)
    draw.polygon([(x2 - 10, y - 6), (x2, y), (x2 - 10, y + 6)], fill=color)
    if label:
        draw.text(((x1 + x2)//2, y - 10), label, fill=color, font=f_badge, anchor="mb")

# ─────────────────────────────────────────────────────────────────────────────
# 1. TOP HEADER BANNER
# ─────────────────────────────────────────────────────────────────────────────
draw_card(40, 30, W - 40, 130, bg="#0B1321", border="#00D4FF", radius=12, width=2)
draw.text((W // 2, 65), "TOKENSHIELD & NEOVAULT — MASTER SYSTEM ARCHITECTURE", fill="#FFFFFF", font=f_hdr, anchor="mm")
draw.text((W // 2, 102), "Nationwide & Global Regional Ingress  •  7-Layer Hierarchical Defense  •  8-Signal Parallel AI Engine  •  Sub-100ms Automated Mitigation", fill="#00D4FF", font=f_subhdr, anchor="mm")

# ─────────────────────────────────────────────────────────────────────────────
# 2. TIER I: NATIONWIDE & GLOBAL REGIONAL INGRESS
# ─────────────────────────────────────────────────────────────────────────────
draw_card(40, 150, W - 40, 370, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((70, 180), "TIER I: GLOBAL & NATIONWIDE REGIONAL INGRESS (WAN / GNS3 TOPOLOGY)", fill="#94A3B8", font=f_tier, anchor="lm")

# Left: Adversary & High-Risk Zones
draw_card(60, 205, 1160, 350, bg="#140D17", border="#FF3B5C", radius=8, width=2)
draw.text((80, 228), "ADVERSARY / HIGH-RISK INGRESS NODES", fill="#FF3B5C", font=f_box_title, anchor="lm")

adv_nodes = [
    ("MOSCOW (BULLETPROOF HOST)", "92.118.160.5 • Destructive DDL / Injections"),
    ("FRANKFURT (TOR EXIT RELAY)", "185.220.101.5 • Session Hijacking & Replay"),
    ("BUCHAREST & LAGOS BOTNET", "Distributed credential stuffing & headless bots"),
    ("RED-TEAM ATTACK HARNESS", "Locust Web Swarm • OWASP ZAP • Apache JMeter"),
]
for idx, (title, desc) in enumerate(adv_nodes):
    col = idx % 2
    row = idx // 2
    nx = 80 + col * 530
    ny = 250 + row * 45
    draw_card(nx, ny, nx + 510, ny + 40, bg="#20111F", border="#4D1525", radius=6, width=1)
    draw.text((nx + 15, ny + 12), title, fill="#FF6B8B", font=f_item_title, anchor="lm")
    draw.text((nx + 15, ny + 28), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Right: Sovereign Domestic & Global Partner Zones
draw_card(1240, 205, W - 60, 350, bg="#0A1A2A", border="#00D4FF", radius=8, width=2)
draw.text((1260, 228), "SOVEREIGN DOMESTIC & TRUSTED FINANCIAL INGRESS NODES", fill="#00D4FF", font=f_box_title, anchor="lm")

clean_nodes = [
    ("MUMBAI CORE DEFENSE GATEWAY", "103.21.58.1 • Primary Financial Production Gateway"),
    ("NCR DELHI MOBILE USERS", "Domestic Retail Banking Customers & Web Traffic"),
    ("BENGALURU API CONSUMERS", "Fintech Partner APIs & Automated Banking SDK"),
    ("TOKYO & SINGAPORE HUBS", "Regional Cross-Border Clearing & SWIFT Partners"),
]
for idx, (title, desc) in enumerate(clean_nodes):
    col = idx % 2
    row = idx // 2
    nx = 1260 + col * 520
    ny = 250 + row * 45
    draw_card(nx, ny, nx + 500, ny + 40, bg="#0D2238", border="#154168", radius=6, width=1)
    draw.text((nx + 15, ny + 12), title, fill="#38BDF8", font=f_item_title, anchor="lm")
    draw.text((nx + 15, ny + 28), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Arrows from Ingress to Edge
draw_arrow_down(610, 350, 400, color="#FF3B5C", width=3, label="Attack Traffic")
draw_arrow_down(1790, 350, 400, color="#00D4FF", width=3, label="Banking Traffic")

# ─────────────────────────────────────────────────────────────────────────────
# 3. TIER II: PERIMETER EDGE & 7 HIERARCHICAL DEFENSE LAYERS
# ─────────────────────────────────────────────────────────────────────────────
draw_card(40, 400, W - 40, 680, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((70, 430), "TIER II: EDGE INGRESS & 7-LAYER HIERARCHICAL DEFENSE ARCHITECTURE", fill="#94A3B8", font=f_tier, anchor="lm")

# Edge Proxy Container
draw_card(60, 455, 620, 660, bg="#101827", border="#FFB800", radius=10, width=2)
draw.text((80, 480), "EDGE REVERSE PROXY & WAF (NGINX)", fill="#FFB800", font=f_box_title, anchor="lm")
draw.text((80, 502), "Container: 172.20.0.3:80 • Docker Subnet: 172.20.0.0/24", fill="#94A3B8", font=f_box_sub, anchor="lm")

edge_features = [
    "• Ingress Routing & SSL/TLS Termination",
    "• Dynamic Blocklist Watcher (blocked_ips.conf)",
    "• Atomic Config Reload within 5 seconds",
    "• Sliding Leaky-Bucket Rate Limiting Zones",
    "• Layer 4/7 Direct Malicious Packet Drop",
]
for i, f in enumerate(edge_features):
    draw.text((85, 532 + i * 24), f, fill="#E2E8F0", font=f_item_title, anchor="lm")

# 7 Defense Layers Grid
draw_card(650, 455, W - 60, 660, bg="#0A1E1E", border="#00FF88", radius=10, width=2)
draw.text((670, 480), "THE 7 HIERARCHICAL DEFENSE LAYERS (SWIFT CSP / RBI / PCI-DSS 4.0 COMPLIANT)", fill="#00FF88", font=f_box_title, anchor="lm")

layers = [
    ("L1: PERIMETER EDGE", "Reverse proxy, CIDR firewalls, TLS handshake posture"),
    ("L2: DEVICE POSTURE", "Canvas/WebGL entropy, UA consistency, bot signatures"),
    ("L3: GEO INTELLIGENCE", "Haversine supersonic transit check, high-risk nation flags"),
    ("L4: NETWORK & VELOCITY", "Sliding rate windows, DoS suppression, Tor exit isolation"),
    ("L5: TRANSACTION TRUST", "Payload regex sanitizer (SQLi/XSS), navigation step guard"),
    ("L6: IDENTITY INTEGRITY", "JWT cryptobinding, typing WPM & mouse jitter biometrics"),
    ("L7: AI MULTI-MODEL CORE", "Isolation Forest, Deep Sequence LSTM, Meta-Classifier"),
]
for idx, (ltitle, ldesc) in enumerate(layers):
    col = idx % 2
    row = idx // 2
    lx = 670 + col * 520
    ly = 505 + row * 38
    w_box = 505 if col == 0 else 505
    draw_card(lx, ly, lx + w_box, ly + 34, bg="#0E2822", border="#1B5E4A", radius=6, width=1)
    draw.text((lx + 10, ly + 11), ltitle, fill="#5EEAD4", font=f_item_title, anchor="lm")
    draw.text((lx + 10, ly + 24), ldesc, fill="#CBD5E1", font=f_item_desc, anchor="lm")

# Arrow from Edge to Application Tier
draw_arrow_down(340, 660, 710, color="#00FF88", width=3, label="proxy_pass")

# ─────────────────────────────────────────────────────────────────────────────
# 4. TIER III: DIGITAL BANKING APPS & INTERCEPTION LAYER
# ─────────────────────────────────────────────────────────────────────────────
draw_card(40, 710, W - 40, 930, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((70, 740), "TIER III: DIGITAL BANKING PLATFORM & ZERO-BYPASS INTERCEPTION LAYER", fill="#94A3B8", font=f_tier, anchor="lm")

# NeoVault Flask Container
draw_card(60, 760, 1300, 910, bg="#0E1E36", border="#3B82F6", radius=10, width=2)
draw.text((80, 785), "NEOVAULT DIGITAL BANKING CORE (FLASK / PYTHON 3.11)", fill="#60A5FA", font=f_box_title, anchor="lm")
draw.text((80, 808), "Container: 172.20.0.2:5001 • Multi-Blueprint Architecture", fill="#94A3B8", font=f_box_sub, anchor="lm")

app_routes = [
    ("/api/auth/*", "JWT stateless session tokens, Bcrypt hash, PyOTP TOTP 2FA, Google OAuth 2.0"),
    ("/api/banking/*", "Checking/Savings accounts, ledger balances, beneficiary fund transfers, cards"),
    ("/api/admin/*", "Active session monitor, revocation endpoints, audit logs & telemetry"),
]
for i, (r_title, r_desc) in enumerate(app_routes):
    ry = 830 + i * 25
    draw.text((85, ry), r_title, fill="#93C5FD", font=f_item_title, anchor="lm")
    draw.text((220, ry), r_desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Middleware Interceptor
draw_card(1330, 760, W - 60, 910, bg="#131F33", border="#00D4FF", radius=10, width=2)
draw.text((1350, 785), "SECURITY INTERCEPTOR & CLIENT TELEMETRY", fill="#00D4FF", font=f_box_title, anchor="lm")

middleware_points = [
    ("@app.before_request Filter", "Mandatory zero-bypass inspection hook protecting all endpoints"),
    ("Behavioral Collector (JS)", "Captures typing flight/dwell times, mouse velocity & canvas entropy"),
    ("Synchronous Evaluation", "Hands request context & telemetry to TokenShield Engine (:7777)"),
    ("State Verification", "Queries Redis O(1) cache for instant session & IP status checks"),
]
for i, (m_title, m_desc) in enumerate(middleware_points):
    my = 812 + i * 23
    draw.text((1355, my), m_title, fill="#38BDF8", font=f_item_title, anchor="lm")
    draw.text((1580, my), m_desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Arrow from App to TokenShield Engine
draw_arrow_down(W // 2, 930, 960, color="#A855F7", width=3, label="POST /api/v1/analyze")

# ─────────────────────────────────────────────────────────────────────────────
# 5. TIER IV: TOKENSHIELD AI SECURITY ENGINE
# ─────────────────────────────────────────────────────────────────────────────
draw_card(40, 960, W - 40, 1260, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((70, 990), "TIER IV: TOKENSHIELD AI-POWERED THREAT DEFENSE ENGINE (PORT 7777)", fill="#94A3B8", font=f_tier, anchor="lm")

# 8 Signals
draw_card(60, 1010, 1150, 1240, bg="#160E26", border="#A855F7", radius=10, width=2)
draw.text((80, 1032), "8-SIGNAL REAL-TIME THREAT ANALYSIS MATRIX", fill="#C084FC", font=f_box_title, anchor="lm")

signals_list = [
    ("S1: IP REPUTATION (0.25)", "Tor exits, VPNs, datacenters, hostile CIDRs"),
    ("S2: REQUEST VELOCITY (0.30)", "Redis sliding window rate counter (60s)"),
    ("S3: SESSION DRIFT (0.30)", "IP address shift, User-Agent header tampering"),
    ("S4: PAYLOAD SANITIZER (0.40)", "SQL Injection (UNION/DROP) & XSS patterns"),
    ("S5: BEHAVIORAL BIOMETRICS (0.25)", "Welford typing WPM & mouse jitter variance"),
    ("S6: GEO IMPOSSIBILITY (0.35)", "Haversine supersonic transit check (>900 km/h)"),
    ("S7: ENDPOINT RISK (0.20)", "High-value transfer & auth route weighting"),
    ("S8: WORKFLOW INTEGRITY (0.30)", "Deep sequence navigation order enforcement"),
]
for idx, (stitle, sdesc) in enumerate(signals_list):
    col = idx % 2
    row = idx // 2
    sx = 80 + col * 520
    sy = 1055 + row * 43
    draw_card(sx, sy, sx + 505, sy + 38, bg="#23143A", border="#4C2875", radius=6, width=1)
    draw.text((sx + 10, sy + 13), stitle, fill="#E9D5FF", font=f_item_title, anchor="lm")
    draw.text((sx + 10, sy + 27), sdesc, fill="#CBD5E1", font=f_item_desc, anchor="lm")

# 3 ML Models & Scorer
draw_card(1180, 1010, W - 60, 1240, bg="#160E26", border="#C084FC", radius=10, width=2)
draw.text((1200, 1032), "3-TIER MACHINE LEARNING CORE & RISK CLASSIFICATION", fill="#C084FC", font=f_box_title, anchor="lm")

ml_models = [
    ("MODEL A: ISOLATION FOREST", "300 Trees • 9 Features • Latency: 2.47ms • Unsupervised Zero-Day Outlier Detector"),
    ("MODEL B: SEQUENCE LSTM AUTOENCODER", "PyTorch MPS/CPU • 10-Step Sliding Buffer • NASA Sequences • Catches Workflow Jumps"),
    ("MODEL C: CALIBRATED META-CLASSIFIER", "HistGradientBoosting + Platt Sigmoid • ROC-AUC: 0.8943 • Precision: 98.18%"),
    ("COMPOSITE THREAT SCORER", "S = min(Sum(s_i), 1.0) • CRITICAL THRESHOLD: S >= 0.85 Triggers Immediate Mitigation"),
]
for idx, (mtitle, mdesc) in enumerate(ml_models):
    my = 1055 + idx * 43
    draw_card(1200, my, W - 80, my + 38, bg="#23143A", border="#4C2875", radius=6, width=1)
    draw.text((1215, my + 13), mtitle, fill="#E9D5FF", font=f_item_title, anchor="lm")
    draw.text((1215, my + 27), mdesc, fill="#CBD5E1", font=f_item_desc, anchor="lm")

# ─────────────────────────────────────────────────────────────────────────────
# 6. TIER V, VI, VII: PERSISTENCE, MITIGATION & COMMAND CENTER
# ─────────────────────────────────────────────────────────────────────────────
draw_card(40, 1290, W - 40, 1690, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((70, 1320), "TIERS V, VI & VII: STATE PERSISTENCE, SUB-100MS MITIGATION & SECOPS WAR ROOM", fill="#94A3B8", font=f_tier, anchor="lm")

# Tier V: Persistence & In-Memory Store
draw_card(60, 1340, 780, 1670, bg="#141124", border="#9333EA", radius=10, width=2)
draw.text((80, 1365), "TIER V: HIGH-SPEED STATE & PERSISTENCE", fill="#C084FC", font=f_box_title, anchor="lm")

db_items = [
    ("REDIS 7 IN-MEMORY CACHE (PORT 6379)", "Container 172.20.0.4 • Sub-ms State Cache", True),
    ("  • ts:block:<token_hash>", "O(1) Token Revocation Blacklist (~0ms)", False),
    ("  • ts:vel:<ip>", "60-Sec Request Velocity Sliding Window", False),
    ("  • ts:fp:<fp_hash>", "Device Hardware Fingerprint Ban (72h)", False),
    ("  • ts:geo:<session>", "Geo-IP Coordinate & Last Seen Timestamp", False),
    ("SQLITE DATABASE (tokenshield.db)", "Relational Store via SQLAlchemy ORM", True),
    ("  • Users & Auth Schema", "Credentials (Bcrypt), TOTP Keys, Status", False),
    ("  • Core Banking Ledger", "Accounts, Balances, Cards, Transfers", False),
    ("  • Incident & Audit Trail", "Forensic Incident Logs & Anomaly Records", False),
]
for i, (d_title, d_desc, is_hdr) in enumerate(db_items):
    dy = 1395 + i * 29
    if is_hdr:
        draw_card(75, dy - 12, 765, dy + 14, bg="#201538", border="#6B21A8", radius=4, width=1)
        draw.text((85, dy + 1), d_title, fill="#E9D5FF", font=f_item_title, anchor="lm")
        draw.text((410, dy + 1), d_desc, fill="#C084FC", font=f_item_desc, anchor="lm")
    else:
        draw.text((85, dy), d_title, fill="#D8B4FE", font=f_item_title, anchor="lm")
        draw.text((310, dy), d_desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Tier VI: 8-Step Mitigation Orchestrator
draw_card(805, 1340, 1615, 1670, bg="#1F0D15", border="#EF4444", radius=10, width=2)
draw.text((825, 1365), "TIER VI: 8-STEP PROGRESSIVE MITIGATION (S >= 0.85)", fill="#EF4444", font=f_box_title, anchor="lm")

mit_steps = [
    ("STEP 1: O(1) REDIS TOKEN REVOCATION", "~0 ms", "Invalidates JWT token hash in Redis cache immediately"),
    ("STEP 2: REDIS IP BLACKLIST", "~0 ms", "Appends client IP to blocked_ip set with 24-hour TTL"),
    ("STEP 3: NGINX EDGE RULE PUSH", "<= 5 s", "Writes deny rule to blocked_ips.conf; signals auto-reload"),
    ("STEP 4: DEVICE FINGERPRINT BAN", "~0 ms", "Bans client canvas/hardware fingerprint for 72 hours"),
    ("STEP 5: ACCOUNT HARD / 2FA LOCK", "~10 ms", "Sets failed_attempts=99 and is_active=False in DB"),
    ("STEP 6: COORDINATED ATTACK SCAN", "~10 ms", "Correlates matching IP/fingerprints across all accounts"),
    ("STEP 7: SMTP SECURITY ALERT DISPATCH", "async", "Sends automated security incident notification to SOC"),
    ("STEP 8: LIVE COMMAND CENTER SSE PUSH", "~0 ms", "Broadcasts event telemetry to the War Room dashboard"),
]
for i, (m_name, m_lat, m_action) in enumerate(mit_steps):
    my = 1395 + i * 33
    draw_card(820, my - 12, 1600, my + 17, bg="#2B111D", border="#5A1C2C", radius=5, width=1)
    draw.text((830, my + 2), m_name, fill="#FCA5A5", font=f_item_title, anchor="lm")
    draw_pill(1150, my - 8, 70, 20, m_lat, bg="#450A1A", border="#EF4444", text_color="#FECDD3")
    draw.text((1235, my + 2), m_action, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Tier VII: War Room & Cyber Command Center
draw_card(1640, 1340, W - 60, 1670, bg="#081C1D", border="#14B8A6", radius=10, width=2)
draw.text((1660, 1365), "TIER VII: CYBER COMMAND CENTER (:7777)", fill="#2DD4BF", font=f_box_title, anchor="lm")

soc_items = [
    ("GLOBAL THREAT MAP (184 REGIONS)", "Live SVG visual map tracking attack origins"),
    ("MUMBAI DEFENSE RADAR CORE", "Real-time radar sweep over primary banking hub"),
    ("SUB-SECOND SSE TELEMETRY STREAM", "Event stream displaying incident cards live"),
    ("7-LAYER DEFENSE HEALTH RADAR", "Visual polygon showing health for layers L1-L7"),
    ("AI THREAT EXPLAINER ENGINE", "Dynamic natural language incident narratives"),
    ("RED-TEAM ATTACK TESTBENCH", "GUI triggers for Token Replay, DDoS, SQLi, Bots"),
    ("VERIFICATION TEST HARNESS", "Integrated with Locust, ZAP & JMeter tests"),
]
for i, (s_title, s_desc) in enumerate(soc_items):
    sy = 1400 + i * 36
    draw_card(1660, sy - 14, W - 80, sy + 18, bg="#0E2B2C", border="#134E4A", radius=6, width=1)
    draw.text((1675, sy - 2), s_title, fill="#5EEAD4", font=f_item_title, anchor="lm")
    draw.text((1675, sy + 10), s_desc, fill="#CCFBF1", font=f_item_desc, anchor="lm")

# Save high-res PNG image
img.save(out_file, "PNG", dpi=(300, 300))
print(f"Master Architecture Diagram generated successfully at: {out_file}")
