#!/usr/bin/env python3
"""
Generate Cyberpunk Dark-Theme Architecture Diagram: Alice vs Hacker -> Engine -> End Result
Matching the exact visual language of master_architecture_diagram.png (black background #060A12, neon glows).
"""

import os
import math
import textwrap
from PIL import Image, ImageDraw, ImageFont

out_dir = "/Users/yashpachhade/tokenshield/diagrams"
os.makedirs(out_dir, exist_ok=True)
png_path = os.path.join(out_dir, "cyberpunk_alice_vs_hacker.png")
brain_path = "/Users/yashpachhade/.gemini/antigravity/brain/9fb84148-ca25-4e5b-8d9e-09484d3c09e5/cyberpunk_alice_vs_hacker.png"

# Canvas dimensions: 2800 x 1550 px
W, H = 2800, 1550
img = Image.new("RGB", (W, H), "#060A12")
draw = ImageDraw.Draw(img)

def get_font(font_type="arial", size=14):
    try:
        if font_type == "bold":
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
        elif font_type == "mono":
            return ImageFont.truetype("/System/Library/Fonts/Courier.dfont", size)
        elif font_type == "italic":
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Italic.ttf", size)
        else:
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

f_hdr = get_font("bold", 36)
f_subhdr = get_font("arial", 18)
f_track = get_font("bold", 22)
f_box_title = get_font("bold", 18)
f_box_sub = get_font("arial", 13)
f_item_title = get_font("bold", 14)
f_item_desc = get_font("arial", 13)
f_badge = get_font("bold", 12)
f_pipe = get_font("bold", 13)
f_verdict = get_font("bold", 16)

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
    arrow_len = 14
    p1 = (p_end[0] - arrow_len * math.cos(angle - math.pi / 6), p_end[1] - arrow_len * math.sin(angle - math.pi / 6))
    p2 = (p_end[0] - arrow_len * math.cos(angle + math.pi / 6), p_end[1] - arrow_len * math.sin(angle + math.pi / 6))
    draw.polygon([p1, p_end, p2], fill=color)

    if label and label_pos:
        lx, ly = label_pos
        bbox = draw.textbbox((lx, ly), label, font=f_pipe, anchor="mm")
        pad_x, pad_y = 10, 5
        draw.rounded_rectangle([bbox[0]-pad_x, bbox[1]-pad_y, bbox[2]+pad_x, bbox[3]+pad_y], radius=5, fill=label_bg, outline=color, width=1)
        draw.text((lx, ly), label, fill=label_color or color, font=f_pipe, anchor="mm")

# =========================================================================
# 1. HEADER (Cyan Cyberpunk Banner)
# =========================================================================
X_LEFT = 100
X_RIGHT = W - 100

