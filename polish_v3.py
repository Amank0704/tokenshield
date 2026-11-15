with open("generate_perfect_diagram_v2.py", "r") as f:
    text = f.read()

# Expand canvas slightly for right margin label breathing room
text = text.replace("W, H = 2750, 2100", "W, H = 2850, 2100")
text = text.replace("label_pos=(X_RIGHT + 40, 900)", "label_pos=(X_RIGHT + 60, 900)")

with open("generate_perfect_diagram_v2.py", "w") as f:
    f.write(text)

