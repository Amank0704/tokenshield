#!/usr/bin/env python3
"""
Generate Simple, Clean, End-to-End Architecture Diagram (Light Background)
Minimalist, high-readability design for posters and presentations.
Zero glyph issues (pure standard fonts), zero crossing lines.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

out_dir = "/Users/yashpachhade/tokenshield/diagrams"
os.makedirs(out_dir, exist_ok=True)
png_path = os.path.join(out_dir, "simple_architecture_diagram.png")
brain_path = "/Users/yashpachhade/.gemini/antigravity/brain/9fb84148-ca25-4e5b-8d9e-09484d3c09e5/simple_architecture_diagram.png"

# Canvas dimensions: 2600 x 1350 px
W, H = 2600, 1350
img = Image.new("RGB", (W, H), "#FFFFFF")
draw = ImageDraw.Draw(img)

def get_font(font_type="arial", size=16):
    try:
        if font_type == "bold":
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
        elif font_type == "italic":
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Italic.ttf", size)
        else:
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

f_title = get_font("bold", 42)
f_subtitle = get_font("arial", 20)
f_stage_num = get_font("bold", 15)
f_stage_title = get_font("bold", 22)
f_box_hdr = get_font("bold", 19)
f_box_body = get_font("arial", 16)
f_box_bold = get_font("bold", 16)
f_arrow = get_font("bold", 14)

C_TEXT_MAIN = "#0F172A"       # Deep slate
C_TEXT_MUTED = "#334155"      # Mid slate
C_BORDER = "#CBD5E1"

def draw_pill(x, y, text, bg, fg, font=f_stage_num):
    w = int(draw.textlength(text, font=font)) + 24
    h = 32
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h//2, fill=bg)
    draw.text((x + w//2, y + h//2), text, font=font, fill=fg, anchor="mm")
    return w

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
        my = (y1 + y2) / 2 - (20 if label_above else -14)
        bbox = draw.textbbox((mx, my), label, font=f_arrow, anchor="mm")
        pad_x, pad_y = 8, 4
        draw.rounded_rectangle([bbox[0]-pad_x, bbox[1]-pad_y, bbox[2]+pad_x, bbox[3]+pad_y], radius=6, fill="#FFFFFF", outline=color, width=2)
        draw.text((mx, my), label, font=f_arrow, fill=color, anchor="mm")

# ==========================================
# HEADER
# ==========================================
draw.text((W // 2, 60), "TokenShield: End-to-End System Architecture", font=f_title, fill=C_TEXT_MAIN, anchor="mm")
draw.text((W // 2, 110), "AI-Powered Real-Time Threat Detection & Mitigation for Core Banking", font=f_subtitle, fill=C_TEXT_MUTED, anchor="mm")
draw.line([(80, 150), (W - 80, 150)], fill=C_BORDER, width=2)

# ==========================================
# 4 MAIN STAGES (HORIZONTAL PIPELINE)
# ==========================================
# STAGE 1: INGRESS CLIENTS (X: 100 to 520)
x1, w1 = 100, 430
draw_pill(x1, 190, "STAGE 1", "#E0F2FE", "#0284C7")
draw.text((x1 + 105, 206), "Incoming Traffic", font=f_stage_title, fill=C_TEXT_MAIN, anchor="lm")

# Card 1A: Alice
draw.rounded_rectangle([x1, 260, x1 + w1, 560], radius=16, fill="#F8FAFC", outline="#0284C7", width=3)
draw.rounded_rectangle([x1 + 20, 280, x1 + 150, 314], radius=6, fill="#0284C7")
draw.text((x1 + 85, 297), "LEGITIMATE", font=f_stage_num, fill="#FFFFFF", anchor="mm")
draw.text((x1 + 165, 297), "User (Alice)", font=f_box_hdr, fill=C_TEXT_MAIN, anchor="lm")

alice_bullets = [
    "- Genuine Customer in Mumbai",
    "- Valid JWT & Session Token",
    "- Normal Typing & Mouse Patterns",
    "- Regular Balance Check / Transfer"
]
by = 350
for b in alice_bullets:
    draw.text((x1 + 24, by), b, font=f_box_body, fill=C_TEXT_MUTED)
    by += 44

# Card 1B: Attacker
draw.rounded_rectangle([x1, 620, x1 + w1, 920], radius=16, fill="#FEF2F2", outline="#DC2626", width=3)
draw.rounded_rectangle([x1 + 20, 640, x1 + 130, 674], radius=6, fill="#DC2626")
draw.text((x1 + 75, 657), "ATTACKER", font=f_stage_num, fill="#FFFFFF", anchor="mm")
draw.text((x1 + 145, 657), "Account Takeover", font=f_box_hdr, fill="#DC2626", anchor="lm")

hacker_bullets = [
    "- Adversary on Tor / Proxy IP",
    "- Replaying Stolen Session Token",
    "- Zero Biometrics (Headless Bot)",
    "- Direct Jump to High-Value Transfer"
]
by = 710
for b in hacker_bullets:
    draw.text((x1 + 24, by), b, font=f_box_body, fill=C_TEXT_MUTED)
    by += 44

# ------------------------------------------
# STAGE 2: NEOVAULT BANK (X: 630 to 1130)
# ------------------------------------------
x2, w2 = 630, 500
draw_pill(x2, 190, "STAGE 2", "#DCFCE7", "#16A34A")
draw.text((x2 + 105, 206), "NeoVault Banking (:5001)", font=f_stage_title, fill=C_TEXT_MAIN, anchor="lm")

draw.rounded_rectangle([x2, 260, x2 + w2, 920], radius=16, fill="#F0FDF4", outline="#16A34A", width=3)

# Inner Box 2A: WSGI Middleware
draw.rounded_rectangle([x2 + 20, 280, x2 + w2 - 20, 560], radius=12, fill="#FFFFFF", outline="#86EFAC", width=2)
draw.text((x2 + 40, 315), "WSGI Detection Middleware", font=f_box_hdr, fill="#15803D")
draw.text((x2 + 40, 350), "Interception Layer (<0.8ms overhead)", font=f_box_body, fill=C_TEXT_MUTED)

mid_bullets = [
    "[+] Intercepts requests before DB commit",
    "[+] Extracts IP, headers, payload, biometrics",
    "[+] Forwards live telemetry to AI Engine",
    "[+] Blocks malicious requests instantly"
]
by = 395
for b in mid_bullets:
    draw.text((x2 + 40, by), b, font=f_box_body, fill="#166534")
    by += 36

# Inner Box 2B: Core Banking & SQLite DB
draw.rounded_rectangle([x2 + 20, 600, x2 + w2 - 20, 880], radius=12, fill="#FFFFFF", outline="#86EFAC", width=2)
draw.text((x2 + 40, 635), "Core Banking Controllers & DB", font=f_box_hdr, fill="#15803D")
draw.text((x2 + 40, 670), "Flask Web App & SQLite Database", font=f_box_body, fill=C_TEXT_MUTED)

db_bullets = [
    "- /api/banking/transfer & /balance",
    "- Alice's Balance: INR 2,50,000",
    "- Protected from fraudulent debits",
    "- Session & Authentication Manager"
]
by = 715
for b in db_bullets:
    draw.text((x2 + 40, by), b, font=f_box_body, fill=C_TEXT_MUTED)
    by += 36

# ------------------------------------------
# STAGE 3: TOKENSHIELD AI ENGINE (X: 1240 to 1820)
# ------------------------------------------
x3, w3 = 1240, 580
draw_pill(x3, 190, "STAGE 3", "#FFEDD5", "#EA580C")
draw.text((x3 + 105, 206), "TokenShield AI Engine (:7777)", font=f_stage_title, fill=C_TEXT_MAIN, anchor="lm")

draw.rounded_rectangle([x3, 260, x3 + w3, 920], radius=16, fill="#FFF7ED", outline="#EA580C", width=3)

# Inner Box 3A: 8 Security Signals
draw.rounded_rectangle([x3 + 20, 280, x3 + w3 - 20, 520], radius=12, fill="#FFFFFF", outline="#FDBA74", width=2)
draw.text((x3 + 40, 310), "8 Real-Time Security Signals", font=f_box_hdr, fill="#C2410C")

col1_sigs = ["S1. IP Reputation (Tor)", "S2. Request Velocity", "S3. Session Consistency", "S4. Payload (SQLi/XSS)"]
col2_sigs = ["S5. Behavioral Biometrics", "S6. Impossible Travel", "S7. Endpoint Risk", "S8. Sequential Behavior"]

sy = 350
for s1, s2 in zip(col1_sigs, col2_sigs):
    draw.text((x3 + 40, sy), s1, font=f_box_body, fill=C_TEXT_MUTED)
    draw.text((x3 + 300, sy), s2, font=f_box_body, fill=C_TEXT_MUTED)
    sy += 36

# Inner Box 3B: 3 ML Models
draw.rounded_rectangle([x3 + 20, 550, x3 + w3 - 20, 770], radius=12, fill="#FFFFFF", outline="#FDBA74", width=2)
draw.text((x3 + 40, 580), "3-Model Machine Learning Ensemble", font=f_box_hdr, fill="#C2410C")

ml_bullets = [
    "1. Isolation Forest (320k normal traffic baseline)",
    "2. Sequential LSTM (Temporal navigation anomaly)",
    "3. Calibrated Meta-Classifier (LightGBM 40-dim fusion)"
]
my = 620
for m in ml_bullets:
    draw.text((x3 + 40, my), m, font=f_box_body, fill=C_TEXT_MUTED)
    my += 44

# Inner Box 3C: Threat Score Badge
draw.rounded_rectangle([x3 + 20, 800, x3 + w3 - 20, 890], radius=10, fill="#FFEDD5", outline="#EA580C", width=2)
draw.text((x3 + w3 // 2, 845), "Composite Risk Score (0.00 to 1.00)  |  Threshold: 0.85", font=f_box_bold, fill="#9A3412", anchor="mm")

# ------------------------------------------
# STAGE 4: DECISION & OUTCOMES (X: 1930 to 2500)
# ------------------------------------------
x4, w4 = 1930, 570
draw_pill(x4, 190, "STAGE 4", "#F3E8FF", "#7E22CE")
draw.text((x4 + 105, 206), "Outcomes & Response", font=f_stage_title, fill=C_TEXT_MAIN, anchor="lm")

# Branch A: Normal (< 0.85) -> ALLOWED
draw.rounded_rectangle([x4, 260, x4 + w4, 540], radius=16, fill="#F0FDF4", outline="#16A34A", width=3)
draw.rounded_rectangle([x4 + 20, 280, x4 + 180, 314], radius=6, fill="#16A34A")
draw.text((x4 + 100, 297), "SCORE < 0.85", font=f_stage_num, fill="#FFFFFF", anchor="mm")
draw.text((x4 + 195, 297), "Transaction Allowed", font=f_box_hdr, fill="#15803D", anchor="lm")

safe_bullets = [
    "[PASS] Low risk assessment (Score ~0.00)",
    "[PASS] Banking controller executes normally",
    "[PASS] Alice's balance transfers securely",
    "[PASS] Clean user experience (0 friction)"
]
sy = 350
for b in safe_bullets:
    draw.text((x4 + 24, sy), b, font=f_box_body, fill="#166534")
    sy += 40

# Branch B: Threat (>= 0.85) -> 7-LAYER MITIGATION (<15ms)
draw.rounded_rectangle([x4, 580, x4 + w4, 920], radius=16, fill="#FEF2F2", outline="#DC2626", width=3)
draw.rounded_rectangle([x4 + 20, 600, x4 + 180, 634], radius=6, fill="#DC2626")
draw.text((x4 + 100, 617), "SCORE >= 0.85", font=f_stage_num, fill="#FFFFFF", anchor="mm")
draw.text((x4 + 195, 617), "Automated Mitigation (<15ms)", font=f_box_hdr, fill="#B91C1C", anchor="lm")

mit_bullets = [
    "- L1: Revoke stolen JWT token immediately",
    "- L2: Terminate active server-side session",
    "- L3: Account Soft-Lock (Alice sees Red Banner)",
    "- L4: Blacklist attacker's Tor IP on Firewall",
    "- L5-L7: Fingerprint ban, botnet sweep, SIEM alert",
    "[RESULT] INR 2,50,000 preserved (INR 0 lost)"
]
my = 665
for b in mit_bullets:
    draw.text((x4 + 24, my), b, font=f_box_body, fill="#7F1D1D")
    my += 38

# ==========================================
# STAGE 5: BOTTOM OBSERVABILITY BAR (X: 100 to 2500)
# ==========================================
draw.rounded_rectangle([100, 970, 2500, 1220], radius=16, fill="#FAF5FF", outline="#9333EA", width=2)
draw_pill(120, 990, "OBSERVABILITY", "#F3E8FF", "#7E22CE")
draw.text((275, 1006), "Live Monitoring & Forensic Audit Infrastructure", font=f_box_hdr, fill="#6B21A8", anchor="lm")

obs_items = [
    ("War Room Dashboard (:7777):", "Live SSE real-time feed, 7 defense layer status badges, instant threat score gauge."),
    ("Simulation Dashboard (:5001):", "Live MacBook kernel telemetry (psutil). Before, During & After CPU/RAM usage tracking."),
    ("NIST SP 800-61r2 Dossier:", "Court-ready incident report with MITRE ATT&CK technique mappings and Print-to-PDF.")
]

oy = 1055
for title, desc in obs_items:
    draw.text((140, oy), title, font=f_box_bold, fill=C_TEXT_MAIN)
    draw.text((450, oy), desc, font=f_box_body, fill=C_TEXT_MUTED)
    oy += 48

# ==========================================
# CLEAN ARROWS CONNECTING THE PIPELINE
# ==========================================
# Ingress -> NeoVault
draw_arrow((x1 + w1, 410), (x2, 410), color="#0284C7", label="Normal HTTP", width=4)
draw_arrow((x1 + w1, 770), (x2, 770), color="#DC2626", label="Stolen Cookie", width=4)

# NeoVault Middleware -> TokenShield AI Engine
draw_arrow((x2 + w2, 420), (x3, 420), color="#16A34A", label="Telemetry", width=4)

# AI Engine -> Outcomes
draw_arrow((x3 + w3, 400), (x4, 400), color="#16A34A", label="Safe (< 0.85)", width=4)
draw_arrow((x3 + w3, 750), (x4, 750), color="#DC2626", label="Threat (>= 0.85)", width=4)

# Clean Feedback Route (Goes UNDER Stage 3 container, perfectly clean)
fb_y = 945
draw.line([(x4 + 100, 920), (x4 + 100, fb_y)], fill="#DC2626", width=3)
draw.line([(x4 + 100, fb_y), (x2 + w2 // 2, fb_y)], fill="#DC2626", width=3)
draw_arrow((x2 + w2 // 2, fb_y), (x2 + w2 // 2, 920), color="#DC2626", label=None, width=3)

# Label on the feedback line
fb_bbox = draw.textbbox((1525, fb_y), "Defensive Action: Invalidate Session & Lock Account", font=f_arrow, anchor="mm")
draw.rounded_rectangle([fb_bbox[0]-8, fb_bbox[1]-4, fb_bbox[2]+8, fb_bbox[3]+4], radius=6, fill="#FEF2F2", outline="#DC2626", width=2)
draw.text((1525, fb_y), "Defensive Action: Invalidate Session & Lock Account", font=f_arrow, fill="#DC2626", anchor="mm")

# Footer
draw.line([(80, 1260), (W - 80, 1260)], fill=C_BORDER, width=2)
draw.text((100, 1300), "TokenShield Project Architecture | Simple End-to-End View | Pure White Background", font=f_subtitle, fill=C_TEXT_MUTED)
draw.text((W - 100, 1300), "Designed for Poster Displays & Academic Presentations", font=f_subtitle, fill=C_TEXT_MUTED, anchor="ra")

# Save file
img.save(png_path, "PNG", dpi=(300, 300))
img.save(brain_path, "PNG", dpi=(300, 300))
print(f"Generated Simple Architecture Diagram: {png_path}")
