import re

with open("generate_master_diagram.py", "r") as f:
    code = f.read()

# Replace Tier V rendering logic
old_tier5 = """# Tier V: Persistence & In-Memory Store
draw_card(60, 1340, 760, 1670, bg="#141124", border="#9333EA", radius=10, width=2)
draw.text((80, 1365), "TIER V: HIGH-SPEED STATE & PERSISTENCE", fill="#C084FC", font=f_box_title, anchor="lm")

db_items = [
    ("REDIS 7 IN-MEMORY CACHE (:6379)", "172.20.0.4 • Low-Latency Sub-ms State Store"),
    ("• ts:block:<token_hash>", "Instant O(1) Session Revocation Blacklist (~0ms)"),
    ("• ts:vel:<ip>", "60-Second Sliding-Window Request Velocity Counters"),
    ("• ts:fp:<fp_hash>", "Device Hardware Fingerprint Ban (TTL 72 Hours)"),
    ("• ts:geo:<session>", "Last Known IP Coordinate & Timestamp for Velocity"),
    ("SQLITE DATABASE (tokenshield.db)", "Relational Store via SQLAlchemy ORM"),
    ("• Users & Auth Ledger", "Credentials (Bcrypt), TOTP Keys, Account Status"),
    ("• Core Banking Ledger", "Accounts, Balances, Cards, Real-time Transactions"),
    ("• Incident & Audit Trail", "Granular Forensic Logs, Threat Scores & Timelines"),
]
for i, (d_title, d_desc) in enumerate(db_items):
    dy = 1395 + i * 29
    color = "#F3E8FF" if "•" not in d_title else "#C084FC"
    draw.text((85, dy), d_title, fill=color, font=f_item_title, anchor="lm")
    draw.text((290, dy), d_desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")"""

new_tier5 = """# Tier V: Persistence & In-Memory Store
draw_card(60, 1340, 780, 1670, bg="#141124", border="#9333EA", radius=10, width=2)
draw.text((80, 1365), "TIER V: HIGH-SPEED STATE & PERSISTENCE", fill="#C084FC", font=f_box_title, anchor="lm")

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
    dy = 1395 + i * 29
    if is_hdr:
        draw_card(75, dy - 12, 765, dy + 14, bg="#201538", border="#6B21A8", radius=4, width=1)
        draw.text((85, dy + 1), d_title, fill="#E9D5FF", font=f_item_title, anchor="lm")
        draw.text((410, dy + 1), d_desc, fill="#C084FC", font=f_item_desc, anchor="lm")
    else:
        draw.text((85, dy), d_title, fill="#D8B4FE", font=f_item_title, anchor="lm")
        draw.text((310, dy), d_desc, fill="#E2E8F0", font=f_item_desc, anchor="lm")"""

code = code.replace(old_tier5, new_tier5)

# Adjust tier 6 left bound
code = code.replace("draw_card(790, 1340, 1610, 1670", "draw_card(805, 1340, 1615, 1670")
code = code.replace("draw.text((810, 1365)", "draw.text((825, 1365)")
code = code.replace("draw_card(810, my - 12, 1590", "draw_card(820, my - 12, 1600")
code = code.replace("draw.text((820, my + 2)", "draw.text((830, my + 2)")
code = code.replace("draw_pill(1140,", "draw_pill(1150,")
code = code.replace("draw.text((1225, my + 2)", "draw.text((1235, my + 2)")

with open("generate_master_diagram.py", "w") as f:
    f.write(code)

print("Updated script written.")
