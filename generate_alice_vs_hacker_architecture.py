#!/usr/bin/env python3
"""
Generate Simple End-to-End Flow Diagram: Alice vs Hacker -> AI Engine -> End Results
High visual clarity, pure white background for poster presentation.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

out_dir = "/Users/yashpachhade/tokenshield/diagrams"
os.makedirs(out_dir, exist_ok=True)
png_path = os.path.join(out_dir, "engine_flow_alice_vs_hacker.png")
brain_path = "/Users/yashpachhade/.gemini/antigravity/brain/9fb84148-ca25-4e5b-8d9e-09484d3c09e5/engine_flow_alice_vs_hacker.png"

# Canvas: 2600 x 1400 px
W, H = 2600, 1400
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

f_main_title = get_font("bold", 44)
f_subtitle = get_font("arial", 21)
f_track_hdr = get_font("bold", 24)
f_step_num = get_font("bold", 14)
f_box_title = get_font("bold", 19)
f_box_bold = get_font("bold", 15)
f_box_text = get_font("arial", 15)
f_arrow = get_font("bold", 14)
f_footer = get_font("arial", 16)

C_TEXT_MAIN = "#0F172A"       # Slate 900
C_TEXT_MUTED = "#334155"      # Slate 700
C_BORDER = "#CBD5E1"          # Slate 300

def draw_pill(x, y, text, bg, fg, font=f_step_num):
    w = int(draw.textlength(text, font=font)) + 22
    h = 28
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
# 1. HEADER
# ==========================================
draw.text((W // 2, 55), "TokenShield: End-to-End Threat Defense Flow", font=f_main_title, fill=C_TEXT_MAIN, anchor="mm")
draw.text((W // 2, 105), "How TokenShield Differentiates Legitimate Users from Attackers in Real-Time (<15ms)", font=f_subtitle, fill=C_TEXT_MUTED, anchor="mm")
draw.line([(80, 145), (W - 80, 145)], fill=C_BORDER, width=2)

# ==========================================
# LAYOUT GEOMETRY: 4 Horizontal Steps
# ==========================================
# Step 1: User / Attacker Origin (x: 100)
# Step 2: Request & Interception (x: 700)
# Step 3: TokenShield AI Engine Analysis (x: 1320)
# Step 4: Final Banking Outcome (x: 1960)

box_w = 480
step_xs = [100, 720, 1340, 1960]

# =========================================================================
# TOP TRACK: LEGITIMATE USER (ALICE) - GREEN PALETTE
# =========================================================================
track1_y = 190
draw_pill(100, track1_y, "PATH A", "#DCFCE7", "#15803D")
draw.text((185, track1_y + 14), "Legitimate User Journey (Clean Session)", font=f_track_hdr, fill="#15803D", anchor="lm")

# Step 1A: Alice
x, y, w, h = step_xs[0], 245, box_w, 420
draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill="#F0FDF4", outline="#16A34A", width=3)
draw_pill(x + 20, y + 20, "1. USER ORIGIN", "#16A34A", "#FFFFFF")
draw.text((x + 165, y + 34), "Alice (Genuine Customer)", font=f_box_title, fill="#15803D", anchor="lm")

bullets = [
    ("Location:", "Mumbai, India (Home Wi-Fi)"),
    ("IP Address:", "103.21.124.88 (Clean Residential)"),
    ("Device:", "MacBook Chrome (Known Fingerprint)"),
    ("Biometrics:", "Typical typing rhythm & mouse path"),
    ("Session:", "Valid JWT created 10 mins ago")
]
by = y + 85
for label, val in bullets:
    draw.text((x + 24, by), label, font=f_box_bold, fill=C_TEXT_MAIN)
    draw.text((x + 130, by), val, font=f_box_text, fill=C_TEXT_MUTED)
    by += 44

# Step 2A: NeoVault Request Intercept
x, y, w, h = step_xs[1], 245, box_w, 420
draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill="#F0FDF4", outline="#16A34A", width=3)
draw_pill(x + 20, y + 20, "2. INGRESS & HOOK", "#16A34A", "#FFFFFF")
draw.text((x + 180, y + 34), "NeoVault WSGI Intercept", font=f_box_title, fill="#15803D", anchor="lm")

bullets = [
    ("Request:", "GET /api/banking/balance"),
    ("Target:", "Check Account (INR 2,50,000)"),
    ("Middleware:", "WSGI Hooks packet in <0.8 ms"),
    ("Telemetry:", "Collects IP, headers & keystrokes"),
    ("Status:", "Non-blocking async forward to Engine")
]
by = y + 85
for label, val in bullets:
    draw.text((x + 24, by), label, font=f_box_bold, fill=C_TEXT_MAIN)
    draw.text((x + 130, by), val, font=f_box_text, fill=C_TEXT_MUTED)
    by += 44

# Step 3A: TokenShield AI Evaluation
x, y, w, h = step_xs[2], 245, box_w + 40, 420
draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill="#F0FDF4", outline="#16A34A", width=3)
draw_pill(x + 20, y + 20, "3. AI EVALUATION", "#16A34A", "#FFFFFF")
draw.text((x + 175, y + 34), "TokenShield AI Engine", font=f_box_title, fill="#15803D", anchor="lm")

bullets = [
    ("8 Signals:", "All 8 signals return nominal (0.00 - 0.05)"),
    ("Biometrics:", "Typing speed & flight time MATCH baseline"),
    ("Geography:", "Zero travel anomaly (Mumbai -> Mumbai)"),
    ("ML Models:", "Isolation Forest & LSTM flag 0 anomalies"),
    ("Threat Score:", "0.02 / 1.00 (Far below 0.85 threshold)")
]
by = y + 85
for label, val in bullets:
    draw.text((x + 24, by), label, font=f_box_bold, fill=C_TEXT_MAIN)
    draw.text((x + 140, by), val, font=f_box_text, fill=C_TEXT_MUTED)
    by += 44

# Score Pill
draw.rounded_rectangle([x + 24, y + 340, x + w - 24, y + 395], radius=10, fill="#DCFCE7", outline="#16A34A", width=2)
draw.text((x + w//2, y + 368), "VERDICT: CLEAN  |  Threat Score = 0.02 (PASS)", font=f_box_bold, fill="#15803D", anchor="mm")

# Step 4A: End Outcome
x, y, w, h = step_xs[3] + 40, 245, box_w - 40, 420
draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill="#F0FDF4", outline="#16A34A", width=3)
draw_pill(x + 20, y + 20, "4. END RESULT", "#16A34A", "#FFFFFF")
draw.text((x + 150, y + 34), "Transaction Approved", font=f_box_title, fill="#15803D", anchor="lm")

bullets = [
    ("Action:", "Bank Controller executes safely"),
    ("Latency:", "Overhead < 5 ms total (imperceptible)"),
    ("Balance:", "INR 2,50,000 intact & accessible"),
    ("Experience:", "Seamless, zero friction, no CAPTCHA"),
    ("Audit Log:", "Logged as Clean Session in War Room")
]
by = y + 85
for label, val in bullets:
    draw.text((x + 24, by), label, font=f_box_bold, fill=C_TEXT_MAIN)
    draw.text((x + 125, by), val, font=f_box_text, fill="#166534")
    by += 44

# Connectors for Track 1
draw_arrow((step_xs[0] + box_w, 455), (step_xs[1], 455), color="#16A34A", label="Valid Request", width=4)
draw_arrow((step_xs[1] + box_w, 455), (step_xs[2], 455), color="#16A34A", label="Telemetry", width=4)
draw_arrow((step_xs[2] + box_w + 40, 455), (step_xs[3] + 40, 455), color="#16A34A", label="Score < 0.85", width=4)

# =========================================================================
# DIVIDER BETWEEN PATHS
# =========================================================================
draw.line([(100, 715), (W - 100, 715)], fill="#E2E8F0", width=2)

# =========================================================================
# BOTTOM TRACK: ATTACKER (HACKER / ATO) - RED PALETTE
# =========================================================================
track2_y = 755
draw_pill(100, track2_y, "PATH B", "#FEE2E2", "#DC2626")
draw.text((185, track2_y + 14), "Threat Actor Attack Journey (Account Takeover / Stolen Cookie)", font=f_track_hdr, fill="#DC2626", anchor="lm")

# Step 1B: Hacker
x, y, w, h = step_xs[0], 810, box_w, 420
draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill="#FEF2F2", outline="#DC2626", width=3)
draw_pill(x + 20, y + 20, "1. ADVERSARY", "#DC2626", "#FFFFFF")
draw.text((x + 155, y + 34), "Attacker (Dark Web / Tor)", font=f_box_title, fill="#B91C1C", anchor="lm")

bullets = [
    ("Origin:", "Frankfurt, Germany (Tor Exit Node)"),
    ("IP Address:", "185.220.101.5 (Known Dark Web Node)"),
    ("Stolen Creds:", "Alice's active session cookie & JWT"),
    ("Biometrics:", "0 Keystrokes (Automated Python Script)"),
    ("Attack Goal:", "Immediate transfer of INR 1,50,000")
]
by = y + 85
for label, val in bullets:
    draw.text((x + 24, by), label, font=f_box_bold, fill=C_TEXT_MAIN)
    draw.text((x + 130, by), val, font=f_box_text, fill=C_TEXT_MUTED)
    by += 44

# Step 2B: NeoVault Interception
x, y, w, h = step_xs[1], 810, box_w, 420
draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill="#FEF2F2", outline="#DC2626", width=3)
draw_pill(x + 20, y + 20, "2. INGRESS & HOOK", "#DC2626", "#FFFFFF")
draw.text((x + 180, y + 34), "NeoVault WSGI Intercept", font=f_box_title, fill="#B91C1C", anchor="lm")

bullets = [
    ("Request:", "POST /api/banking/transfer (High Value)"),
    ("Payload:", "Send INR 1,50,000 to Mule Account"),
    ("Token Status:", "Cryptographically valid (Passes standard WAF)"),
    ("Middleware:", "WSGI Hooks request BEFORE DB commit"),
    ("Action:", "Forwards packet vector to Engine :7777")
]
by = y + 85
for label, val in bullets:
    draw.text((x + 24, by), label, font=f_box_bold, fill=C_TEXT_MAIN)
    draw.text((x + 130, by), val, font=f_box_text, fill=C_TEXT_MUTED)
    by += 44

# Step 3B: TokenShield AI Engine Analysis
x, y, w, h = step_xs[2], 810, box_w + 40, 420
draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill="#FEF2F2", outline="#DC2626", width=3)
draw_pill(x + 20, y + 20, "3. AI EVALUATION", "#DC2626", "#FFFFFF")
draw.text((x + 175, y + 34), "TokenShield AI Engine", font=f_box_title, fill="#B91C1C", anchor="lm")

bullets = [
    ("S1 IP Check:", "Tor Exit Node detected (Score = 0.85)"),
    ("S5 Biometrics:", "Zero typing cadence / automated bot (0.90)"),
    ("S6 Geography:", "Mumbai -> Frankfurt in 4 mins (Impossible)"),
    ("S8 Sequence:", "Skipped dashboard, leaped to transfer (0.88)"),
    ("ML Ensemble:", "Meta-Classifier blends signals -> Score = 0.94")
]
by = y + 85
for label, val in bullets:
    draw.text((x + 24, by), label, font=f_box_bold, fill=C_TEXT_MAIN)
    draw.text((x + 140, by), val, font=f_box_text, fill=C_TEXT_MUTED)
    by += 44

# Score Pill
draw.rounded_rectangle([x + 24, y + 340, x + w - 24, y + 395], radius=10, fill="#FEE2E2", outline="#DC2626", width=2)
draw.text((x + w//2, y + 368), "VERDICT: CRITICAL THREAT  |  Threat Score = 0.94 (TRIGGER)", font=f_box_bold, fill="#DC2626", anchor="mm")

# Step 4B: Automated Mitigation & End Outcome
x, y, w, h = step_xs[3] + 40, 810, box_w - 40, 420
draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill="#FEF2F2", outline="#DC2626", width=3)
draw_pill(x + 20, y + 20, "4. MITIGATION", "#DC2626", "#FFFFFF")
draw.text((x + 150, y + 34), "7-Layer Neutralization", font=f_box_title, fill="#B91C1C", anchor="lm")

bullets = [
    ("L1 Token Revoke:", "Stolen JWT blacklisted in 1.2 ms"),
    ("L2 Session Kill:", "Active session cache destroyed"),
    ("L3 Soft-Lock:", "Alice's screen shows Red Security Banner"),
    ("L4 IP Ban:", "Attacker IP blocked on Ingress Firewall"),
    ("MONEY SAVED:", "INR 1,50,000 Fraud Stopped (INR 0 Lost)")
]
by = y + 85
for label, val in bullets:
    draw.text((x + 24, by), label, font=f_box_bold, fill="#B91C1C")
    draw.text((x + 165, by), val, font=f_box_text, fill=C_TEXT_MUTED)
    by += 44

# Connectors for Track 2
draw_arrow((step_xs[0] + box_w, 1020), (step_xs[1], 1020), color="#DC2626", label="Stolen Cookie", width=4)
draw_arrow((step_xs[1] + box_w, 1020), (step_xs[2], 1020), color="#DC2626", label="Telemetry", width=4)
draw_arrow((step_xs[2] + box_w + 40, 1020), (step_xs[3] + 40, 1020), color="#DC2626", label="Score >= 0.85 (<15ms)", width=4)

# ==========================================
# FOOTER / METADATA
# ==========================================
draw.line([(80, 1280), (W - 80, 1280)], fill=C_BORDER, width=2)
draw.text((100, 1330), "TokenShield Real-Time Defense Architecture | End-to-End Threat Comparison | Pure White Poster Edition", font=f_footer, fill=C_TEXT_MUTED)
draw.text((W - 100, 1330), "Sub-15ms Cascading Mitigation  *  Zero False Positives for Clean Users", font=f_footer, fill=C_TEXT_MUTED, anchor="ra")

img.save(png_path, "PNG", dpi=(300, 300))
img.save(brain_path, "PNG", dpi=(300, 300))
print(f"Generated End-to-End Alice vs Hacker Diagram: {png_path}")
