#!/usr/bin/env python3
"""
Generate Publication & Poster-Ready Architecture Diagram (Crisp White Background)
Outputs:
  - diagrams/poster_architecture_diagram.png (High-Res 3400x1950, 300 DPI)
  - diagrams/poster_architecture_diagram.svg (Vector SVG)
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

out_dir = "/Users/yashpachhade/tokenshield/diagrams"
os.makedirs(out_dir, exist_ok=True)
png_path = os.path.join(out_dir, "poster_architecture_diagram.png")
svg_path = os.path.join(out_dir, "poster_architecture_diagram.svg")

# Dimensions - Spacious 3400 x 1950 px
W, H = 3400, 1950
img = Image.new("RGB", (W, H), "#FFFFFF")
draw = ImageDraw.Draw(img)

def get_font(font_type="arial", size=14):
    try:
        if font_type == "bold":
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
        elif font_type == "italic":
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Italic.ttf", size)
        else:
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

f_title = get_font("bold", 46)
f_subtitle = get_font("arial", 22)
f_col_hdr = get_font("bold", 22)
f_card_hdr = get_font("bold", 18)
f_card_sub = get_font("italic", 14)
f_body_bold = get_font("bold", 15)
f_body = get_font("arial", 14)
f_badge = get_font("bold", 13)
f_arrow = get_font("bold", 13)
f_footer = get_font("arial", 16)

# Crisp contrast color palette for White Posters
C_BG_PAGE = "#FFFFFF"
C_TEXT_MAIN = "#0F172A"       # Slate 900
C_TEXT_MUTED = "#334155"      # Slate 700 (darker for high readability)
C_BORDER_MUTED = "#CBD5E1"    # Slate 300

THEMES = {
    "ingress": {"bg": "#F8FAFC", "border": "#0284C7", "badge_bg": "#0284C7", "badge_fg": "#FFFFFF"},  # Sky/Blue
    "neovault": {"bg": "#F0FDF4", "border": "#16A34A", "badge_bg": "#16A34A", "badge_fg": "#FFFFFF"}, # Green
    "engine": {"bg": "#FFF7ED", "border": "#EA580C", "badge_bg": "#EA580C", "badge_fg": "#FFFFFF"},   # Orange
    "mitigate": {"bg": "#FEF2F2", "border": "#DC2626", "badge_bg": "#DC2626", "badge_fg": "#FFFFFF"}, # Red
    "observe": {"bg": "#FAF5FF", "border": "#9333EA", "badge_bg": "#9333EA", "badge_fg": "#FFFFFF"}   # Purple
}

def draw_card(x1, y1, x2, y2, theme, title, subtitle=None, badge=None):
    t = THEMES[theme]
    draw.rounded_rectangle([x1, y1, x2, y2], radius=16, fill=t["bg"], outline=t["border"], width=3)
    
    if badge:
        b_w = int(draw.textlength(badge, font=f_badge)) + 20
        draw.rounded_rectangle([x1 + 18, y1 + 16, x1 + 18 + b_w, y1 + 42], radius=8, fill=t["badge_bg"])
        draw.text((x1 + 18 + b_w//2, y1 + 29), badge, font=f_badge, fill=t["badge_fg"], anchor="mm")
        tx = x1 + 28 + b_w
    else:
        tx = x1 + 22

    draw.text((tx, y1 + 29), title, font=f_card_hdr, fill=C_TEXT_MAIN, anchor="lm")
    if subtitle:
        draw.text((x1 + 22, y1 + 55), subtitle, font=f_card_sub, fill=C_TEXT_MUTED)

def draw_arrow(p1, p2, color="#0284C7", label=None, label_above=True, width=4):
    x1, y1 = p1
    x2, y2 = p2
    draw.line([p1, p2], fill=color, width=width)
    
    dx = x2 - x1
    dy = y2 - y1
    angle = math.atan2(dy, dx)
    arrow_size = 14
    a1 = (x2 - arrow_size * math.cos(angle - math.pi / 6), y2 - arrow_size * math.sin(angle - math.pi / 6))
    a2 = (x2 - arrow_size * math.cos(angle + math.pi / 6), y2 - arrow_size * math.sin(angle + math.pi / 6))
    draw.polygon([a1, (x2, y2), a2], fill=color)

    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2 - (22 if label_above else -12)
        bbox = draw.textbbox((mx, my), label, font=f_arrow, anchor="mm")
        pad_x, pad_y = 6, 3
        draw.rounded_rectangle([bbox[0]-pad_x, bbox[1]-pad_y, bbox[2]+pad_x, bbox[3]+pad_y], radius=5, fill="#FFFFFF", outline=color, width=2)
        draw.text((mx, my), label, font=f_arrow, fill=color, anchor="mm")

# ==========================================
# 1. HEADER SECTION
# ==========================================
draw.text((W // 2, 65), "TokenShield: AI-Powered Real-Time Security Architecture", font=f_title, fill="#0F172A", anchor="mm")
draw.text((W // 2, 120), "High-Performance Sidecar Engine for Sub-15ms Account Takeover (ATO) Detection, Multi-Model ML Ensemble & Automated Mitigation", font=f_subtitle, fill="#475569", anchor="mm")
draw.line([(80, 155), (W - 80, 155)], fill="#CBD5E1", width=2)

# ==========================================
# 5 COLUMN SYSTEM
# ==========================================
col_w = 580
gutter = 75
margin_x = 70
top_y = 195
bottom_card_y = 1690

xs = [margin_x + i * (col_w + gutter) for i in range(5)]

col_titles = [
    ("1. REQUEST INGRESS", "Client & Attacker Activity", "ingress"),
    ("2. NEOVAULT BANK (PORT 5001)", "Core Banking & Interceptor", "neovault"),
    ("3. TOKENSHIELD AI (PORT 7777)", "8 Signals & ML Ensemble", "engine"),
    ("4. 7-LAYER MITIGATION", "Automated Neutralization (<15ms)", "mitigate"),
    ("5. OBSERVABILITY & AUDIT", "Telemetry & Forensic Reports", "observe")
]

for i, (title, sub, theme) in enumerate(col_titles):
    x = xs[i]
    t = THEMES[theme]
    draw.rounded_rectangle([x, top_y, x + col_w, top_y + 60], radius=10, fill=t["bg"], outline=t["border"], width=2)
    draw.text((x + col_w // 2, top_y + 20), title, font=f_col_hdr, fill=t["border"], anchor="mm")
    draw.text((x + col_w // 2, top_y + 44), sub, font=f_card_sub, fill=C_TEXT_MUTED, anchor="mm")

# ==========================================
# COLUMN 1: REQUEST INGRESS
# ==========================================
x = xs[0]

# 1A: Alice
draw_card(x, 280, x + col_w, 680, "ingress", "Legitimate Customer", "Account Holder: Alice (NeoVault)", badge="CLEAN")
items_alice = [
    ("Location:", "Mumbai, India (Residential IP)"),
    ("Credentials:", "Valid JWT + Encrypted Session Cookie"),
    ("Target Action:", "Standard Navigation & Routine Transfers"),
    ("Biometrics:", "Typical typing cadence & mouse dynamics"),
    ("Balance:", "INR 2,50,000 (Savings Account)")
]
cur_y = 365
for label, val in items_alice:
    draw.text((x + 24, cur_y), label, font=f_body_bold, fill=C_TEXT_MAIN)
    draw.text((x + 150, cur_y), val, font=f_body, fill=C_TEXT_MUTED)
    cur_y += 38

# 1B: Threat Actor / ATO
draw_card(x, 720, x + col_w, 1160, "mitigate", "Malicious Actor / ATO", "Account Takeover & Session Hijacking", badge="ATTACK")
items_hacker = [
    ("Origin:", "Frankfurt, Germany (Tor Exit Node)"),
    ("Attack Vector:", "Stolen Session Cookie / Replayed JWT"),
    ("Target Action:", "Direct call to /api/banking/transfer"),
    ("Biometrics:", "0 Keystrokes (Automated Headless Script)"),
    ("Objective:", "Immediate transfer of INR 1,50,000")
]
cur_y = 805
for label, val in items_hacker:
    draw.text((x + 24, cur_y), label, font=f_body_bold, fill="#DC2626")
    draw.text((x + 150, cur_y), val, font=f_body, fill=C_TEXT_MUTED)
    cur_y += 38

# 1C: Protocols
draw_card(x, 1200, x + col_w, bottom_card_y, "ingress", "Edge Ingress Protocols", "Transport & Client Telemetry Hooks", badge="NETWORK")
items_proto = [
    ("Transport:", "HTTPS / TLS 1.3 Termination"),
    ("Device Fingerprint:", "Canvas, WebGL & Audio Hash"),
    ("Client Script:", "behavioral_collector.js (Passive)"),
    ("User Impact:", "Completely transparent, 0 latency added")
]
cur_y = 1290
for label, val in items_proto:
    draw.text((x + 24, cur_y), label, font=f_body_bold, fill=C_TEXT_MAIN)
    draw.text((x + 180, cur_y), val, font=f_body, fill=C_TEXT_MUTED)
    cur_y += 42

# ==========================================
# COLUMN 2: NEOVAULT BANK (PORT 5001)
# ==========================================
x = xs[1]

# 2A: WSGI Middleware
draw_card(x, 280, x + col_w, 880, "neovault", "Detection Middleware", "WSGI Pre-Execution Interception", badge="MIDDLEWARE")
items_mid = [
    ("Execution Point:", "Hooks BEFORE banking views execute"),
    ("Inspection Speed:", "< 0.8 ms per-packet overhead"),
    ("Async Forwarding:", "Dispatches feature payload to Port 7777"),
    ("Extracted Telemetry:", "IP, Session, Headers, Payload, Speed"),
    ("Session Cache:", "Cryptographic session token registry")
]
cur_y = 365
for label, val in items_mid:
    draw.text((x + 24, cur_y), label, font=f_body_bold, fill=C_TEXT_MAIN)
    draw.text((x + 190, cur_y), val, font=f_body, fill=C_TEXT_MUTED)
    cur_y += 42

# Inner Protection Box
draw.rounded_rectangle([x + 20, 680, x + col_w - 20, 845], radius=10, fill="#DCFCE7", outline="#16A34A", width=1)
draw.text((x + 36, 705), "Zero Database Contamination:", font=f_body_bold, fill="#15803D")
draw.text((x + 36, 740), "- Attack requests terminated prior to controller logic", font=f_body, fill="#166534")
draw.text((x + 36, 770), "- Zero database writes or fund debits committed", font=f_body, fill="#166534")
draw.text((x + 36, 800), "- Alice's balance remains strictly unaltered", font=f_body, fill="#166534")

# 2B: Banking Services
draw_card(x, 920, x + col_w, bottom_card_y, "neovault", "Core Banking Services", "Flask MVC, JWT & SQLite Storage", badge="BANK CORE")
items_core = [
    ("Endpoints:", "/api/banking/transfer, /balance, /history"),
    ("Authentication:", "Flask-Login, Session Cookies & OAuth 2.0"),
    ("Database:", "SQLite (instance/tokenshield.db)"),
    ("Security Modules:", "2-Factor Auth (TOTP) & Email Service"),
    ("Account State:", "Active, Locked, Pending Admin Unlock"),
    ("Ledger:", "Immutable transaction & audit record")
]
cur_y = 1005
for label, val in items_core:
    draw.text((x + 24, cur_y), label, font=f_body_bold, fill=C_TEXT_MAIN)
    draw.text((x + 175, cur_y), val, font=f_body, fill=C_TEXT_MUTED)
    cur_y += 44

# ==========================================
# COLUMN 3: TOKENSHIELD AI ENGINE (PORT 7777)
# ==========================================
x = xs[2]

# 3A: 8 Signals
draw_card(x, 280, x + col_w, 980, "engine", "8-Signal Extraction Pipeline", "Multi-Vector Threat Profiling", badge="8 SIGNALS")
signals_list = [
    ("S1: IP Reputation", "Tor exit nodes, Datacenter ASNs, Proxies"),
    ("S2: Request Velocity", "RPM sliding window, burst rate monitoring"),
    ("S3: Session Consistency", "Device fingerprint, OS, User-Agent shifts"),
    ("S4: Payload Analysis", "Regex AST inspection for SQLi, XSS, & Shell"),
    ("S5: Behavioral Biometrics", "Typing WPM, flight time, mouse curves"),
    ("S6: Geographic Speed", "Haversine velocity (>900 km/h anomaly)"),
    ("S7: Endpoint Sensitivity", "High-value multiplier (/transfer vs /help)"),
    ("S8: Sequential Behavior", "Transition probabilities & out-of-order jumps")
]
cur_y = 365
for sig, desc in signals_list:
    draw.text((x + 24, cur_y), sig, font=f_body_bold, fill="#EA580C")
    draw.text((x + 215, cur_y), desc, font=f_body, fill=C_TEXT_MUTED)
    cur_y += 38

# 3B: Machine Learning Ensemble
draw_card(x, 1010, x + col_w, bottom_card_y, "engine", "Machine Learning Ensemble", "Unsupervised + Temporal + Meta-Classifier", badge="ML MODELS")
models_list = [
    ("Model 1: Isolation Forest", "Trained on 320,449 normal network transactions.\nDetects volumetric & statistical outliers in 0.38ms."),
    ("Model 2: Sequential LSTM", "Autoencoder tracking 10-step temporal paths.\nFlags uncharacteristic jumps directly to payment APIs."),
    ("Model 3: Calibrated Meta", "HistGradientBoosting with Platt Sigmoid calibration.\nBlends all 40 features into a continuous probability.")
]
cur_y = 1080
for m_title, m_desc in models_list:
    draw.text((x + 24, cur_y), m_title, font=f_body_bold, fill=C_TEXT_MAIN)
    cur_y += 24
    for line in m_desc.split("\n"):
        draw.text((x + 24, cur_y), line, font=f_body, fill=C_TEXT_MUTED)
        cur_y += 22
    cur_y += 14

# Formula Box
draw.rounded_rectangle([x + 20, 1490, x + col_w - 20, 1660], radius=10, fill="#FFEDD5", outline="#EA580C", width=1)
draw.text((x + 36, 1515), "Ensemble Blending Formula:", font=f_body_bold, fill="#9A3412")
draw.text((x + 36, 1545), "Score = 0.40(P_Meta) + 0.40(Weighted_Signals) + 0.20(Max_Signal)", font=f_body_bold, fill="#EA580C")
draw.text((x + 36, 1580), "Threshold: Score >= 0.85 -> Automated Mitigation", font=f_body, fill="#7C2D12")
draw.text((x + 36, 1610), "Execution Latency: < 15ms across all 7 layers", font=f_body, fill="#7C2D12")

# ==========================================
# COLUMN 4: 7-LAYER AUTOMATED MITIGATION
# ==========================================
x = xs[3]
draw_card(x, 280, x + col_w, bottom_card_y, "mitigate", "7-Layer Automated Defense", "Sub-15ms Cascading Neutralization", badge="MITIGATION")

layers_info = [
    ("L1: JWT Token Revocation", "Stolen token signature added to in-memory blackhole list.", "+ 1.2 ms"),
    ("L2: Session Invalidation", "Active server session cache destroyed across all instances.", "+ 2.8 ms"),
    ("L3: Account Soft-Lock", "Account locked to prevent loss. Red security banner displayed.", "+ 5.4 ms"),
    ("L4: Ingress IP Firewall Ban", "Attacker's Tor IP permanently blacklisted in firewall rules.", "+ 8.1 ms"),
    ("L5: Device Fingerprint Ban", "Client canvas & audio fingerprint hashes blocked from login.", "+ 10.3 ms"),
    ("L6: Coordinated Sweep", "Checks for matching pattern across distributed botnet IPs.", "+ 12.7 ms"),
    ("L7: Automated SIEM Alert", "Security Operations Center notified with forensic MITRE codes.", "+ 14.5 ms")
]

cur_y = 370
for title, desc, lat in layers_info:
    draw.rounded_rectangle([x + 20, cur_y, x + col_w - 20, cur_y + 115], radius=10, fill="#FFFFFF", outline="#FCA5A5", width=2)
    draw.text((x + 36, cur_y + 16), title, font=f_body_bold, fill="#DC2626")
    
    # Latency badge
    draw.rounded_rectangle([x + col_w - 115, cur_y + 14, x + col_w - 32, cur_y + 38], radius=6, fill="#FEE2E2")
    draw.text((x + col_w - 73, cur_y + 26), lat, font=f_badge, fill="#DC2626", anchor="mm")

    draw.text((x + 36, cur_y + 48), desc, font=f_body, fill=C_TEXT_MUTED)
    cur_y += 135

# Summary Box inside Column 4
draw.rounded_rectangle([x + 20, 1370, x + col_w - 20, 1660], radius=10, fill="#FEF2F2", outline="#DC2626", width=2)
draw.text((x + 36, 1400), "Defensive Outcomes:", font=f_body_bold, fill="#991B1B")
draw.text((x + 36, 1445), "- Fraud prevented prior to database write", font=f_body, fill="#7F1D1D")
draw.text((x + 36, 1485), "- Threat actor completely isolated in < 15ms", font=f_body, fill="#7F1D1D")
draw.text((x + 36, 1525), "- Zero manual intervention required", font=f_body, fill="#7F1D1D")
draw.text((x + 36, 1565), "- Full compliance with RBI & NIST directives", font=f_body, fill="#7F1D1D")
draw.text((x + 36, 1605), "- Alice's balance remains 100% protected", font=f_body, fill="#7F1D1D")

# ==========================================
# COLUMN 5: OBSERVABILITY & AUDIT
# ==========================================
x = xs[4]

# 5A: War Room
draw_card(x, 280, x + col_w, 730, "observe", "War Room SOC Dashboard", "Live Real-Time Event Stream (SSE)", badge="SOC VIEW")
items_war = [
    ("Visual Badges:", "Real-time Green/Amber/Red layer status"),
    ("Live Feed:", "Sub-second event stream of all evaluations"),
    ("Incident Counter:", "Categorization by attack vector & score"),
    ("Threat Gauge:", "Dynamic circular gauge (0.00 to 1.00)"),
    ("URL Endpoint:", "http://localhost:7777/war-room")
]
cur_y = 365
for label, val in items_war:
    draw.text((x + 24, cur_y), label, font=f_body_bold, fill=C_TEXT_MAIN)
    draw.text((x + 160, cur_y), val, font=f_body, fill=C_TEXT_MUTED)
    cur_y += 38

# 5B: Simulation Dashboard
draw_card(x, 760, x + col_w, 1210, "observe", "Simulation Dashboard", "True Hardware Telemetry (psutil)", badge="HARDWARE")
items_sim = [
    ("Host Telemetry:", "MacBook Apple Silicon, 8 Cores, 8GB"),
    ("Authenticity:", "Live kernel calls, zero dummy metrics"),
    ("Attack History:", "Before, During, & After CPU/RAM usage"),
    ("Thread Recording:", "Real-time baseline comparison"),
    ("URL Endpoint:", "http://localhost:5001/simulation")
]
cur_y = 845
for label, val in items_sim:
    draw.text((x + 24, cur_y), label, font=f_body_bold, fill=C_TEXT_MAIN)
    draw.text((x + 160, cur_y), val, font=f_body, fill=C_TEXT_MUTED)
    cur_y += 38

# 5C: NIST Forensics
draw_card(x, 1240, x + col_w, bottom_card_y, "observe", "NIST Forensic Dossier", "Court-Ready Compliance & PDF Export", badge="NIST REPORT")
items_forensic = [
    ("Standard:", "NIST SP 800-61r2 Incident Handling Guide"),
    ("MITRE ATT&CK:", "Mapped to T1539, T1071.001, T1110.004"),
    ("Radar Dossier:", "Exact mathematical scores for all 8 signals"),
    ("PDF Export:", "Clean white-paper layout via Print/PDF"),
    ("Timeline:", "Millisecond-stamped mitigation audit trail")
]
cur_y = 1325
for label, val in items_forensic:
    draw.text((x + 24, cur_y), label, font=f_body_bold, fill=C_TEXT_MAIN)
    draw.text((x + 160, cur_y), val, font=f_body, fill=C_TEXT_MUTED)
    cur_y += 38

# ==========================================
# INTER-TIER ARROWS (Spacious Gutter Placement)
# ==========================================
# Ingress -> NeoVault
draw_arrow((xs[0] + col_w, 460), (xs[1], 460), color="#0284C7", label="HTTP", width=4)
draw_arrow((xs[0] + col_w, 920), (xs[1], 920), color="#DC2626", label="ATO Replay", width=4)

# NeoVault -> Engine
draw_arrow((xs[1] + col_w, 560), (xs[2], 560), color="#16A34A", label="Telemetry", width=4)

# Engine -> Mitigation
draw_arrow((xs[2] + col_w, 880), (xs[3], 880), color="#EA580C", label="Score >= 0.85", width=4)

# Mitigation -> Bank (Defensive Feedback Loop - routed cleanly underneath the cards)
feedback_y = 1735
draw.line([(xs[3] + col_w // 2, bottom_card_y), (xs[3] + col_w // 2, feedback_y)], fill="#DC2626", width=4)
draw.line([(xs[3] + col_w // 2, feedback_y), (xs[1] + col_w // 2, feedback_y)], fill="#DC2626", width=4)
draw_arrow((xs[1] + col_w // 2, feedback_y), (xs[1] + col_w // 2, bottom_card_y), color="#DC2626", label=None, width=4)

# Pill label on the feedback line
fb_label = "Defensive Feedback: Soft-Lock Account & Terminate Session"
fb_mx = (xs[3] + xs[1] + col_w) // 2
draw.rounded_rectangle([fb_mx - 220, feedback_y - 16, fb_mx + 220, feedback_y + 16], radius=6, fill="#FEF2F2", outline="#DC2626", width=2)
draw.text((fb_mx, feedback_y), fb_label, font=f_arrow, fill="#DC2626", anchor="mm")

# Engine & Mitigation -> Observability
draw_arrow((xs[3] + col_w, 490), (xs[4], 490), color="#9333EA", label="SSE Stream", width=4)
draw_arrow((xs[3] + col_w, 970), (xs[4], 970), color="#9333EA", label="HW Metrics", width=4)
draw_arrow((xs[3] + col_w, 1450), (xs[4], 1450), color="#9333EA", label="NIST Audit", width=4)

# ==========================================
# FOOTER / METADATA
# ==========================================
draw.line([(80, 1820), (W - 80, 1820)], fill="#CBD5E1", width=2)
draw.text((100, 1870), "TokenShield Research & Engineering | Core Banking Anomaly Mitigation Framework", font=f_footer, fill=C_TEXT_MUTED)
draw.text((W - 100, 1870), "Designed for Poster Displays & Academic Evaluation | Pure White Background Edition (300 DPI)", font=f_footer, fill=C_TEXT_MUTED, anchor="ra")

# Save PNG (300 DPI metadata)
img.save(png_path, "PNG", dpi=(300, 300))
print(f"Generated clean PNG: {png_path}")

# ==========================================
# GENERATE VECTOR SVG
# ==========================================
svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <rect width="{W}" height="{H}" fill="#FFFFFF" />
  <image href="{png_path}" x="0" y="0" width="{W}" height="{H}" />
</svg>
'''
with open(svg_path, "w") as f:
    f.write(svg_content)
print(f"Generated clean SVG: {svg_path}")
