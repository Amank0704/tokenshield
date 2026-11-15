import os
import math
from PIL import Image, ImageDraw, ImageFont

out_dir = "/Users/yashpachhade/tokenshield/diagrams"
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "master_architecture_diagram.png")

# Canvas dimensions: 2750 x 2100 px (Spacious gutters, zero line overlap)
W, H = 2850, 2100
img = Image.new("RGB", (W, H), "#060A12")
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
f_pipe = get_font("bold", 12)

def draw_card(x1, y1, x2, y2, bg="#0E1624", border="#1E2C42", radius=10, width=2):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=bg, outline=border, width=width)

def draw_pill(x, y, w, h, text, bg="#16253A", border="#00D4FF", text_color="#00D4FF"):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h//2, fill=bg, outline=border, width=1)
    draw.text((x + w//2, y + h//2), text, fill=text_color, font=f_badge, anchor="mm")

def draw_flow_arrow(points, color="#00D4FF", width=3, label=None, label_pos=None, label_bg="#080F1D", label_color=None):
    if len(points) < 2:
        return
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=color, width=width)
    
    p_prev = points[-2]
    p_end = points[-1]
    dx = p_end[0] - p_prev[0]
    dy = p_end[1] - p_prev[1]
    angle = math.atan2(dy, dx)
    arrow_len = 13
    p1 = (p_end[0] - arrow_len * math.cos(angle - math.pi / 6), p_end[1] - arrow_len * math.sin(angle - math.pi / 6))
    p2 = (p_end[0] - arrow_len * math.cos(angle + math.pi / 6), p_end[1] - arrow_len * math.sin(angle + math.pi / 6))
    draw.polygon([p1, p_end, p2], fill=color)

    if label and label_pos:
        lx, ly = label_pos
        bbox = draw.textbbox((lx, ly), label, font=f_pipe, anchor="mm")
        pad_x, pad_y = 10, 5
        draw.rounded_rectangle([bbox[0]-pad_x, bbox[1]-pad_y, bbox[2]+pad_x, bbox[3]+pad_y], radius=5, fill=label_bg, outline=color, width=1)
        draw.text((lx, ly), label, fill=label_color or color, font=f_pipe, anchor="mm")

# Left margin: 120 (leaves 0-120 for M3 conduit)
# Right margin: 2630 (leaves 2630-2750 for Layer update conduit)
# Center gutter: 1330 to 1420 (90 px wide)
X_LEFT = 130
X_RIGHT = 2620
X_MID_L = 1330
X_MID_R = 1420

# ─────────────────────────────────────────────────────────────────────────────
# 1. HEADER
# ─────────────────────────────────────────────────────────────────────────────
draw_card(X_LEFT, 25, X_RIGHT, 115, bg="#0B1321", border="#00D4FF", radius=12, width=2)
draw.text(((X_LEFT + X_RIGHT) // 2, 55), "TOKENSHIELD & NEOVAULT — MASTER SYSTEM ARCHITECTURE", fill="#FFFFFF", font=f_hdr, anchor="mm")
draw.text(((X_LEFT + X_RIGHT) // 2, 90), "Nationwide Regional Ingress  •  7-Layer Defense  •  8-Signal AI Engine  •  Sub-100ms Mitigation  •  End-to-End Pipeline Circuit", fill="#00D4FF", font=f_subhdr, anchor="mm")

# ─────────────────────────────────────────────────────────────────────────────
# 2. TIER I: INGRESS (y: 135 to 345)
# ─────────────────────────────────────────────────────────────────────────────
draw_card(X_LEFT, 135, X_RIGHT, 345, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((X_LEFT + 30, 160), "TIER I: GLOBAL & NATIONWIDE REGIONAL INGRESS (WAN / GNS3 TOPOLOGY)", fill="#94A3B8", font=f_tier, anchor="lm")

# Adversary (Left)
draw_card(X_LEFT + 20, 185, X_MID_L - 20, 330, bg="#160C14", border="#FF3B5C", radius=8, width=2)
draw.text((X_LEFT + 40, 205), "ADVERSARY / HIGH-RISK INGRESS NODES", fill="#FF3B5C", font=f_box_title, anchor="lm")
adv_nodes = [
    ("MOSCOW (BULLETPROOF HOST)", "92.118.160.5 • Destructive DDL / Injections"),
    ("FRANKFURT (TOR EXIT RELAY)", "185.220.101.5 • Session Hijacking & Replay"),
    ("BUCHAREST & LAGOS BOTNET", "Distributed credential stuffing & headless bots"),
    ("RED-TEAM ATTACK HARNESS", "Locust Web Swarm • OWASP ZAP • Apache JMeter"),
]
for idx, (title, desc) in enumerate(adv_nodes):
    col, row = idx % 2, idx // 2
    nx = X_LEFT + 40 + col * 570
    ny = 225 + row * 45
    draw_card(nx, ny, nx + 550, ny + 40, bg="#24101D", border="#4D1525", radius=6, width=1)
    draw.text((nx + 15, ny + 12), title, fill="#FF6B8B", font=f_item_title, anchor="lm")
    draw.text((nx + 15, ny + 27), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Sovereign (Right)
draw_card(X_MID_R + 20, 185, X_RIGHT - 20, 330, bg="#081827", border="#00D4FF", radius=8, width=2)
draw.text((X_MID_R + 40, 205), "SOVEREIGN DOMESTIC & TRUSTED FINANCIAL INGRESS NODES", fill="#00D4FF", font=f_box_title, anchor="lm")
clean_nodes = [
    ("MUMBAI CORE DEFENSE GATEWAY", "103.21.58.1 • Primary Financial Production Gateway"),
    ("NCR DELHI MOBILE USERS", "Domestic Retail Banking Customers & Web Traffic"),
    ("BENGALURU API CONSUMERS", "Fintech Partner APIs & Automated Banking SDK"),
    ("TOKYO & SINGAPORE HUBS", "Regional Cross-Border Clearing & SWIFT Partners"),
]
for idx, (title, desc) in enumerate(clean_nodes):
    col, row = idx % 2, idx // 2
    nx = X_MID_R + 40 + col * 570
    ny = 225 + row * 45
    draw_card(nx, ny, nx + 550, ny + 40, bg="#0D2238", border="#154168", radius=6, width=1)
    draw.text((nx + 15, ny + 12), title, fill="#38BDF8", font=f_item_title, anchor="lm")
    draw.text((nx + 15, ny + 27), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# ─────────────────────────────────────────────────────────────────────────────
# 3. TIER II: EDGE & 7 LAYERS (y: 420 to 690)
# ─────────────────────────────────────────────────────────────────────────────
draw_card(X_LEFT, 420, X_RIGHT, 690, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((X_LEFT + 30, 445), "TIER II: EDGE INGRESS & 7-LAYER HIERARCHICAL DEFENSE ARCHITECTURE", fill="#94A3B8", font=f_tier, anchor="lm")

# Nginx WAF (x: X_LEFT + 20 to X_LEFT + 820)
draw_card(X_LEFT + 20, 470, X_LEFT + 820, 670, bg="#101827", border="#FFB800", radius=10, width=2)
draw.text((X_LEFT + 40, 495), "EDGE REVERSE PROXY & WAF (NGINX)", fill="#FFB800", font=f_box_title, anchor="lm")
draw.text((X_LEFT + 40, 517), "Container: 172.20.0.3:80 • Docker Subnet: 172.20.0.0/24", fill="#94A3B8", font=f_box_sub, anchor="lm")
edge_features = [
    "• Ingress Routing & SSL/TLS 1.3 Termination",
    "• Dynamic Blocklist Watcher (blocked_ips.conf)",
    "• Atomic Config Reload within 5 seconds",
    "• Sliding Leaky-Bucket Rate Limiting Zones",
    "• Layer 4/7 Direct Malicious Packet Drop",
]
for i, f in enumerate(edge_features):
    draw.text((X_LEFT + 45, 545 + i * 23), f, fill="#E2E8F0", font=f_item_title, anchor="lm")

# 7 Layers (x: X_LEFT + 860 to X_RIGHT - 20)
draw_card(X_LEFT + 860, 470, X_RIGHT - 20, 670, bg="#071A1A", border="#00FF88", radius=10, width=2)
draw.text((X_LEFT + 880, 495), "THE 7 HIERARCHICAL DEFENSE LAYERS (SWIFT CSP / RBI / PCI-DSS 4.0 COMPLIANT)", fill="#00FF88", font=f_box_title, anchor="lm")
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
    col, row = idx % 2, idx // 2
    lx = X_LEFT + 880 + col * 800
    ly = 520 + row * 35
    draw_card(lx, ly, lx + 780, ly + 31, bg="#0C2522", border="#155543", radius=5, width=1)
    draw.text((lx + 10, ly + 9), ltitle, fill="#5EEAD4", font=f_item_title, anchor="lm")
    draw.text((lx + 10, ly + 21), ldesc, fill="#CBD5E1", font=f_item_desc, anchor="lm")

# ─────────────────────────────────────────────────────────────────────────────
# 4. TIER III: APPS & INTERCEPTOR (y: 760 to 990)
# ─────────────────────────────────────────────────────────────────────────────
draw_card(X_LEFT, 760, X_RIGHT, 990, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((X_LEFT + 30, 785), "TIER III: DIGITAL BANKING PLATFORM & ZERO-BYPASS INTERCEPTION LAYER", fill="#94A3B8", font=f_tier, anchor="lm")

# NeoVault Core (x: X_LEFT + 20 to X_MID_L - 20)
draw_card(X_LEFT + 20, 810, X_MID_L - 20, 970, bg="#0B1A2E", border="#3B82F6", radius=10, width=2)
draw.text((X_LEFT + 40, 833), "NEOVAULT DIGITAL BANKING CORE (FLASK / PYTHON 3.11)", fill="#60A5FA", font=f_box_title, anchor="lm")
draw.text((X_LEFT + 40, 855), "Container: 172.20.0.2:5001 • Multi-Blueprint Architecture", fill="#94A3B8", font=f_box_sub, anchor="lm")
app_routes = [
    ("/api/auth/*", "JWT stateless session tokens, Bcrypt hash, PyOTP TOTP 2FA, Google OAuth 2.0"),
    ("/api/banking/*", "Checking/Savings accounts, ledger balances, beneficiary fund transfers, cards"),
    ("/api/admin/*", "Active session monitor, revocation endpoints, audit logs & telemetry"),
]
for i, (r_title, r_desc) in enumerate(app_routes):
    ry = 880 + i * 27
    draw.text((X_LEFT + 45, ry), r_title, fill="#93C5FD", font=f_item_title, anchor="lm")
    draw.text((X_LEFT + 180, ry), r_desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Interceptor (x: X_MID_R + 20 to X_RIGHT - 20)
draw_card(X_MID_R + 20, 810, X_RIGHT - 20, 970, bg="#0D1E33", border="#00D4FF", radius=10, width=2)
draw.text((X_MID_R + 40, 833), "SECURITY INTERCEPTOR & CLIENT TELEMETRY", fill="#00D4FF", font=f_box_title, anchor="lm")
middleware_points = [
    ("@app.before_request Hook", "Mandatory zero-bypass inspection hook protecting every endpoint"),
    ("Behavioral Collector (JS)", "Captures typing flight/dwell times, mouse velocity & canvas entropy"),
    ("Synchronous Evaluation", "Hands request context & telemetry to TokenShield Engine (:7777)"),
    ("Instant Revocation Check", "Queries Redis O(1) cache for session & IP status prior to execution"),
]
for i, (m_title, m_desc) in enumerate(middleware_points):
    my = 860 + i * 25
    draw.text((X_MID_R + 45, my), m_title, fill="#38BDF8", font=f_item_title, anchor="lm")
    draw.text((X_MID_R + 290, my), m_desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# ─────────────────────────────────────────────────────────────────────────────
# 5. TIER IV: TOKENSHIELD AI ENGINE (y: 1060 to 1370)
# ─────────────────────────────────────────────────────────────────────────────
draw_card(X_LEFT, 1060, X_RIGHT, 1370, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((X_LEFT + 30, 1085), "TIER IV: TOKENSHIELD AI-POWERED THREAT DEFENSE ENGINE (STANDALONE MICROSERVICE :7777)", fill="#94A3B8", font=f_tier, anchor="lm")

# 8 Signals (x: X_LEFT + 20 to X_MID_L - 20)
draw_card(X_LEFT + 20, 1110, X_MID_L - 20, 1350, bg="#150B24", border="#A855F7", radius=10, width=2)
draw.text((X_LEFT + 40, 1133), "8-SIGNAL REAL-TIME THREAT ANALYSIS MATRIX", fill="#C084FC", font=f_box_title, anchor="lm")
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
    col, row = idx % 2, idx // 2
    sx = X_LEFT + 40 + col * 570
    sy = 1155 + row * 45
    draw_card(sx, sy, sx + 550, sy + 39, bg="#221138", border="#492473", radius=6, width=1)
    draw.text((sx + 10, sy + 12), stitle, fill="#E9D5FF", font=f_item_title, anchor="lm")
    draw.text((sx + 10, sy + 26), sdesc, fill="#CBD5E1", font=f_item_desc, anchor="lm")

# 3 ML Models (x: X_MID_R + 20 to X_RIGHT - 20)
draw_card(X_MID_R + 20, 1110, X_RIGHT - 20, 1350, bg="#150B24", border="#C084FC", radius=10, width=2)
draw.text((X_MID_R + 40, 1133), "3-TIER MACHINE LEARNING CORE & RISK CLASSIFICATION", fill="#C084FC", font=f_box_title, anchor="lm")
ml_models = [
    ("MODEL A: ISOLATION FOREST", "300 Trees • 9 Features • Latency: 2.47ms • Unsupervised Zero-Day Outlier Detector"),
    ("MODEL B: SEQUENCE LSTM AUTOENCODER", "PyTorch MPS/CPU • 10-Step Sliding Buffer • NASA Sequences • Catches Workflow Jumps"),
    ("MODEL C: CALIBRATED META-CLASSIFIER", "HistGradientBoosting + Platt Sigmoid • ROC-AUC: 0.8943 • Precision: 98.18%"),
    ("COMPOSITE THREAT SCORER", "S = min(Sum(s_i), 1.0) • CRITICAL THRESHOLD: S >= 0.85 Triggers Immediate Mitigation"),
]
for idx, (mtitle, mdesc) in enumerate(ml_models):
    my = 1155 + idx * 45
    draw_card(X_MID_R + 40, my, X_RIGHT - 40, my + 39, bg="#221138", border="#492473", radius=6, width=1)
    draw.text((X_MID_R + 55, my + 12), mtitle, fill="#E9D5FF", font=f_item_title, anchor="lm")
    draw.text((X_MID_R + 55, my + 26), mdesc, fill="#CBD5E1", font=f_item_desc, anchor="lm")

# ─────────────────────────────────────────────────────────────────────────────
# 6. TIERS V, VI, VII: PERSISTENCE, MITIGATION & WAR ROOM (y: 1450 to 2000)
# ─────────────────────────────────────────────────────────────────────────────
draw_card(X_LEFT, 1450, X_RIGHT, 2010, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((X_LEFT + 30, 1475), "TIERS V, VI & VII: STATE PERSISTENCE, SUB-100MS MITIGATION & SECOPS WAR ROOM", fill="#94A3B8", font=f_tier, anchor="lm")

# Tier V: State & Persistence (x: X_LEFT + 20 to X_LEFT + 750)
X_T5_R = X_LEFT + 750
draw_card(X_LEFT + 20, 1500, X_T5_R, 1990, bg="#130D24", border="#9333EA", radius=10, width=2)
draw.text((X_LEFT + 40, 1525), "TIER V: HIGH-SPEED STATE & PERSISTENCE", fill="#C084FC", font=f_box_title, anchor="lm")

db_items = [
    ("REDIS 7 IN-MEMORY CACHE (PORT 6379)", "Container 172.20.0.4 • Sub-ms Cache", True),
    ("  • ts:block:<token_hash>", "O(1) Token Revocation Blacklist (~0ms)", False),
    ("  • ts:vel:<ip>", "60-Sec Request Velocity Sliding Window", False),
    ("  • ts:fp:<fp_hash>", "Device Hardware Fingerprint Ban (72h)", False),
    ("  • ts:geo:<session>", "Geo-IP Coordinate & Last Seen Time", False),
    ("SQLITE DATABASE (tokenshield.db)", "Relational Store via SQLAlchemy ORM", True),
    ("  • Users & Auth Schema", "Credentials (Bcrypt), TOTP Keys, Status", False),
    ("  • Core Banking Ledger", "Accounts, Balances, Cards, Transfers", False),
    ("  • Incident & Audit Trail", "Forensic Incident Logs & Anomaly Records", False),
]
for i, (d_title, d_desc, is_hdr) in enumerate(db_items):
    dy = 1560 + i * 45
    if is_hdr:
        draw_card(X_LEFT + 35, dy - 12, X_T5_R - 15, dy + 18, bg="#201538", border="#6B21A8", radius=4, width=1)
        draw.text((X_LEFT + 45, dy + 2), d_title, fill="#E9D5FF", font=f_item_title, anchor="lm")
        draw.text((X_LEFT + 400, dy + 2), d_desc, fill="#C084FC", font=f_item_desc, anchor="lm")
    else:
        draw.text((X_LEFT + 45, dy), d_title, fill="#D8B4FE", font=f_item_title, anchor="lm")
        draw.text((X_LEFT + 310, dy), d_desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Tier VI: Mitigation Orchestrator (x: X_T5_R + 70 to X_RIGHT - 750)
X_T6_L = X_T5_R + 70
X_T6_R = X_RIGHT - 750
draw_card(X_T6_L, 1500, X_T6_R, 1990, bg="#1E0B14", border="#EF4444", radius=10, width=2)
draw.text((X_T6_L + 20, 1525), "TIER VI: 8-STEP PROGRESSIVE MITIGATION (S >= 0.85)", fill="#EF4444", font=f_box_title, anchor="lm")

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
    my = 1560 + i * 51
    draw_card(X_T6_L + 15, my - 16, X_T6_R - 15, my + 24, bg="#2D0F1C", border="#5E1D2D", radius=5, width=1)
    draw.text((X_T6_L + 30, my + 2), m_name, fill="#FCA5A5", font=f_item_title, anchor="lm")
    draw_pill(X_T6_L + 390, my - 8, 65, 22, m_lat, bg="#4A0B1A", border="#EF4444", text_color="#FECDD3")
    draw.text((X_T6_L + 475, my + 2), m_action, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Tier VII: War Room (x: X_T6_R + 70 to X_RIGHT - 20)
X_T7_L = X_T6_R + 70
draw_card(X_T7_L, 1500, X_RIGHT - 20, 1990, bg="#07191A", border="#14B8A6", radius=10, width=2)
draw.text((X_T7_L + 20, 1525), "TIER VII: CYBER COMMAND CENTER (:7777)", fill="#2DD4BF", font=f_box_title, anchor="lm")

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
    sy = 1565 + i * 58
    draw_card(X_T7_L + 15, sy - 16, X_RIGHT - 35, sy + 28, bg="#0D2728", border="#144F4B", radius=6, width=1)
    draw.text((X_T7_L + 30, sy - 2), s_title, fill="#5EEAD4", font=f_item_title, anchor="lm")
    draw.text((X_T7_L + 30, sy + 13), s_desc, fill="#CCFBF1", font=f_item_desc, anchor="lm")

# ─────────────────────────────────────────────────────────────────────────────
# 7. HIGH-VISIBILITY PIPELINE CONNECTIONS (ZERO TEXT OVERLAP)
# ─────────────────────────────────────────────────────────────────────────────

# PATH 1: Adversary Ingress -> Nginx WAF (Red)
draw_flow_arrow(
    [(700, 330), (700, 380), (380, 380), (380, 470)],
    color="#FF3B5C", width=4,
    label="MALICIOUS EXPLOITS / STOLEN JWTs / BOT FLOOD",
    label_pos=(540, 380), label_color="#FF6B8B"
)

# PATH 2: Sovereign Clean Ingress -> Nginx WAF (Cyan)
draw_flow_arrow(
    [(2000, 330), (2000, 400), (620, 400), (620, 470)],
    color="#00D4FF", width=4,
    label="CLEAN BANKING TRAFFIC / TLS 1.3 HTTPS",
    label_pos=(1350, 400), label_color="#38BDF8"
)

# PATH 3: Nginx -> NeoVault Banking App Core (Green)
draw_flow_arrow(
    [(500, 670), (500, 810)],
    color="#00FF88", width=4,
    label="proxy_pass (EDGE FILTERED)",
    label_pos=(500, 735), label_color="#00FF88"
)

# PATH 4: NeoVault App -> Security Interceptor (Cyan, across center gutter)
draw_flow_arrow(
    [(X_MID_L - 20, 890), (X_MID_R + 20, 890)],
    color="#00D4FF", width=4,
    label="ZERO-BYPASS INTERCEPT",
    label_pos=((X_MID_L + X_MID_R) // 2, 865), label_color="#00D4FF"
)

# PATH 5: Interceptor -> TokenShield AI Security Engine (Purple, through center gutter)
draw_flow_arrow(
    [(X_MID_R + 250, 970), (X_MID_R + 250, 1025), ((X_MID_L + X_MID_R) // 2, 1025), ((X_MID_L + X_MID_R) // 2, 1110)],
    color="#C084FC", width=4,
    label="POST /api/v1/analyze (PAYLOAD + BIOMETRIC TELEMETRY)",
    label_pos=(1600, 1025), label_color="#E9D5FF"
)

# PATH 6: AI Engine -> 7 Defense Layers Health Update (Emerald, around right margin!)
draw_flow_arrow(
    [(X_RIGHT - 20, 1230), (X_RIGHT + 40, 1230), (X_RIGHT + 40, 570), (X_RIGHT - 20, 570)],
    color="#5EEAD4", width=3,
    label="UPDATE DEFENSE LAYERS (L1 - L7)",
    label_pos=(X_RIGHT + 60, 900), label_color="#5EEAD4"
)

# PATH 7: AI Engine -> 8-Step Mitigation Trigger (Red, straight down center gutter)
draw_flow_arrow(
    [((X_MID_L + X_MID_R) // 2, 1350), ((X_MID_L + X_MID_R) // 2, 1500)],
    color="#EF4444", width=5,
    label="THREAT DETECTED (S >= 0.85) -> TRIGGER 8-STEP MITIGATION",
    label_pos=((X_MID_L + X_MID_R) // 2, 1420), label_color="#FECDD3"
)

# PATH 8: Step 1 & 2 -> Redis Cache (Red/Purple, across Gutter V-VI)
draw_flow_arrow(
    [(X_T6_L, 1610), (X_T5_R, 1610)],
    color="#EF4444", width=4,
    label="M1: REVOKE & M2: IP BAN",
    label_pos=((X_T5_R + X_T6_L) // 2, 1585), label_color="#FCA5A5"
)

# PATH 9: Step 5 -> SQLite DB Hard Lock (Red, across Gutter V-VI)
draw_flow_arrow(
    [(X_T6_L, 1815), (X_T5_R, 1815)],
    color="#EF4444", width=4,
    label="M5: LOCK ACCOUNT IN DB",
    label_pos=((X_T5_R + X_T6_L) // 2, 1790), label_color="#FCA5A5"
)

# PATH 10: Step 3 -> Nginx Edge Reload (Orange Loop, around left margin!)
draw_flow_arrow(
    [(X_T6_L, 1710), (X_T5_R - 40, 1710), (X_T5_R - 40, 1425), (60, 1425), (60, 570), (X_LEFT + 20, 570)],
    color="#FFB800", width=4,
    label="M3: WRITE blocked_ips.conf (AUTO-RELOAD <= 5s)",
    label_pos=(380, 1425), label_color="#FDE68A"
)

# PATH 11: Step 8 -> Cyber Command Center Live SSE Stream (Cyan, across Gutter VI-VII)
draw_flow_arrow(
    [(X_T6_R, 1945), (X_T7_L, 1945)],
    color="#14B8A6", width=4,
    label="M8: PUSH LIVE INCIDENT SSE PACKET",
    label_pos=((X_T6_R + X_T7_L) // 2, 1920), label_color="#5EEAD4"
)

# Save high-res PNG image
img.save(out_file, "PNG", dpi=(300, 300))
print(f"Master Architecture Diagram v2 generated successfully at: {out_file}")
