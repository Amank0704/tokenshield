import os
from PIL import Image, ImageDraw, ImageFont

out_dir = "/Users/yashpachhade/tokenshield/diagrams"
os.makedirs(out_dir, exist_ok=True)

font_path_regular = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
font_path_bold = "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"
font_path_italic = "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf"
font_path_arial = "/System/Library/Fonts/Supplemental/Arial.ttf"
font_path_arial_bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

def get_font(font_type="arial", size=13):
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

def create_compact_sequence():
    # Width and height: compact, clean, highly readable
    width, height = 1260, 1380
    # Soft, ultra-light off-white background
    img = Image.new("RGB", (width, height), "#FAFAFA")
    draw = ImageDraw.Draw(img)

    f_title = get_font("arial_bold", 19)
    f_sub = get_font("arial", 13)
    f_header = get_font("arial_bold", 13)
    f_msg = get_font("arial_bold", 11)
    f_msg_reg = get_font("arial", 11)
    f_note = get_font("italic", 11)
    f_phase = get_font("arial_bold", 12)
    f_badge = get_font("arial_bold", 10)

    # Document Title
    draw.text((width // 2, 35), "TokenShield: End-to-End System Sequence Diagram", fill="#0F172A", font=f_title, anchor="mm")
    draw.text((width // 2, 60), "Authentication  •  Continuous 7-Signal Scoring  •  8-Stage Mitigation  •  Perimeter Enforcement", fill="#64748B", font=f_sub, anchor="mm")

    # Participants (Clean 5 main lifelines for clarity)
    participants = [
        ("Legit User", 120, "#2563EB", "#EFF6FF", "#BFDBFE"),
        ("Attacker", 340, "#DC2626", "#FEF2F2", "#FECACA"),
        ("Nginx (Edge)", 580, "#0D9488", "#F0FDFA", "#99F6E4"),
        ("TokenShield Engine", 830, "#1E3A8A", "#F1F5F9", "#CBD5E1"),
        ("Redis (Cache)", 1040, "#B91C1C", "#FFF1F2", "#FECDD3"),
        ("DB / Dashboard", 1180, "#475569", "#F8FAFC", "#E2E8F0")
    ]

    top_y = 100
    bottom_y = 1320

    # Draw Lifelines (subtle dashed vertical lines)
    for name, x, color, fill_c, border_c in participants:
        for y in range(top_y + 26, bottom_y, 14):
            draw.line([(x, y), (x, y + 7)], fill="#CBD5E1", width=2)

    # Participant Boxes (Top and Bottom)
    for name, x, color, fill_c, border_c in participants:
        for py in [top_y, bottom_y]:
            w_box = 100 if "Engine" not in name else 125
            h_box = 36
            draw.rounded_rectangle([x - w_box//2, py - h_box//2, x + w_box//2, py + h_box//2], radius=5, fill=fill_c, outline=border_c, width=1)
            draw.text((x, py), name, fill=color, font=f_header, anchor="mm")

    # Helper: draw message arrow
    def draw_msg(x1, x2, y, text, color="#1E40AF", dashed=False, bold=True, badge=""):
        if dashed:
            dist = abs(x2 - x1)
            steps = max(int(dist / 9), 1)
            for i in range(steps):
                if i % 2 == 0:
                    sx = x1 + (x2 - x1) * (i / steps)
                    ex = x1 + (x2 - x1) * ((i + 1) / steps)
                    draw.line([(sx, y), (ex, y)], fill=color, width=2)
        else:
            draw.line([(x1, y), (x2, y)], fill=color, width=2)

        direction = 1 if x2 > x1 else -1
        draw.polygon([(x2, y), (x2 - 8 * direction, y - 4), (x2 - 8 * direction, y + 4)], fill=color)

        mid_x = (x1 + x2) / 2
        f_use = f_msg if bold else f_msg_reg
        draw.text((mid_x, y - 9), text, fill=color, font=f_use, anchor="mb")

        if badge:
            badge_w = len(badge) * 6 + 10
            draw.rounded_rectangle([mid_x - badge_w//2, y + 2, mid_x + badge_w//2, y + 17], radius=3, fill="#F8FAFC", outline="#CBD5E1", width=1)
            draw.text((mid_x, y + 9), badge, fill="#475569", font=f_badge, anchor="mm")

    # Helper: Self note
    def draw_self(x, y, text, color="#1E40AF", side="right", sub=""):
        offset = 26 if side == "right" else -26
        draw.line([(x, y - 8), (x + offset, y - 8)], fill=color, width=2)
        draw.line([(x + offset, y - 8), (x + offset, y + 8)], fill=color, width=2)
        draw.line([(x + offset, y + 8), (x, y + 8)], fill=color, width=2)
        direction = -1 if side == "right" else 1
        draw.polygon([(x, y + 8), (x - 6 * direction, y + 5), (x - 6 * direction, y + 11)], fill=color)

        anchor = "lm" if side == "right" else "rm"
        text_x = x + offset + (8 if side == "right" else -8)
        draw.text((text_x, y - (4 if sub else 0)), text, fill=color, font=f_msg, anchor=anchor)
        if sub:
            draw.text((text_x, y + 10), sub, fill="#64748B", font=f_note, anchor=anchor)

    # Helper: Light Phase Banner
    def draw_banner(y, title, bg="#F1F5F9", border="#E2E8F0", text_c="#334155"):
        draw.rounded_rectangle([50, y - 12, width - 50, y + 12], radius=4, fill=bg, outline=border, width=1)
        draw.text((65, y), title, fill=text_c, font=f_phase, anchor="lm")

    # 1. AUTHENTICATION & BASELINE
    draw_banner(148, "1. AUTHENTICATION & BASELINE REGISTRATION", bg="#F0F9FF", border="#BAE6FD", text_c="#0369A1")
    draw_msg(120, 830, 185, "(1) POST /api/auth/login (User-Agent, Device FP, Telemetry)", color="#0284C7")
    draw_msg(830, 1040, 225, "(2) Issue JWT & register session baseline in Redis (ts:fp, ts:geo)", color="#B91C1C", badge="TTL 24h")
    draw_msg(830, 120, 265, "(3) Return HTTP 200 OK + JWT Bearer Token", color="#059669", dashed=True)

    # 2. BENIGN CONTINUOUS SCORING
    draw_banner(305, "2. NORMAL USER ACCESS & 7-SIGNAL SCORING (SAFE TIER)", bg="#F0FDF4", border="#BBF7D0", text_c="#15803D")
    draw_msg(120, 580, 342, "(4) GET /api/banking/dashboard (w/ Bearer JWT & telemetry)", color="#16A34A")
    draw_msg(580, 830, 380, "(5) Nginx proxy_pass → Flask before_request hook", color="#16A34A")
    draw_self(830, 420, "(6) Evaluate 7 signals: IP, UA, Geo, Biometrics", color="#1E40AF", sub="Score S = 0.08 < 0.30 (Safe)")
    draw_msg(830, 120, 465, "(7) Return HTTP 200 OK with banking dashboard data", color="#16A34A", dashed=True)

    # 3. TOKEN THEFT & REPLAY
    draw_banner(508, "3. TOKEN THEFT EXFILTRATION & MALICIOUS REPLAY", bg="#FEF2F2", border="#FECACA", text_c="#B91C1C")
    draw_self(340, 545, "(8) Adversary steals valid JWT", color="#DC2626", side="left", sub="via XSS / MITM interception")
    draw_msg(340, 580, 590, "(9) POST /api/banking/transfer w/ stolen JWT (Tor IP, spoofed UA)", color="#DC2626", dashed=True)
    draw_msg(580, 830, 630, "(10) Forward packet to TokenShield before_request engine", color="#DC2626")

    # 4. CRITICAL THREAT SCORING
    draw_banner(672, "4. REAL-TIME THREAT SCORING & ANOMALY TRIGGER", bg="#FFF7ED", border="#FED7AA", text_c="#C2410C")
    draw_msg(830, 1040, 710, "(11) Redis lookup: sliding-window velocity & origin IP comparison", color="#B91C1C")
    draw_self(830, 755, "(12) Seven-Signal Critical Path Scoring:", color="#EA580C", 
              sub="IP drift (+0.20) + Geo >900km/h (+0.35) + Vel (+0.30) → Score S = 0.94 ≥ 0.85 [CRITICAL]")

    # 5. EIGHT-STAGE PROGRESSIVE MITIGATION
    draw_banner(810, "5. EIGHT-STAGE PROGRESSIVE MITIGATION CASCADE", bg="#FEF2F2", border="#FCA5A5", text_c="#991B1B")
    draw_msg(830, 1040, 848, "(13) Stage 1 & 2: Redis token revocation & IP ban", color="#B91C1C", badge="~0 ms")
    draw_msg(830, 580, 890, "(14) Stage 3: Write offending IP to Nginx dynamic blocklist", color="#0D9488", badge="reload ≤ 5s")
    draw_msg(830, 1040, 930, "(15) Stage 4: Ban rogue device fingerprint (TTL 72h)", color="#B91C1C", badge="~0 ms")
    draw_msg(830, 1180, 970, "(16) Stage 5: DB Account 2FA lockout & correlation check", color="#475569", badge="~10 ms")
    draw_msg(830, 1180, 1010, "(17) Stage 7 & 8: SMTP email alert & SSE dashboard broadcast", color="#D97706", badge="async")

    # 6. TRANSACTION ABORT & ACTIVE ENFORCEMENT
    draw_banner(1052, "6. INSTANT ATTACK TERMINATION & EDGE ENFORCEMENT", bg="#F8FAFC", border="#E2E8F0", text_c="#1E293B")
    draw_msg(830, 340, 1090, "(18) Abort malicious transfer: HTTP 401 Unauthorized", color="#DC2626", bold=True, dashed=True)
    draw_msg(340, 580, 1130, "(19) Attacker retries request with same token & IP", color="#DC2626", dashed=True)
    draw_msg(580, 340, 1170, "(20) Edge blocked: HTTP 403 Forbidden (Nginx blocklist, 0.8 ms)", color="#DC2626", bold=True)

    # 7. USER STEP-UP 2FA RECOVERY
    draw_banner(1212, "7. LEGITIMATE USER 2FA STEP-UP & RECOVERY", bg="#F0FDF4", border="#BBF7D0", text_c="#15803D")
    draw_msg(120, 830, 1250, "(21) User completes Step-Up 2FA TOTP verification", color="#16A34A")
    draw_msg(830, 1180, 1285, "(22) Unlock DB account & issue new secure JWT session", color="#475569")

    out_file = os.path.join(out_dir, "fig_full_project_sequence_compact.png")
    img.save(out_file, "PNG", dpi=(300, 300))
    print("Saved compact light sequence diagram at:", out_file)

if __name__ == "__main__":
    create_compact_sequence()
