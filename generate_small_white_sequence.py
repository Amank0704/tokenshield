import os
from PIL import Image, ImageDraw, ImageFont

out_dir = "/Users/yashpachhade/tokenshield/diagrams"
os.makedirs(out_dir, exist_ok=True)

font_path_regular = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
font_path_bold = "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"
font_path_italic = "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf"
font_path_arial = "/System/Library/Fonts/Supplemental/Arial.ttf"
font_path_arial_bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

def get_font(font_type="arial", size=11):
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

def create_small_white_sequence():
    # Pure white background, compact dimensions (fits easily anywhere)
    width, height = 1000, 920
    img = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    f_title = get_font("arial_bold", 15)
    f_sub = get_font("arial", 11)
    f_header = get_font("arial_bold", 11)
    f_msg = get_font("arial_bold", 10)
    f_msg_reg = get_font("arial", 10)
    f_note = get_font("italic", 9)
    f_badge = get_font("arial_bold", 9)

    # Title & Subtitle
    draw.text((width // 2, 24), "TokenShield: End-to-End System Sequence Flow", fill="#0F172A", font=f_title, anchor="mm")
    draw.text((width // 2, 44), "Authentication  •  7-Signal Anomaly Scoring  •  Automated Mitigation  •  Edge Blocking", fill="#64748B", font=f_sub, anchor="mm")

    # 6 Actors
    participants = [
        ("User", 90),
        ("Attacker", 240),
        ("Nginx", 420),
        ("Engine", 610),
        ("Redis", 790),
        ("DB / Dash", 920)
    ]

    top_y = 80
    bottom_y = 880

    # Draw Lifelines (thin dashed lines)
    for name, x in participants:
        for y in range(top_y + 18, bottom_y - 10, 12):
            draw.line([(x, y), (x, y + 6)], fill="#CBD5E1", width=1)

    # Participant Boxes (Top & Bottom)
    for name, x in participants:
        for py in [top_y, bottom_y]:
            w_b = 80 if name != "Engine" else 95
            h_b = 26
            draw.rounded_rectangle([x - w_b//2, py - h_b//2, x + w_b//2, py + h_b//2], radius=4, fill="#F8FAFC", outline="#94A3B8", width=1)
            draw.text((x, py), name, fill="#1E293B", font=f_header, anchor="mm")

    # Helper: draw message arrow
    def draw_msg(x1, x2, y, text, color="#1D4ED8", dashed=False, bold=False, badge=""):
        if dashed:
            dist = abs(x2 - x1)
            steps = max(int(dist / 8), 1)
            for i in range(steps):
                if i % 2 == 0:
                    sx = x1 + (x2 - x1) * (i / steps)
                    ex = x1 + (x2 - x1) * ((i + 1) / steps)
                    draw.line([(sx, y), (ex, y)], fill=color, width=1)
        else:
            draw.line([(x1, y), (x2, y)], fill=color, width=1)

        direction = 1 if x2 > x1 else -1
        draw.polygon([(x2, y), (x2 - 7 * direction, y - 3), (x2 - 7 * direction, y + 3)], fill=color)

        mid_x = (x1 + x2) / 2
        f_use = f_msg if bold else f_msg_reg
        draw.text((mid_x, y - 7), text, fill=color, font=f_use, anchor="mb")

        if badge:
            badge_w = len(badge) * 5 + 8
            draw.rounded_rectangle([mid_x - badge_w//2, y + 2, mid_x + badge_w//2, y + 14], radius=2, fill="#FFFFFF", outline="#CBD5E1", width=1)
            draw.text((mid_x, y + 8), badge, fill="#475569", font=f_badge, anchor="mm")

    # Helper: Self note
    def draw_self(x, y, text, color="#1D4ED8", side="right", sub=""):
        offset = 20 if side == "right" else -20
        draw.line([(x, y - 6), (x + offset, y - 6)], fill=color, width=1)
        draw.line([(x + offset, y - 6), (x + offset, y + 6)], fill=color, width=1)
        draw.line([(x + offset, y + 6), (x, y + 6)], fill=color, width=1)
        direction = -1 if side == "right" else 1
        draw.polygon([(x, y + 6), (x - 5 * direction, y + 3), (x - 5 * direction, y + 9)], fill=color)

        anchor = "lm" if side == "right" else "rm"
        text_x = x + offset + (6 if side == "right" else -6)
        draw.text((text_x, y - (3 if sub else 0)), text, fill=color, font=f_msg, anchor=anchor)
        if sub:
            draw.text((text_x, y + 8), sub, fill="#64748B", font=f_note, anchor=anchor)

    # 1. Login & Baseline
    draw_msg(90, 610, 125, "(1) POST /login (telemetry & device FP)", color="#2563EB")
    draw_msg(610, 790, 165, "(2) Issue JWT & save baseline in Redis (ts:fp, ts:geo)", color="#B91C1C", badge="TTL 24h")
    draw_msg(610, 90, 205, "(3) HTTP 200 OK + JWT Bearer Token", color="#059669", dashed=True)

    # 2. Normal Safe Request
    draw_msg(90, 420, 250, "(4) GET /dashboard (JWT + cadence)", color="#059669")
    draw_msg(420, 610, 285, "(5) proxy_pass", color="#059669")
    draw_self(610, 320, "(6) Score 7 signals: S = 0.08 < 0.30 (Safe)", color="#166534")
    draw_msg(610, 90, 360, "(7) HTTP 200 OK (Dashboard Data)", color="#059669", dashed=True)

    # 3. Token Theft & Critical Scoring
    draw_self(240, 400, "(8) Steals JWT (XSS/MITM)", color="#DC2626", side="left")
    draw_msg(240, 420, 440, "(9) POST /transfer w/ stolen JWT (Tor IP)", color="#DC2626", dashed=True)
    draw_msg(420, 610, 475, "(10) proxy_pass to Engine", color="#DC2626")
    draw_self(610, 515, "(11) Score 7 signals: IP drift + Geo-jump + Velocity", color="#EA580C", 
              sub="Score S = 0.94 ≥ 0.85 → CRITICAL THREAT")

    # 4. Mitigation Cascade (8 Stages compressed cleanly)
    draw_msg(610, 790, 560, "(12) Stage 1 & 2: Revoke token & IP ban (ts:block:*)", color="#B91C1C", badge="~0 ms")
    draw_msg(610, 420, 600, "(13) Stage 3: Write to dynamic blocklist file", color="#0D9488", badge="reload ≤ 5s")
    draw_msg(610, 790, 640, "(14) Stage 4: Ban device fingerprint [ts:fp]", color="#B91C1C", badge="~0 ms")
    draw_msg(610, 920, 680, "(15) Stage 5-8: Lock DB 2FA + SSE alert + SMTP email", color="#475569", badge="~10 ms / async")

    # 5. Attack Termination & Edge Blocking
    draw_msg(610, 240, 725, "(16) Abort transaction: 401 Unauthorized", color="#DC2626", bold=True, dashed=True)
    draw_msg(240, 420, 765, "(17) Attacker retries identical request", color="#DC2626", dashed=True)
    draw_msg(420, 240, 800, "(18) Edge blocked: 403 Forbidden (Nginx blocklist in 0.8 ms)", color="#DC2626", bold=True)

    # 6. User 2FA Step-up Recovery
    draw_msg(90, 610, 840, "(19) User completes Step-Up 2FA verification → unlock account", color="#059669")

    out_file = os.path.join(out_dir, "fig_full_project_sequence_small.png")
    img.save(out_file, "PNG", dpi=(300, 300))
    print("Saved small white sequence diagram at:", out_file)

if __name__ == "__main__":
    create_small_white_sequence()
