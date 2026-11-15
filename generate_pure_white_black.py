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

def create_pure_white_black_ink():
    # Crisp, pure white background with black lines and black text
    width, height = 960, 840
    # Solid RGB White (255, 255, 255)
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font("arial_bold", 15)
    f_sub = get_font("arial", 11)
    f_header = get_font("arial_bold", 11)
    f_msg = get_font("arial_bold", 10)
    f_msg_reg = get_font("arial", 10)
    f_note = get_font("italic", 9)
    f_badge = get_font("arial_bold", 9)

    # Title & Subtitle in solid black
    draw.text((width // 2, 22), "TokenShield: Complete Request Lifecycle & Mitigation Sequence", fill="#000000", font=f_title, anchor="mm")
    draw.text((width // 2, 42), "Authentication  •  Continuous 7-Signal Scoring  •  8-Stage Mitigation  •  Edge Enforcement", fill="#333333", font=f_sub, anchor="mm")

    # 6 Actors across top
    participants = [
        ("User", 85),
        ("Attacker", 230),
        ("Nginx", 400),
        ("Engine", 580),
        ("Redis", 760),
        ("DB / Dash", 885)
    ]

    top_y = 75
    bottom_y = 805

    # Draw Lifelines (subtle black/gray dashed lines)
    for name, x in participants:
        for y in range(top_y + 18, bottom_y - 10, 10):
            draw.line([(x, y), (x, y + 5)], fill="#777777", width=1)

    # Participant Boxes (White fill with solid black border & black text)
    for name, x in participants:
        for py in [top_y, bottom_y]:
            w_b = 75 if name != "Engine" else 90
            h_b = 26
            draw.rounded_rectangle([x - w_b//2, py - h_b//2, x + w_b//2, py + h_b//2], radius=3, fill="#FFFFFF", outline="#000000", width=1)
            draw.text((x, py), name, fill="#000000", font=f_header, anchor="mm")

    # Helper: draw message arrow in solid black
    def draw_msg(x1, x2, y, text, dashed=False, bold=False, badge=""):
        color = "#000000"
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
        draw.text((mid_x, y - 7), text, fill="#000000", font=f_use, anchor="mb")

        if badge:
            badge_w = len(badge) * 5 + 8
            draw.rounded_rectangle([mid_x - badge_w//2, y + 2, mid_x + badge_w//2, y + 14], radius=2, fill="#FFFFFF", outline="#555555", width=1)
            draw.text((mid_x, y + 8), badge, fill="#000000", font=f_badge, anchor="mm")

    # Helper: Self note in black
    def draw_self(x, y, text, side="right", sub=""):
        color = "#000000"
        offset = 18 if side == "right" else -18
        draw.line([(x, y - 5), (x + offset, y - 5)], fill=color, width=1)
        draw.line([(x + offset, y - 5), (x + offset, y + 5)], fill=color, width=1)
        draw.line([(x + offset, y + 5), (x, y + 5)], fill=color, width=1)
        direction = -1 if side == "right" else 1
        draw.polygon([(x, y + 5), (x - 5 * direction, y + 2), (x - 5 * direction, y + 8)], fill=color)

        anchor = "lm" if side == "right" else "rm"
        text_x = x + offset + (6 if side == "right" else -6)
        draw.text((text_x, y - (3 if sub else 0)), text, fill="#000000", font=f_msg, anchor=anchor)
        if sub:
            draw.text((text_x, y + 8), sub, fill="#444444", font=f_note, anchor=anchor)

    # 1. Login & Baseline
    draw_msg(85, 580, 115, "(1) POST /login (telemetry & device FP)")
    draw_msg(580, 760, 150, "(2) Issue JWT & register baseline in Redis (ts:fp, ts:geo)", badge="TTL 24h")
    draw_msg(580, 85, 185, "(3) HTTP 200 OK + JWT Bearer Token", dashed=True)

    # 2. Normal Safe Request
    draw_msg(85, 400, 225, "(4) GET /dashboard (JWT + normal cadence)")
    draw_msg(400, 580, 255, "(5) proxy_pass")
    draw_self(580, 288, "(6) Score 7 signals: S = 0.08 < 0.30 (Safe)")
    draw_msg(580, 85, 325, "(7) HTTP 200 OK (Dashboard Data)", dashed=True)

    # 3. Token Theft & Critical Scoring
    draw_self(230, 360, "(8) Steals JWT (XSS/MITM)", side="left")
    draw_msg(230, 400, 395, "(9) POST /transfer w/ stolen JWT (Tor IP)", dashed=True)
    draw_msg(400, 580, 428, "(10) proxy_pass to Engine")
    draw_self(580, 465, "(11) Score 7 signals: IP drift + Geo-jump + Velocity", 
              sub="Score S = 0.94 ≥ 0.85 → CRITICAL THREAT")

    # 4. Mitigation Cascade (8 Stages)
    draw_msg(580, 760, 508, "(12) Stage 1 & 2: Revoke token & ban IP (ts:block:*)", badge="~0 ms")
    draw_msg(580, 400, 545, "(13) Stage 3: Write to dynamic blocklist file", badge="reload ≤ 5s")
    draw_msg(580, 760, 582, "(14) Stage 4: Ban device fingerprint [ts:fp]", badge="~0 ms")
    draw_msg(580, 885, 618, "(15) Stage 5-8: Lock DB 2FA + SSE alert + SMTP email", badge="~10 ms / async")

    # 5. Attack Termination & Edge Blocking
    draw_msg(580, 230, 660, "(16) Abort transaction: 401 Unauthorized", bold=True, dashed=True)
    draw_msg(230, 400, 698, "(17) Attacker retries request", dashed=True)
    draw_msg(400, 230, 730, "(18) Edge blocked: 403 Forbidden (Nginx blocklist, 0.8 ms)", bold=True)

    # 6. User 2FA Step-up Recovery
    draw_msg(85, 580, 768, "(19) User completes Step-Up 2FA verification → unlock account")

    out_file = os.path.join(out_dir, "fig_sequence_pure_white.png")
    img.save(out_file, "PNG", dpi=(300, 300))
    print("Saved pure white diagram at:", out_file)

if __name__ == "__main__":
    create_pure_white_black_ink()