draw_card(X_LEFT, 25, X_RIGHT, 115, bg="#0B1321", border="#00D4FF", radius=12, width=2)
draw.text(((X_LEFT + X_RIGHT) // 2, 55), "TOKENSHIELD & NEOVAULT — REAL-TIME THREAT DEFENSE FLOW", fill="#FFFFFF", font=f_hdr, anchor="mm")
draw.text(((X_LEFT + X_RIGHT) // 2, 90), "Dual-Track Execution Circuit: Legitimate Session (Alice) vs. Account Takeover (Hacker) • Real-Time AI Scoring & Mitigation (<15ms)", fill="#00D4FF", font=f_subhdr, anchor="mm")

# =========================================================================
# GEOMETRY CONFIGURATION
# =========================================================================
col_w = 580
step_xs = [100, 780, 1460, 2140]

# =========================================================================
# 2. TOP TRACK: ALICE (LEGITIMATE USER) — NEON GREEN CIRCUIT
# =========================================================================
t1_y1 = 135
t1_y2 = 680

draw_card(X_LEFT, t1_y1, X_RIGHT, t1_y2, bg="#07131B", border="#052E2B", radius=14, width=2)
draw_pill(X_LEFT + 25, t1_y1 + 18, 90, 28, "CIRCUIT A", bg="#064E3B", border="#10B981", text_color="#6EE7B7")
draw.text((X_LEFT + 130, t1_y1 + 32), "LEGITIMATE USER EXECUTION PATH (ALICE — MUMBAI CORE GATEWAY)", fill="#34D399", font=f_track, anchor="lm")

# Card 1A: Alice
x, y = step_xs[0] + 20, t1_y1 + 65
w, h = col_w, 450
draw_card(x, y, x + w, y + h, bg="#0B1C1E", border="#10B981", radius=10, width=2)
draw_pill(x + 20, y + 16, 120, 26, "TRUSTED ORIGIN", bg="#064E3B", border="#10B981", text_color="#A7F3D0")
draw.text((x + 155, y + 29), "Alice (Verified Account)", fill="#ECFDF5", font=f_box_title, anchor="lm")
draw.text((x + 20, y + 60), "Location: Mumbai, India (Residential Broadband)", fill="#94A3B8", font=f_box_sub)

alice_items = [
    ("IP & ISP:", "103.21.124.88 • Clean Tata Communications ASN"),
    ("SESSION TOKEN:", "Valid JWT created 12m ago via standard login"),
    ("HARDWARE FINGERPRINT:", "Chrome 122 on macOS • Matched known device profile"),
    ("BEHAVIORAL BIOMETRICS:", "Typing speed 115 WPM • Key flight & mouse curvature MATCH"),
    ("REQUEST INTENT:", "Routine GET /api/banking/balance (INR 2,50,000)"),
]
iy = y + 90
for title, desc in alice_items:
    draw_card(x + 16, iy, x + w - 16, iy + 52, bg="#0F2927", border="#065F46", radius=6, width=1)
    draw.text((x + 30, iy + 16), title, fill="#6EE7B7", font=f_item_title, anchor="lm")
    draw.text((x + 30, iy + 36), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")
    iy += 60

# Card 2A: NeoVault WSGI Intercept
x = step_xs[1] - 20
draw_card(x, y, x + w, y + h, bg="#0B1C1E", border="#10B981", radius=10, width=2)
draw_pill(x + 20, y + 16, 130, 26, "ZERO-BYPASS HOOK", bg="#064E3B", border="#10B981", text_color="#A7F3D0")
draw.text((x + 165, y + 29), "NeoVault WSGI Middleware", fill="#ECFDF5", font=f_box_title, anchor="lm")
draw.text((x + 20, y + 60), "Endpoint: http://localhost:5001 • Container WSGI Layer", fill="#94A3B8", font=f_box_sub)

mid_items_a = [
    ("INTERCEPTION TIMING:", "Hooks request in 0.72 ms BEFORE view executes"),
    ("DATA EXTRACTION:", "Parses IP, session token, headers & biometric vector"),
    ("ASYNC DISPATCH:", "Transfers telemetry JSON to TokenShield Engine :7777"),
    ("CACHE LOOKUP:", "Checks in-memory O(1) local revocation bloom filter"),
    ("PASS-THROUGH STATE:", "Pending evaluation • Database state untouched"),
]
iy = y + 90
for title, desc in mid_items_a:
    draw_card(x + 16, iy, x + w - 16, iy + 52, bg="#0F2927", border="#065F46", radius=6, width=1)
    draw.text((x + 30, iy + 16), title, fill="#6EE7B7", font=f_item_title, anchor="lm")
    draw.text((x + 30, iy + 36), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")
    iy += 60

# Card 3A: TokenShield AI Engine
x = step_xs[2] - 60
draw_card(x, y, x + w, y + h, bg="#0B1C1E", border="#10B981", radius=10, width=2)
draw_pill(x + 20, y + 16, 130, 26, "AI ENGINE SCORING", bg="#064E3B", border="#10B981", text_color="#A7F3D0")
draw.text((x + 165, y + 29), "TokenShield AI Engine (:7777)", fill="#ECFDF5", font=f_box_title, anchor="lm")
draw.text((x + 20, y + 60), "8 Signals + 3 ML Models Ensemble Evaluation", fill="#94A3B8", font=f_box_sub)

ai_items_a = [
    ("8 SECURITY SIGNALS:", "S1-S8 Nominal • S5 Biometrics Match Baseline (0.02)"),
    ("GEO HAVERSINE SPEED:", "0 km/h (Consecutive requests inside Mumbai)"),
    ("ML ENSEMBLE:", "Isolation Forest: Normal • LSTM Sequence: Expected"),
    ("FINAL THREAT SCORE:", "0.02 / 1.00 (Configured Threshold: 0.85)"),
]
iy = y + 90
for title, desc in ai_items_a:
    draw_card(x + 16, iy, x + w - 16, iy + 52, bg="#0F2927", border="#065F46", radius=6, width=1)
    draw.text((x + 30, iy + 16), title, fill="#6EE7B7", font=f_item_title, anchor="lm")
    draw.text((x + 30, iy + 36), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")
    iy += 60

# Verdict Box
draw_card(x + 16, y + 360, x + w - 16, y + 425, bg="#064E3B", border="#34D399", radius=8, width=2)
draw.text((x + w//2, y + 392), "VERDICT: CLEAN (Score 0.02 < 0.85) — ALLOW REQUEST", fill="#FFFFFF", font=f_verdict, anchor="mm")

# Card 4A: Banking Outcome
x = step_xs[3] - 100
draw_card(x, y, x + w + 40, y + h, bg="#0B1C1E", border="#10B981", radius=10, width=2)
draw_pill(x + 20, y + 16, 140, 26, "TRANSACTION SAFE", bg="#064E3B", border="#10B981", text_color="#A7F3D0")
draw.text((x + 175, y + 29), "Core Banking Execution", fill="#ECFDF5", font=f_box_title, anchor="lm")
draw.text((x + 20, y + 60), "Status: 200 OK • Customer Capital 100% Secure", fill="#94A3B8", font=f_box_sub)

out_items_a = [
    ("CONTROLLER EXECUTION:", "Banking routes execute normally • Latency < 4.2ms"),
    ("ACCOUNT BALANCE:", "INR 2,50,000 intact & available in SQLite DB"),
    ("USER EXPERIENCE:", "Seamless, zero friction, zero CAPTCHAs, no MFA prompt"),
    ("OBSERVABILITY LOG:", "Clean transaction broadcast to War Room SOC stream"),
    ("SECURITY METRIC:", "Zero False Positives maintained on trusted traffic"),
]
iy = y + 90
for title, desc in out_items_a:
    draw_card(x + 16, iy, x + w + 24, iy + 52, bg="#0F2927", border="#065F46", radius=6, width=1)
    draw.text((x + 30, iy + 16), title, fill="#6EE7B7", font=f_item_title, anchor="lm")
    draw.text((x + 30, iy + 36), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")
    iy += 60

# Connectors for Track 1
p1 = (step_xs[0] + 20 + col_w, t1_y1 + 290)
p2 = (step_xs[1] - 20, t1_y1 + 290)
draw_flow_arrow([p1, p2], color="#10B981", width=3, label="VALID HTTPS", label_pos=((p1[0]+p2[0])//2, p1[1]-18), label_bg="#0B1C1E", label_color="#34D399")

p3 = (step_xs[1] - 20 + col_w, t1_y1 + 290)
p4 = (step_xs[2] - 60, t1_y1 + 290)
draw_flow_arrow([p3, p4], color="#10B981", width=3, label="TELEMETRY", label_pos=((p3[0]+p4[0])//2, p3[1]-18), label_bg="#0B1C1E", label_color="#34D399")

p5 = (step_xs[2] - 60 + col_w, t1_y1 + 290)
p6 = (step_xs[3] - 100, t1_y1 + 290)
draw_flow_arrow([p5, p6], color="#10B981", width=3, label="SCORE < 0.85", label_pos=((p5[0]+p6[0])//2, p5[1]-18), label_bg="#0B1C1E", label_color="#34D399")

# =========================================================================
# 3. BOTTOM TRACK: HACKER (ACCOUNT TAKEOVER) — NEON RED CIRCUIT
# =========================================================================
t2_y1 = 710
t2_y2 = 1255

draw_card(X_LEFT, t2_y1, X_RIGHT, t2_y2, bg="#160C14", border="#4D1525", radius=14, width=2)
draw_pill(X_LEFT + 25, t2_y1 + 18, 90, 28, "CIRCUIT B", bg="#7F1D1D", border="#EF4444", text_color="#FCA5A5")
draw.text((X_LEFT + 130, t2_y1 + 32), "ADVERSARY ATTACK PATH (STOLEN TOKEN / ATO — TOR EXIT RELAY)", fill="#F87171", font=f_track, anchor="lm")

# Card 1B: Hacker
x, y = step_xs[0] + 20, t2_y1 + 65
w, h = col_w, 450
draw_card(x, y, x + w, y + h, bg="#24101D", border="#FF3B5C", radius=10, width=2)
draw_pill(x + 20, y + 16, 120, 26, "THREAT ACTOR", bg="#7F1D1D", border="#FF3B5C", text_color="#FECDD3")
draw.text((x + 155, y + 29), "Dark Web Adversary", fill="#FFF1F2", font=f_box_title, anchor="lm")
draw.text((x + 20, y + 60), "Origin: Frankfurt Tor Exit Node • 185.220.101.5", fill="#94A3B8", font=f_box_sub)

hacker_items = [
    ("ATTACK VECTOR:", "Session Hijacking & Token Replay (Infostealer malware)"),
    ("STOLEN CREDENTIALS:", "Alice's active session cookie & Bearer JWT token"),
    ("HARDWARE FINGERPRINT:", "Headless Linux curl/bot • Mismatches Alice's Mac profile"),
    ("BEHAVIORAL BIOMETRICS:", "0 Keystrokes, 0 mouse movement • Scripted execution"),
    ("MALICIOUS INTENT:", "Immediate POST /api/banking/transfer (INR 1,50,000 to mule)"),
]
iy = y + 90
for title, desc in hacker_items:
    draw_card(x + 16, iy, x + w - 16, iy + 52, bg="#331422", border="#6B1D2F", radius=6, width=1)
    draw.text((x + 30, iy + 16), title, fill="#FF6B8B", font=f_item_title, anchor="lm")
    draw.text((x + 30, iy + 36), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")
    iy += 60

# Card 2B: NeoVault WSGI Intercept
x = step_xs[1] - 20
draw_card(x, y, x + w, y + h, bg="#24101D", border="#FF3B5C", radius=10, width=2)
draw_pill(x + 20, y + 16, 130, 26, "INTERCEPTION POINT", bg="#7F1D1D", border="#FF3B5C", text_color="#FECDD3")
draw.text((x + 165, y + 29), "NeoVault WSGI Middleware", fill="#FFF1F2", font=f_box_title, anchor="lm")
draw.text((x + 20, y + 60), "Zero Database Contamination • Intercepts Prior to DB Write", fill="#94A3B8", font=f_box_sub)

mid_items_b = [
    ("TOKEN VALIDITY:", "Token signature is valid (Bypasses legacy signature WAFs)"),
    ("PRE-EXECUTION HOOK:", "WSGI interceptor blocks execution of transfer logic"),
    ("TELEMETRY PACKET:", "Packages Tor IP, missing biometrics, endpoint risk"),
    ("DISPATCH SPEED:", "Transfers vector to TokenShield Engine in 0.65ms"),
    ("HOLDING PATTERN:", "Database write blocked until threat verdict returns"),
]
iy = y + 90
for title, desc in mid_items_b:
    draw_card(x + 16, iy, x + w - 16, iy + 52, bg="#331422", border="#6B1D2F", radius=6, width=1)
    draw.text((x + 30, iy + 16), title, fill="#FF6B8B", font=f_item_title, anchor="lm")
    draw.text((x + 30, iy + 36), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")
    iy += 60

# Card 3B: TokenShield AI Engine
x = step_xs[2] - 60
draw_card(x, y, x + w, y + h, bg="#24101D", border="#FF3B5C", radius=10, width=2)
draw_pill(x + 20, y + 16, 130, 26, "AI THREAT VERDICT", bg="#7F1D1D", border="#FF3B5C", text_color="#FECDD3")
draw.text((x + 165, y + 29), "TokenShield AI Engine (:7777)", fill="#FFF1F2", font=f_box_title, anchor="lm")
draw.text((x + 20, y + 60), "Multi-Model Fusion & 8-Signal Anomaly Scoring", fill="#94A3B8", font=f_box_sub)

ai_items_b = [
    ("S1 IP REPUTATION:", "Tor Exit Node identified in darklist (Score = 0.85)"),
    ("S5 BIOMETRICS:", "Zero human keystroke dynamics detected (Score = 0.90)"),
    ("S6 GEOGRAPHY:", "Haversine Impossible Travel Mumbai -> Frankfurt in 4m (0.85)"),
    ("S8 SEQUENTIAL:", "Skipped account dashboard, leaped straight to payment (0.88)"),
]
iy = y + 90
for title, desc in ai_items_b:
    draw_card(x + 16, iy, x + w - 16, iy + 52, bg="#331422", border="#6B1D2F", radius=6, width=1)
    draw.text((x + 30, iy + 16), title, fill="#FF6B8B", font=f_item_title, anchor="lm")
    draw.text((x + 30, iy + 36), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")
    iy += 60

# Verdict Box
draw_card(x + 16, y + 360, x + w - 16, y + 425, bg="#7F1D1D", border="#FF3B5C", radius=8, width=2)
draw.text((x + w//2, y + 392), "VERDICT: CRITICAL ATO (Score 0.94 >= 0.85) — TRIGGER 7 LAYERS", fill="#FFFFFF", font=f_verdict, anchor="mm")

# Card 4B: Automated 7-Layer Mitigation
x = step_xs[3] - 100
draw_card(x, y, x + w + 40, y + h, bg="#24101D", border="#FF3B5C", radius=10, width=2)
draw_pill(x + 20, y + 16, 140, 26, "CASCADING DEFENSE", bg="#7F1D1D", border="#FF3B5C", text_color="#FECDD3")
draw.text((x + 175, y + 29), "7-Layer Progressive Mitigation", fill="#FFF1F2", font=f_box_title, anchor="lm")
draw.text((x + 20, y + 60), "Sub-15ms Cascading Execution • Zero Capital Loss", fill="#94A3B8", font=f_box_sub)

mit_items = [
    ("L1 JWT REVOCATION:", "Stolen token blacklisted in-memory in ~0 ms"),
    ("L2 SESSION DESTROY:", "Active server session destroyed across all instances in ~0 ms"),
    ("L3 ACCOUNT SOFT-LOCK:", "Alice's screen locked with Red Defensive Banner (<5 ms)"),
    ("L4 FIREWALL IP BAN:", "Attacker's Tor node IP permanently blacklisted (<8 ms)"),
    ("OUTCOME:", "INR 1,50,000 FRAUD STOPPED • INR 0 LOST • DB UNALTERED"),
]
iy = y + 90
for title, desc in mit_items:
    draw_card(x + 16, iy, x + w + 24, iy + 52, bg="#331422", border="#6B1D2F", radius=6, width=1)
    draw.text((x + 30, iy + 16), title, fill="#FF6B8B", font=f_item_title, anchor="lm")
    draw.text((x + 30, iy + 36), desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")
    iy += 60

# Connectors for Track 2
p7 = (step_xs[0] + 20 + col_w, t2_y1 + 290)
p8 = (step_xs[1] - 20, t2_y1 + 290)
draw_flow_arrow([p7, p8], color="#FF3B5C", width=3, label="STOLEN COOKIE", label_pos=((p7[0]+p8[0])//2, p7[1]-18), label_bg="#24101D", label_color="#FF6B8B")

p9 = (step_xs[1] - 20 + col_w, t2_y1 + 290)
p10 = (step_xs[2] - 60, t2_y1 + 290)
draw_flow_arrow([p9, p10], color="#FF3B5C", width=3, label="TELEMETRY", label_pos=((p9[0]+p10[0])//2, p9[1]-18), label_bg="#24101D", label_color="#FF6B8B")

p11 = (step_xs[2] - 60 + col_w, t2_y1 + 290)
p12 = (step_xs[3] - 100, t2_y1 + 290)
draw_flow_arrow([p11, p12], color="#FF3B5C", width=3, label="SCORE >= 0.85 (<15ms)", label_pos=((p11[0]+p12[0])//2, p11[1]-18), label_bg="#24101D", label_color="#FF6B8B")

# =========================================================================
# 4. BOTTOM OBSERVABILITY TIER (Cyberpunk Slate Blue)
# =========================================================================
t3_y1 = 1285
t3_y2 = 1485
draw_card(X_LEFT, t3_y1, X_RIGHT, t3_y2, bg="#0A111C", border="#1E2A3C", radius=12, width=2)
draw_pill(X_LEFT + 25, t3_y1 + 18, 110, 26, "OBSERVABILITY", bg="#1E293B", border="#00D4FF", text_color="#38BDF8")
draw.text((X_LEFT + 150, t3_y1 + 31), "TIER III: LIVE TELEMETRY & POST-INCIDENT FORENSIC AUDITING", fill="#94A3B8", font=f_track, anchor="lm")

obs_boxes = [
    ("WAR ROOM SOC DASHBOARD (:7777)", "Live Server-Sent Events (SSE) stream\n7-Layer dynamic health badges\nReal-time 0.00 to 1.00 threat gauge"),
    ("SIMULATION DASHBOARD (:5001)", "Direct kernel hardware telemetry via psutil\nMacBook Apple Silicon 8-Core/8GB live metrics\nBefore, During, & After CPU/RAM history"),
    ("NIST SP 800-61r2 FORENSIC DOSSIER", "Automated incident report generation\nMapped to MITRE ATT&CK (T1539, T1071.001)\nInstant Print-to-PDF court-ready export"),
]
for idx, (title, desc) in enumerate(obs_boxes):
    bx = X_LEFT + 25 + idx * 850
    draw_card(bx, t3_y1 + 60, bx + 830, t3_y1 + 175, bg="#0D1E30", border="#164E63", radius=8, width=1)
    draw.text((bx + 20, t3_y1 + 86), title, fill="#00D4FF", font=f_item_title, anchor="lm")
    dy = t3_y1 + 115
    for line in desc.split("\n"):
        draw.text((bx + 20, dy), line, fill="#CBD5E1", font=f_item_desc, anchor="lm")
        dy += 22

# Save PNG
img.save(png_path, "PNG", dpi=(300, 300))
img.save(brain_path, "PNG", dpi=(300, 300))
print(f"Generated Cyberpunk Alice vs Hacker Diagram: {png_path}")
