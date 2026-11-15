import os
import math
from PIL import Image, ImageDraw, ImageFont

out_dir = "/Users/yashpachhade/tokenshield/diagrams"
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "master_architecture_diagram.png")

# Canvas dimensions (High density, crisp 2600 x 2050)
W, H = 2600, 2050
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
    # Draw line segments
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=color, width=width)
    
    # Arrow head at the last segment
    p_prev = points[-2]
    p_end = points[-1]
    dx = p_end[0] - p_prev[0]
    dy = p_end[1] - p_prev[1]
    angle = math.atan2(dy, dx)
    arrow_len = 12
    p1 = (p_end[0] - arrow_len * math.cos(angle - math.pi / 6), p_end[1] - arrow_len * math.sin(angle - math.pi / 6))
    p2 = (p_end[0] - arrow_len * math.cos(angle + math.pi / 6), p_end[1] - arrow_len * math.sin(angle + math.pi / 6))
    draw.polygon([p1, p_end, p2], fill=color)

    # Optional Label along path
    if label and label_pos:
        lx, ly = label_pos
        bbox = draw.textbbox((lx, ly), label, font=f_pipe, anchor="mm")
        pad_x, pad_y = 8, 4
        draw.rounded_rectangle([bbox[0]-pad_x, bbox[1]-pad_y, bbox[2]+pad_x, bbox[3]+pad_y], radius=4, fill=label_bg, outline=color, width=1)
        draw.text((lx, ly), label, fill=label_color or color, font=f_pipe, anchor="mm")

