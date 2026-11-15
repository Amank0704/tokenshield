import os
import math
from PIL import Image, ImageDraw, ImageFont

out_dir = "/Users/yashpachhade/tokenshield/diagrams"
os.makedirs(out_dir, exist_ok=True)

font_path_regular = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
font_path_bold = "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"
font_path_italic = "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf"
font_path_arial = "/System/Library/Fonts/Supplemental/Arial.ttf"
font_path_arial_bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

def get_font(font_type="arial", size=14):
    try:
        if font_type == "arial_bold":
            return ImageFont.truetype(font_path_arial_bold, size)
        elif font_type == "arial":
            return ImageFont.truetype(font_path_arial, size)
        elif font_type == "bold":
            return ImageFont.truetype(font_path_bold, size)
        elif font_type == "italic":
            return ImageFont.truetype(font_path_italic, size)
        else:
            return ImageFont.truetype(font_path_regular, size)
    except Exception:
        return ImageFont.load_default()

def create_full_sequence_diagram():
    # Width and height for an exhaustive, publication-grade sequence diagram
    width, height = 1600, 2400
    img = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    f_title = get_font("arial_bold", 24)
    f_sub = get_font("arial", 15)
    f_header = get_font("arial_bold", 15)
    f_msg = get_font("arial_bold", 13)
    f_msg_regular = get_font("arial", 13)
    f_note = get_font("italic", 12)
    f_phase = get_font("arial_bold", 14)
    f_badge = get_font("arial_bold", 11)

    # Document Header Title
    draw.text((width // 2, 45), "TokenShield: Complete End-to-End System Sequence Diagram", fill="#0F172A", font=f_title, anchor="mm")
    draw.text((width // 2, 75), "Comprehensive Request Lifecycle, 7-Signal Critical Path Scoring & 8-Stage Automated Mitigation", fill="#475569", font=f_sub, anchor="mm")

    # Actors / Lifeline Columns
    participants = [
        ("Legit User", 130, "#2563EB", "#EFF6FF"),
        ("Attacker", 340, "#DC2626", "#FEF2F2"),
        ("Nginx (Edge)", 570, "#0D9488", "#F0FDFA"),
        ("TokenShield Engine", 830, "#1E3A8A", "#EEF2FF"),
        ("Redis (Cache)", 1090, "#B91C1C", "#FFF1F2"),
        ("Database (DB)", 1310, "#475569", "#F8FAFC"),
        ("SOC / User Alert", 1490, "#D97706", "#FFFBEB")
    ]

    top_y = 120
    bottom_y = 2320

    # Draw Lifelines (vertical dashed tracks)
    for name, x, color, fill_c in participants:
        # Draw dashed line
        for y in range(top_y + 40, bottom_y, 16):
            draw.line([(x, y), (x, y + 8)], fill="#CBD5E1", width=2)

    # Helper: draw participant box at top and bottom
    for name, x, color, fill_c in participants:
        for py in [top_y, bottom_y]:
            w_box = 105
            h_box = 44
            draw.rounded_rectangle([x - w_box//2, py - h_box//2, x + w_box//2, py + h_box//2], radius=6, fill=fill_c, outline=color, width=2)
            draw.text((x, py), name, fill=color, font=f_header, anchor="mm")

    # Helper function: draw message arrow
    def draw_msg(x1, x2, y, text, color="#1E40AF", dashed=False, bold=True, return_arrow=False, badge=""):
        if dashed:
            dist = abs(x2 - x1)
            steps = max(int(dist / 10), 1)
            for i in range(steps):
                if i % 2 == 0:
                    sx = x1 + (x2 - x1) * (i / steps)
                    ex = x1 + (x2 - x1) * ((i + 1) / steps)
                    draw.line([(sx, y), (ex, y)], fill=color, width=2)
        else:
            draw.line([(x1, y), (x2, y)], fill=color, width=2)

        # Arrowhead
        direction = 1 if x2 > x1 else -1
        draw.polygon([(x2, y), (x2 - 10 * direction, y - 5), (x2 - 10 * direction, y + 5)], fill=color)

        mid_x = (x1 + x2) / 2
        font_use = f_msg if bold else f_msg_regular
        draw.text((mid_x, y - 10), text, fill=color, font=font_use, anchor="mb")

        if badge:
            # Draw latency or status pill
            badge_w = len(badge) * 7 + 12
            bx1, by1 = mid_x - badge_w // 2, y + 3
            bx2, by2 = mid_x + badge_w // 2, y + 21
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=4, fill="#F1F5F9", outline="#94A3B8", width=1)
            draw.text((mid_x, (by1 + by2) // 2), badge, fill="#334155", font=f_badge, anchor="mm")

    # Helper function: self-call note on a participant
    def draw_self_note(x, y, text, color="#1E40AF", side="right", sub_text=""):
        # loop arrow
        offset = 35 if side == "right" else -35
        draw.line([(x, y - 10), (x + offset, y - 10)], fill=color, width=2)
        draw.line([(x + offset, y - 10), (x + offset, y + 10)], fill=color, width=2)
        draw.line([(x + offset, y + 10), (x, y + 10)], fill=color, width=2)
        direction = -1 if side == "right" else 1
        draw.polygon([(x, y + 10), (x - 8 * direction, y + 6), (x - 8 * direction, y + 14)], fill=color)

        anchor = "lm" if side == "right" else "rm"
        text_x = x + offset + (10 if side == "right" else -10)
        draw.text((text_x, y - (4 if sub_text else 0)), text, fill=color, font=f_msg, anchor=anchor)
        if sub_text:
            draw.text((text_x, y + 14), sub_text, fill="#64748B", font=f_note, anchor=anchor)

    # Helper function: Phase Divider Banner
    def draw_phase_banner(y, title, bg="#F8FAFC", border="#CBD5E1", text_color="#1E293B"):
        h_banner = 28
        draw.rounded_rectangle([60, y - h_banner//2, width - 60, y + h_banner//2], radius=5, fill=bg, outline=border, width=1)
        draw.text((80, y), title, fill=text_color, font=f_phase, anchor="lm")

    # -------------------------------------------------------------
    # PHASE 1: LOGIN & CREDENTIAL ISSUANCE
    # -------------------------------------------------------------
    draw_phase_banner(180, "PHASE 1: LEGITIMATE AUTHENTICATION & BASELINE ANCHORING", bg="#EFF6FF", border="#93C5FD", text_color="#1E40AF")
    
    draw_msg(130, 570, 220, "(1) POST /api/auth/login + Client Telemetry (FP, Canvas, IP)", color="#2563EB")
    draw_msg(570, 830, 260, "(2) proxy_pass to Auth Blueprint", color="#2563EB")
    draw_msg(830, 1310, 300, "(3) Verify user credentials & password hash", color="#475569")
    draw_msg(1310, 830, 340, "(4) Credentials valid: User ID & Roles confirmed", color="#475569", dashed=True)
    draw_self_note(830, 380, "(5) Issue JWT Bearer Token (w/ claim jti)", color="#1E3A8A")
    draw_msg(830, 1090, 425, "(6) Register initial session baseline (ts:fp, ts:geo, ts:vel)", color="#B91C1C", badge="TTL 24h")
    draw_msg(830, 130, 475, "(7) Return HTTP 200 OK + JWT Bearer Token", color="#059669", dashed=True)

    # -------------------------------------------------------------
    # PHASE 2: NORMAL USER TRANSACTIONS (SAFE SCORING)
    # -------------------------------------------------------------
    draw_phase_banner(535, "PHASE 2: CONTINUOUS 7-SIGNAL MONITORING — BENIGN REQUEST (SCORE S < 0.30)", bg="#F0FDF4", border="#86EFAC", text_color="#166534")

    draw_msg(130, 570, 575, "(8) GET /api/banking/dashboard (Bearer JWT + Biometric Cadence)", color="#059669")
    draw_msg(570, 830, 615, "(9) proxy_pass → Flask before_request hook", color="#059669")
    draw_msg(830, 1090, 655, "(10) Query Redis: ts:block:* check & INCR sliding window", color="#B91C1C")
    draw_msg(1090, 830, 695, "(11) Return: Not blocked, velocity normal (12 req/min)", color="#B91C1C", dashed=True)
    draw_self_note(830, 740, "(12) Calculate 7 signals: IP, UA, Payload, Geo, Biometrics", color="#1E3A8A", sub_text="Score S = 0.08  [Safe Tier]")
    draw_msg(830, 1310, 790, "(13) Execute business logic & fetch balance from DB", color="#475569")
    draw_msg(830, 130, 835, "(14) Return HTTP 200 OK with banking dashboard data", color="#059669", dashed=True)

    # -------------------------------------------------------------
    # PHASE 3: ATTACKER SESSION HIJACKING INVOCATION
    # -------------------------------------------------------------
    draw_phase_banner(895, "PHASE 3: TOKEN THEFT EXFILTRATION & MALICIOUS REPLAY", bg="#FEF2F2", border="#FCA5A5", text_color="#991B1B")

    draw_self_note(340, 935, "(15) Adversary steals JWT (via XSS, MITM, extension)", color="#DC2626", side="left")
    draw_msg(340, 570, 985, "(16) POST /api/banking/transfer with stolen JWT (Tor IP, spoofed UA)", color="#DC2626", dashed=True)
    draw_msg(570, 830, 1030, "(17) Forward packet to TokenShield before_request engine", color="#DC2626")

    # -------------------------------------------------------------
    # PHASE 4: CRITICAL ANOMALY SCORING
    # -------------------------------------------------------------
    draw_phase_banner(1090, "PHASE 4: REAL-TIME 7-SIGNAL EVALUATION & CRITICAL BREACH TRIGGER", bg="#FFF7ED", border="#FED7AA", text_color="#C2410C")

    draw_msg(830, 1090, 1130, "(18) Redis state queries: geo-history, sliding-window rate, origin IP", color="#B91C1C")
    draw_msg(1090, 830, 1170, "(19) Return: Redis origin IP drift (+0.20), velocity spike (+0.30)", color="#B91C1C", dashed=True)
    draw_self_note(830, 1225, "(20) Seven-Signal Critical Path Scoring & ML Ensemble", color="#C2410C", 
                   sub_text="s1(Rep)=0.25, s2(Vel)=0.30, s3(Sess)=0.30, s5(Bio)=0.25, s6(Geo)=0.35 → S = 0.94 ≥ 0.85")
    draw_self_note(830, 1285, "(21) Anomaly Threshold Exceeded → Autonomous Critical Trigger", color="#B91C1C", 
                   sub_text="Threat(S) = CRITICAL  → Trigger 8-Stage Mitigation Pipeline")

    # -------------------------------------------------------------
    # PHASE 5: 8-STAGE AUTOMATED MITIGATION PIPELINE
    # -------------------------------------------------------------
    draw_phase_banner(1350, "PHASE 5: EIGHT-STAGE PROGRESSIVE MITIGATION CASCADE", bg="#FEF2F2", border="#EF4444", text_color="#B91C1C")

    draw_msg(830, 1090, 1395, "(22) Stage 1: Redis token revocation (SET ts:block:<jti>)", color="#B91C1C", badge="~0 ms latency")
    draw_msg(830, 1090, 1445, "(23) Stage 2: Redis IP block (SET ts:block:ip:<ip>)", color="#B91C1C", badge="TTL 24h (~0 ms)")
    draw_msg(830, 570, 1495, "(24) Stage 3: Write IP to dynamic blocklist file (Nginx)", color="#0D9488", badge="reload ≤ 5s")
    draw_msg(830, 1090, 1545, "(25) Stage 4: Ban rogue device fingerprint (SET ts:fp:<hash>)", color="#B91C1C", badge="TTL 72h (~0 ms)")
    draw_msg(830, 1310, 1595, "(26) Stage 5: DB Account Lockout & Force 2FA Step-up", color="#475569", badge="~10 ms latency")
    draw_self_note(830, 1650, "(27) Stage 6: Coordinated-attack cluster correlation", color="#1E3A8A", sub_text="Cross-tenant telemetry matching (~10 ms)")
    draw_msg(830, 1490, 1705, "(28) Stage 7: Dispatch SMTP high-priority alert to affected user & SOC", color="#D97706", badge="async thread")
    draw_msg(830, 1490, 1755, "(29) Stage 8: SSE real-time security dashboard event broadcast", color="#D97706", badge="async push")

    # -------------------------------------------------------------
    # PHASE 6: TERMINATION & PERIMETER ENFORCEMENT
    # -------------------------------------------------------------
    draw_phase_banner(1815, "PHASE 6: TRANSACTION TERMINATION & IMMEDIATE MULTI-LAYER ENFORCEMENT", bg="#F8FAFC", border="#CBD5E1", text_color="#0F172A")

    draw_msg(830, 340, 1855, "(30) Abort transaction: HTTP 401 Unauthorized [Revoked Token]", color="#DC2626", dashed=True, bold=True)
    draw_msg(340, 570, 1905, "(31) Attacker re-attempts transfer with identical stolen JWT", color="#DC2626", dashed=True)
    draw_self_note(570, 1950, "(32) Nginx edge dynamic blocklist match", color="#0D9488", side="left", sub_text="IP dropped at edge in 0.8 ms")
    draw_msg(570, 340, 2000, "(33) Edge Rejection: HTTP 403 Forbidden (Never reaches Flask)", color="#DC2626", bold=True)
    draw_msg(340, 570, 2050, "(34) Attacker switches IP via proxy pool, retries token", color="#DC2626", dashed=True)
    draw_msg(570, 830, 2095, "(35) Nginx passes new IP to Flask middleware", color="#0D9488")
    draw_msg(830, 1090, 2135, "(36) Instant O(1) Redis blocklist check: ts:block:<jti> found", color="#B91C1C")
    draw_msg(830, 340, 2180, "(37) Autonomous Token Rejection: HTTP 401 Unauthorized", color="#DC2626", bold=True)

    # -------------------------------------------------------------
    # PHASE 7: ACCOUNT RECOVERY & LEGITIMATE 2FA STEP-UP
    # -------------------------------------------------------------
    draw_phase_banner(2235, "PHASE 7: USER RECOVERY, 2FA STEP-UP & RE-AUTHENTICATION", bg="#F0FDF4", border="#86EFAC", text_color="#166534")

    draw_msg(130, 830, 2275, "(38) Legit user responds to alert → completes mandatory 2FA TOTP verification", color="#059669")
    draw_msg(830, 1310, 2305, "(39) Unlock DB account record & generate fresh credential pair with updated baseline", color="#475569")

    output_path = os.path.join(out_dir, "fig_full_project_sequence.png")
    img.save(output_path, "PNG", dpi=(300, 300))
    print("Successfully generated full project sequence diagram at:", output_path)

if __name__ == "__main__":
    create_full_sequence_diagram()
