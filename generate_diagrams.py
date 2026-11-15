import os
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

# ---------------------------------------------------------
# FIGURE 1: Container-Level System Architecture
# ---------------------------------------------------------
def create_fig1():
    width, height = 1200, 680
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    f_title = get_font("arial_bold", 18)
    f_sub = get_font("arial", 15)
    f_label = get_font("arial_bold", 13)

    def draw_box(x1, y1, x2, y2, bg_color, border_color="#111111", radius=8, width_b=2):
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=bg_color, outline=border_color, width=width_b)

    draw_box(80, 40, 520, 130, "#F2F4F7", "#2C3E50")
    draw.text((300, 68), "Client Applications", fill="#1A252C", font=f_title, anchor="mm")
    draw.text((300, 102), "Web / Mobile / API", fill="#4A5568", font=f_sub, anchor="mm")

    draw_box(680, 40, 1120, 130, "#F2F4F7", "#2C3E50")
    draw.text((900, 68), "Red-Team / Test Traffic", fill="#1A252C", font=f_title, anchor="mm")
    draw.text((900, 102), "Load harness, scanner", fill="#4A5568", font=f_sub, anchor="mm")

    draw_box(80, 220, 520, 310, "#FAFAFA", "#2C3E50")
    draw.text((300, 248), "Edge Reverse Proxy (Nginx)", fill="#1A252C", font=f_title, anchor="mm")
    draw.text((300, 280), "rate-limit zones  •  dynamic blocklist", fill="#4A5568", font=f_sub, anchor="mm")

    draw_box(80, 390, 1120, 480, "#F0F4F8", "#1E3A8A", radius=10, width_b=3)
    draw.text((600, 418), "TokenShield Detection Engine (Flask)", fill="#0F172A", font=get_font("arial_bold", 20), anchor="mm")
    draw.text((600, 452), "before_request hook  •  7-signal scoring", fill="#1E40AF", font=f_sub, anchor="mm")

    draw_box(80, 560, 520, 640, "#F2F4F7", "#2C3E50")
    draw.text((300, 585), "In-Memory State (Redis)", fill="#1A252C", font=f_title, anchor="mm")
    draw.text((300, 615), "O(1) blocklists  •  velocity  •  geo", fill="#4A5568", font=f_sub, anchor="mm")

    draw_box(680, 560, 1120, 640, "#F2F4F7", "#2C3E50")
    draw.text((900, 585), "Relational Store", fill="#1A252C", font=f_title, anchor="mm")
    draw.text((900, 615), "Users  •  Sessions  •  Behavior", fill="#4A5568", font=f_sub, anchor="mm")

    def draw_arrow(x1, y1, x2, y2, color="#10B981", width_l=3, style="solid"):
        if style == "dashed":
            dist = ((x2-x1)**2 + (y2-y1)**2)**0.5
            dashes = int(dist / 12)
            for i in range(dashes):
                if i % 2 == 0:
                    sx = x1 + (x2-x1) * (i / dashes)
                    sy = y1 + (y2-y1) * (i / dashes)
                    ex = x1 + (x2-x1) * ((i+1) / dashes)
                    ey = y1 + (y2-y1) * ((i+1) / dashes)
                    draw.line([sx, sy, ex, ey], fill=color, width=width_l)
        else:
            draw.line([x1, y1, x2, y2], fill=color, width=width_l)

        import math
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_len = 12
        p1 = (x2 - arrow_len * math.cos(angle - math.pi / 6), y2 - arrow_len * math.sin(angle - math.pi / 6))
        p2 = (x2 - arrow_len * math.cos(angle + math.pi / 6), y2 - arrow_len * math.sin(angle + math.pi / 6))
        draw.polygon([p1, (x2, y2), p2], fill=color)

    draw_arrow(300, 130, 300, 220, color="#059669", width_l=3)
    draw_arrow(300, 310, 300, 390, color="#059669", width_l=3)
    draw.text((315, 350), "proxy_pass", fill="#047857", font=f_label, anchor="ls")

    draw_arrow(900, 130, 900, 390, color="#DC2626", width_l=3, style="dashed")
    draw.text((915, 260), "direct evaluation", fill="#B91C1C", font=f_label, anchor="ls")

    draw_arrow(300, 480, 300, 560, color="#334155", width_l=3)
    draw_arrow(300, 560, 300, 480, color="#334155", width_l=3)

    draw_arrow(900, 480, 900, 560, color="#334155", width_l=3)
    draw_arrow(900, 560, 900, 480, color="#334155", width_l=3)

    draw_arrow(80, 600, 30, 600, color="#475569", width_l=2, style="dashed")
    draw_arrow(30, 600, 30, 265, color="#475569", width_l=2, style="dashed")
    draw_arrow(30, 265, 80, 265, color="#475569", width_l=2, style="dashed")
    draw.text((25, 430), "blocklist push\n≤ 5 s reload", fill="#334155", font=get_font("arial_bold", 12), anchor="rm")

    img.save(os.path.join(out_dir, "fig1_architecture.png"), "PNG", dpi=(300, 300))