# ─────────────────────────────────────────────────────────────────────────────
# 1. TOP HEADER BANNER
# ─────────────────────────────────────────────────────────────────────────────
draw_card(50, 25, W - 50, 115, bg="#0B1321", border="#00D4FF", radius=12, width=2)
draw.text((W // 2, 55), "TOKENSHIELD & NEOVAULT — MASTER SYSTEM ARCHITECTURE", fill="#FFFFFF", font=f_hdr, anchor="mm")
draw.text((W // 2, 90), "Nationwide Regional Ingress  •  7-Layer Defense  •  8-Signal AI Engine  •  Sub-100ms Mitigation  •  End-to-End Pipeline Circuit", fill="#00D4FF", font=f_subhdr, anchor="mm")

# ─────────────────────────────────────────────────────────────────────────────
# 2. TIER I: GLOBAL & NATIONWIDE REGIONAL INGRESS
# ─────────────────────────────────────────────────────────────────────────────
draw_card(50, 135, W - 50, 345, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((80, 160), "TIER I: GLOBAL & NATIONWIDE REGIONAL INGRESS (WAN / GNS3 TOPOLOGY)", fill="#94A3B8", font=f_tier, anchor="lm")

# Left: Adversary & High-Risk Zones (x: 70 to 1250)
draw_card(70, 185, 1250, 330, bg="#160C14", border="#FF3B5C", radius=8, width=2)
draw.text((90, 205), "ADVERSARY / HIGH-RISK INGRESS NODES", fill="#FF3B5C", font=f_box_title, anchor="lm")

adv_nodes = [
    ("MOSCOW (BULLETPROOF HOST)", "92.118.160.5 • Destructive DDL / Injections"),
    ("FRANKFURT (TOR EXIT RELAY)", "185.220.101.5 • Session Hijacking & Replay"),
    ("BUCHAREST & LAGOS BOTNET", "Distributed credential stuffing & headless bots"),
    ("RED-TEAM ATTACK HARNESS", "Locust Web Swarm • OWASP ZAP • Apache JMeter"),
]
for idx, (title, desc) in enumerate(adv_nodes):
    col = idx % 2
    row = idx // 2
    nx = 90 + col * 570
    ny = 225 + row * 45
    draw_card(nx, ny, nx + 550, ny + 40, bg="#24101D", border="#4D1525", radius=6, width=1)
    draw.text((nx + 15, ny + 12), title, fill="#FF6B8B", font=f_item_title, anchor="lm")
    draw.text((nx + 15, ny + 27), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Right: Sovereign Domestic & Global Partner Zones (x: 1350 to 2530)
draw_card(1350, 185, 2530, 330, bg="#081827", border="#00D4FF", radius=8, width=2)
draw.text((1370, 205), "SOVEREIGN DOMESTIC & TRUSTED FINANCIAL INGRESS NODES", fill="#00D4FF", font=f_box_title, anchor="lm")

clean_nodes = [
    ("MUMBAI CORE DEFENSE GATEWAY", "103.21.58.1 • Primary Financial Production Gateway"),
    ("NCR DELHI MOBILE USERS", "Domestic Retail Banking Customers & Web Traffic"),
    ("BENGALURU API CONSUMERS", "Fintech Partner APIs & Automated Banking SDK"),
    ("TOKYO & SINGAPORE HUBS", "Regional Cross-Border Clearing & SWIFT Partners"),
]
for idx, (title, desc) in enumerate(clean_nodes):
    col = idx % 2
    row = idx // 2
    nx = 1370 + col * 570
    ny = 225 + row * 45
    draw_card(nx, ny, nx + 550, ny + 40, bg="#0D2238", border="#154168", radius=6, width=1)
    draw.text((nx + 15, ny + 12), title, fill="#38BDF8", font=f_item_title, anchor="lm")
    draw.text((nx + 15, ny + 27), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# ─────────────────────────────────────────────────────────────────────────────
# 3. TIER II: PERIMETER EDGE & 7 HIERARCHICAL DEFENSE LAYERS
# ─────────────────────────────────────────────────────────────────────────────
draw_card(50, 415, W - 50, 690, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((80, 440), "TIER II: EDGE INGRESS & 7-LAYER HIERARCHICAL DEFENSE ARCHITECTURE", fill="#94A3B8", font=f_tier, anchor="lm")

# Edge Proxy Container (x: 70 to 860)
draw_card(70, 465, 860, 670, bg="#101827", border="#FFB800", radius=10, width=2)
draw.text((90, 490), "EDGE REVERSE PROXY & WAF (NGINX)", fill="#FFB800", font=f_box_title, anchor="lm")
draw.text((90, 512), "Container: 172.20.0.3:80 • Docker Subnet: 172.20.0.0/24", fill="#94A3B8", font=f_box_sub, anchor="lm")

edge_features = [
    "• Ingress Routing & SSL/TLS 1.3 Termination",
    "• Dynamic Blocklist Watcher (blocked_ips.conf)",
    "• Atomic Config Reload within 5 seconds",
    "• Sliding Leaky-Bucket Rate Limiting Zones",
    "• Layer 4/7 Direct Malicious Packet Drop",
]
for i, f in enumerate(edge_features):
    draw.text((95, 542 + i * 23), f, fill="#E2E8F0", font=f_item_title, anchor="lm")

# 7 Defense Layers Grid (x: 910 to 2530)
draw_card(910, 465, 2530, 670, bg="#071A1A", border="#00FF88", radius=10, width=2)
draw.text((930, 490), "THE 7 HIERARCHICAL DEFENSE LAYERS (SWIFT CSP / RBI / PCI-DSS 4.0 COMPLIANT)", fill="#00FF88", font=f_box_title, anchor="lm")

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
    lx = 930 + col * 790
    ly = 515 + row * 36
    draw_card(lx, ly, lx + 770, ly + 32, bg="#0C2522", border="#155543", radius=5, width=1)
    draw.text((lx + 10, ly + 10), ltitle, fill="#5EEAD4", font=f_item_title, anchor="lm")
    draw.text((lx + 10, ly + 22), ldesc, fill="#CBD5E1", font=f_item_desc, anchor="lm")

# ─────────────────────────────────────────────────────────────────────────────
# 4. TIER III: DIGITAL BANKING APPS & INTERCEPTION LAYER
# ─────────────────────────────────────────────────────────────────────────────
draw_card(50, 755, W - 50, 990, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((80, 780), "TIER III: DIGITAL BANKING PLATFORM & ZERO-BYPASS INTERCEPTION LAYER", fill="#94A3B8", font=f_tier, anchor="lm")

# NeoVault Flask Container (x: 70 to 1350)
draw_card(70, 805, 1350, 970, bg="#0B1A2E", border="#3B82F6", radius=10, width=2)
draw.text((90, 828), "NEOVAULT DIGITAL BANKING CORE (FLASK / PYTHON 3.11)", fill="#60A5FA", font=f_box_title, anchor="lm")
draw.text((90, 850), "Container: 172.20.0.2:5001 • Multi-Blueprint Architecture", fill="#94A3B8", font=f_box_sub, anchor="lm")

app_routes = [
    ("/api/auth/*", "JWT stateless session tokens, Bcrypt hash, PyOTP TOTP 2FA, Google OAuth 2.0"),
    ("/api/banking/*", "Checking/Savings accounts, ledger balances, beneficiary fund transfers, cards"),
    ("/api/admin/*", "Active session monitor, revocation endpoints, audit logs & telemetry"),
]
for i, (r_title, r_desc) in enumerate(app_routes):
    ry = 878 + i * 27
    draw.text((95, ry), r_title, fill="#93C5FD", font=f_item_title, anchor="lm")
    draw.text((230, ry), r_desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Middleware Interceptor (x: 1420 to 2530)
draw_card(1420, 805, 2530, 970, bg="#0D1E33", border="#00D4FF", radius=10, width=2)
draw.text((1440, 828), "SECURITY INTERCEPTOR & CLIENT TELEMETRY", fill="#00D4FF", font=f_box_title, anchor="lm")

middleware_points = [
    ("@app.before_request Hook", "Mandatory zero-bypass inspection hook protecting every endpoint"),
    ("Behavioral Collector (JS)", "Captures typing flight/dwell times, mouse velocity & canvas entropy"),
    ("Synchronous Evaluation", "Hands request context & telemetry to TokenShield Engine (:7777)"),
    ("Instant Revocation Check", "Queries Redis O(1) cache for session & IP status prior to execution"),
]
for i, (m_title, m_desc) in enumerate(middleware_points):
    my = 856 + i * 25
    draw.text((1445, my), m_title, fill="#38BDF8", font=f_item_title, anchor="lm")
    draw.text((1690, my), m_desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# ─────────────────────────────────────────────────────────────────────────────
# 5. TIER IV: TOKENSHIELD AI SECURITY ENGINE (PORT 7777)
# ─────────────────────────────────────────────────────────────────────────────
draw_card(50, 1055, W - 50, 1370, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((80, 1080), "TIER IV: TOKENSHIELD AI-POWERED THREAT DEFENSE ENGINE (STANDALONE MICROSERVICE :7777)", fill="#94A3B8", font=f_tier, anchor="lm")

# 8 Signals (x: 70 to 1250)
draw_card(70, 1105, 1250, 1350, bg="#150B24", border="#A855F7", radius=10, width=2)
draw.text((90, 1128), "8-SIGNAL REAL-TIME THREAT ANALYSIS MATRIX", fill="#C084FC", font=f_box_title, anchor="lm")

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
    sx = 90 + col * 570
    sy = 1152 + row * 46
    draw_card(sx, sy, sx + 550, sy + 40, bg="#221138", border="#492473", radius=6, width=1)
    draw.text((sx + 10, sy + 13), stitle, fill="#E9D5FF", font=f_item_title, anchor="lm")
    draw.text((sx + 10, sy + 28), sdesc, fill="#CBD5E1", font=f_item_desc, anchor="lm")

# 3 ML Models & Scorer (x: 1300 to 2530)
draw_card(1300, 1105, 2530, 1350, bg="#150B24", border="#C084FC", radius=10, width=2)
draw.text((1320, 1128), "3-TIER MACHINE LEARNING CORE & RISK CLASSIFICATION", fill="#C084FC", font=f_box_title, anchor="lm")

ml_models = [
    ("MODEL A: ISOLATION FOREST", "300 Trees • 9 Features • Latency: 2.47ms • Unsupervised Zero-Day Outlier Detector"),
    ("MODEL B: SEQUENCE LSTM AUTOENCODER", "PyTorch MPS/CPU • 10-Step Sliding Buffer • NASA Sequences • Catches Workflow Jumps"),
    ("MODEL C: CALIBRATED META-CLASSIFIER", "HistGradientBoosting + Platt Sigmoid • ROC-AUC: 0.8943 • Precision: 98.18%"),
    ("COMPOSITE THREAT SCORER", "S = min(Sum(s_i), 1.0) • CRITICAL THRESHOLD: S >= 0.85 Triggers Immediate Mitigation"),
]
for idx, (mtitle, mdesc) in enumerate(ml_models):
    my = 1152 + idx * 46
    draw_card(1320, my, 2510, my + 40, bg="#221138", border="#492473", radius=6, width=1)
    draw.text((1335, my + 13), mtitle, fill="#E9D5FF", font=f_item_title, anchor="lm")
    draw.text((1335, my + 28), mdesc, fill="#CBD5E1", font=f_item_desc, anchor="lm")

# ─────────────────────────────────────────────────────────────────────────────
# 6. TIERS V, VI, VII: PERSISTENCE, MITIGATION & SECOPS WAR ROOM
# ─────────────────────────────────────────────────────────────────────────────
draw_card(50, 1445, W - 50, 1990, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw.text((80, 1470), "TIERS V, VI & VII: STATE PERSISTENCE, SUB-100MS MITIGATION & SECOPS WAR ROOM", fill="#94A3B8", font=f_tier, anchor="lm")

# Tier V: High-Speed State & Persistence (x: 70 to 800)
draw_card(70, 1495, 800, 1970, bg="#130D24", border="#9333EA", radius=10, width=2)
draw.text((90, 1520), "TIER V: HIGH-SPEED STATE & PERSISTENCE", fill="#C084FC", font=f_box_title, anchor="lm")

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
    dy = 1555 + i * 44
    if is_hdr:
        draw_card(85, dy - 12, 785, dy + 18, bg="#201538", border="#6B21A8", radius=4, width=1)
        draw.text((95, dy + 2), d_title, fill="#E9D5FF", font=f_item_title, anchor="lm")
        draw.text((430, dy + 2), d_desc, fill="#C084FC", font=f_item_desc, anchor="lm")
    else:
        draw.text((95, dy), d_title, fill="#D8B4FE", font=f_item_title, anchor="lm")
        draw.text((320, dy), d_desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Tier VI: 8-Step Mitigation Orchestrator (x: 840 to 1750)
draw_card(840, 1495, 1750, 1970, bg="#1E0B14", border="#EF4444", radius=10, width=2)
draw.text((860, 1520), "TIER VI: 8-STEP PROGRESSIVE MITIGATION (S >= 0.85)", fill="#EF4444", font=f_box_title, anchor="lm")

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
    my = 1555 + i * 50
    draw_card(855, my - 16, 1735, my + 24, bg="#2D0F1C", border="#5E1D2D", radius=5, width=1)
    draw.text((870, my + 2), m_name, fill="#FCA5A5", font=f_item_title, anchor="lm")
    draw_pill(1240, my - 8, 70, 22, m_lat, bg="#4A0B1A", border="#EF4444", text_color="#FECDD3")
    draw.text((1330, my + 2), m_action, fill="#E2E8F0", font=f_item_desc, anchor="lm")

# Tier VII: War Room & Cyber Command Center (x: 1790 to 2530)
draw_card(1790, 1495, 2530, 1970, bg="#07191A", border="#14B8A6", radius=10, width=2)
draw.text((1810, 1520), "TIER VII: CYBER COMMAND CENTER (:7777)", fill="#2DD4BF", font=f_box_title, anchor="lm")

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
    sy = 1560 + i * 56
    draw_card(1810, sy - 16, 2510, sy + 28, bg="#0D2728", border="#144F4B", radius=6, width=1)
    draw.text((1825, sy - 2), s_title, fill="#5EEAD4", font=f_item_title, anchor="lm")
    draw.text((1825, sy + 13), s_desc, fill="#CCFBF1", font=f_item_desc, anchor="lm")


# ─────────────────────────────────────────────────────────────────────────────
# 7. HIGH-VISIBILITY CONNECTING ARROWS & PIPELINE CONDUITS
# ─────────────────────────────────────────────────────────────────────────────

# PATH 1: Adversary Ingress -> Nginx WAF (Red)
draw_flow_arrow(
    [(660, 330), (660, 375), (320, 375), (320, 465)],
    color="#FF3B5C", width=4,
    label="MALICIOUS EXPLOITS / STOLEN JWTs / BOT FLOOD",
    label_pos=(490, 375), label_color="#FF6B8B"
)

# PATH 2: Sovereign Clean Ingress -> Nginx WAF (Cyan)
draw_flow_arrow(
    [(1950, 330), (1950, 375), (600, 375), (600, 465)],
    color="#00D4FF", width=4,
    label="CLEAN BANKING TRAFFIC / TLS 1.3 HTTPS",
    label_pos=(1275, 375), label_color="#38BDF8"
)

# PATH 3: Nginx -> NeoVault Banking App Core (Green)
draw_flow_arrow(
    [(460, 670), (460, 805)],
    color="#00FF88", width=4,
    label="proxy_pass (FILTERED EDGE TRAFFIC)",
    label_pos=(460, 735), label_color="#00FF88"
)

# PATH 4: NeoVault App -> Security Interceptor (Cyan)
draw_flow_arrow(
    [(1350, 885), (1420, 885)],
    color="#00D4FF", width=4,
    label="ZERO-BYPASS INSPECTION",
    label_pos=(1385, 855), label_color="#00D4FF"
)

# PATH 5: Interceptor -> TokenShield AI Security Engine (Purple)
draw_flow_arrow(
    [(1975, 970), (1975, 1015), (1915, 1015), (1915, 1105)],
    color="#C084FC", width=4,
    label="POST /api/v1/analyze (PAYLOAD + BIOMETRIC TELEMETRY)",
    label_pos=(1945, 1015), label_color="#E9D5FF"
)

# PATH 6: AI Engine -> 7 Defense Layers Health Update (Emerald)
draw_flow_arrow(
    [(1600, 1105), (1600, 1030), (1200, 1030), (1200, 670)],
    color="#5EEAD4", width=3,
    label="UPDATE DEFENSE LAYER HEALTH (L1 - L7)",
    label_pos=(1400, 1030), label_color="#5EEAD4"
)

# PATH 7: AI Engine -> 8-Step Mitigation Trigger (Red)
draw_flow_arrow(
    [(1300, 1350), (1300, 1495)],
    color="#EF4444", width=5,
    label="THREAT DETECTED (S >= 0.85) -> TRIGGER 8-STEP MITIGATION",
    label_pos=(1300, 1420), label_color="#FECDD3"
)

# PATH 8: Step 1 & 2 -> Redis Cache (Red/Purple)
draw_flow_arrow(
    [(855, 1580), (800, 1580)],
    color="#EF4444", width=4,
    label="M1: REVOKE JWT & M2: IP BAN",
    label_pos=(828, 1560), label_color="#FCA5A5"
)

# PATH 9: Step 3 -> Nginx Edge Reload (Orange Loop curving up left)
draw_flow_arrow(
    [(855, 1680), (40, 1680), (40, 565), (70, 565)],
    color="#FFB800", width=4,
    label="M3: WRITE blocked_ips.conf (EDGE RELOAD <= 5s)",
    label_pos=(40, 1125), label_color="#FDE68A"
)

# PATH 10: Step 5 -> SQLite DB Hard Lock (Red)
draw_flow_arrow(
    [(855, 1780), (800, 1780)],
    color="#EF4444", width=4,
    label="M5: LOCK ACCOUNT IN DB",
    label_pos=(828, 1760), label_color="#FCA5A5"
)

# PATH 11: Step 8 -> Cyber Command Center Live SSE Stream (Cyan)
draw_flow_arrow(
    [(1735, 1930), (1810, 1930)],
    color="#14B8A6", width=4,
    label="M8: PUSH LIVE INCIDENT SSE PACKET",
    label_pos=(1772, 1905), label_color="#5EEAD4"
)

# Save high-res PNG image
img.save(out_file, "PNG", dpi=(300, 300))
print(f"Master Architecture Diagram generated successfully at: {out_file}")