# ---------------------------------------------------------
# FIGURE 2: Eight-Stage Progressive Mitigation Pipeline
# ---------------------------------------------------------
def create_fig2():
    width, height = 1100, 680
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    f_head = get_font("arial_bold", 17)
    f_step = get_font("arial_bold", 14)
    f_time = get_font("arial", 13)

    draw.rounded_rectangle([150, 25, 950, 80], radius=8, fill="#FEE2E2", outline="#DC2626", width=2)
    draw.text((550, 52), "Anomaly Score S ≥ 0.85 (Critical Threshold)", fill="#991B1B", font=f_head, anchor="mm")

    steps = [
        ("1. Redis token revocation", "~0 ms"),
        ("2. Redis IP block (TTL 24 h)", "~0 ms"),
        ("3. Nginx edge block", "≤ 5 s reload"),
        ("4. Device fingerprint ban (TTL 72 h)", "~0 ms"),
        ("5. Account 2FA lockout (DB)", "~10 ms"),
        ("6. Coordinated-attack correlation", "~10 ms"),
        ("7. SMTP security alert", "async"),
        ("8. Live dashboard SSE push", "async"),
    ]

    def draw_arrow_down(x, y1, y2, color="#334155"):
        draw.line([x, y1, x, y2], fill=color, width=2)
        draw.polygon([(x-5, y2-7), (x, y2), (x+5, y2-7)], fill=color)

    draw_arrow_down(550, 80, 105)

    y_start = 105
    box_height = 44
    gap = 20

    for i, (text, time_str) in enumerate(steps):
        curr_y = y_start + i * (box_height + gap)
        draw.rounded_rectangle([180, curr_y, 750, curr_y + box_height], radius=6, fill="#EFF6FF", outline="#3B82F6", width=2)
        draw.text((210, curr_y + box_height/2), text, fill="#1E3A8A", font=f_step, anchor="lm")

        draw.rounded_rectangle([780, curr_y + 4, 920, curr_y + box_height - 4], radius=4, fill="#F1F5F9", outline="#94A3B8", width=1)
        draw.text((850, curr_y + box_height/2), time_str, fill="#475569", font=f_time, anchor="mm")

        if i < len(steps) - 1:
            draw_arrow_down(465, curr_y + box_height, curr_y + box_height + gap)

    img.save(os.path.join(out_dir, "fig2_mitigation.png"), "PNG", dpi=(300, 300))

# ---------------------------------------------------------
# FIGURE 3: Packet-Level Sequence for Token-Theft Incident
# ---------------------------------------------------------
def create_fig3():
    width, height = 1200, 680
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    f_title = get_font("arial_bold", 15)
    f_msg = get_font("arial", 13)
    f_note = get_font("italic", 13)

    nodes = [
        ("Attacker", 120),
        ("Nginx", 360),
        ("Engine", 600),
        ("Redis", 840),
        ("DB / Dash", 1080)
    ]

    for name, x in nodes:
        draw.rounded_rectangle([x - 65, 30, x + 65, 75], radius=6, fill="#E2E8F0", outline="#475569", width=2)
        draw.text((x, 52), name, fill="#0F172A", font=f_title, anchor="mm")

        for y in range(80, 640, 14):
            draw.line([x, y, x, y + 7], fill="#94A3B8", width=2)

    def draw_msg(x1, x2, y, text, color="#1D4ED8", dashed=False, bold=False):
        if dashed:
            dist = abs(x2 - x1)
            dashes = int(dist / 10)
            for i in range(dashes):
                if i % 2 == 0:
                    sx = x1 + (x2 - x1) * (i / dashes)
                    ex = x1 + (x2 - x1) * ((i + 1) / dashes)
                    draw.line([sx, y, ex, y], fill=color, width=2)
        else:
            draw.line([x1, y, x2, y], fill=color, width=2 if not bold else 3)

        direction = 1 if x2 > x1 else -1
        draw.polygon([(x2, y), (x2 - 10 * direction, y - 5), (x2 - 10 * direction, y + 5)], fill=color)

        mid_x = (x1 + x2) / 2
        f_use = get_font("arial_bold", 13) if bold else f_msg
        draw.text((mid_x, y - 11), text, fill=color, font=f_use, anchor="mb")

    draw_msg(120, 360, 125, "(1) GET w/ stolen JWT", color="#1E40AF")
    draw_msg(360, 600, 185, "(2) proxy_pass", color="#1E40AF")
    draw.text((615, 240), "(3) score 7 signals", fill="#1E40AF", font=f_note, anchor="lm")
    draw_msg(600, 840, 300, "(4) SET S=0.91, ts:block", color="#1E40AF")
    draw_msg(600, 360, 365, "(5) write blocklist", color="#1E40AF")
    draw.text((350, 390), "reload ≤ 5s", fill="#475569", font=f_note, anchor="rm")
    draw_msg(600, 1080, 445, "(6) DB 2FA lock + SSE push", color="#1E40AF")
    draw_msg(120, 360, 520, "(7) replay identical JWT", color="#B91C1C", dashed=True)
    draw.text((375, 555), "(8) edge-blocked", fill="#B91C1C", font=f_note, anchor="lm")
    draw_msg(360, 120, 605, "(9) 401 Unauthorized", color="#B91C1C", bold=True)

    img.save(os.path.join(out_dir, "fig3_sequence.png"), "PNG", dpi=(300, 300))

if __name__ == "__main__":
    create_fig1()
    create_fig2()
    create_fig3()
    print("All compact diagrams generated successfully in:", out_dir)
