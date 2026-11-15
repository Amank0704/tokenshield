#!/usr/bin/env python3
"""
TokenShield Project & Node Structure Visualizer
Usage:
    python3 show_tree.py          (Clean high-level architecture tree)
    python3 show_tree.py --depth 3 (Deeper view)
    python3 show_tree.py engine   (Inspect engine node)
    python3 show_tree.py app      (Inspect NeoVault app node)
"""

import os
import sys

# ANSI Colors
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
RESET = "\033[0m"

SKIP_DIRS = {
    ".git", "venv", "__pycache__", ".pytest_cache",
    "node_modules", ".idea", ".vscode", ".DS_Store"
}

def print_tree(dir_path, prefix="", max_depth=2, current_depth=0):
    if current_depth > max_depth:
        return

    try:
        entries = sorted([e for e in os.listdir(dir_path) if e not in SKIP_DIRS and not e.startswith(".")])
    except PermissionError:
        return

    # Filter out bulky docx files or raw dumps if at root
    if current_depth == 0:
        entries = [e for e in entries if not (e.endswith(".docx") or e.endswith(".csv"))]

    for i, entry in enumerate(entries):
        full_path = os.path.join(dir_path, entry)
        is_dir = os.path.isdir(full_path)
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "

        if is_dir:
            color = BOLD + CYAN
            icon = "📁 "
            suffix = "/"
        else:
            if entry.endswith(".py"):
                color = GREEN
                icon = "🐍 "
            elif entry.endswith(".html"):
                color = YELLOW
                icon = "🌐 "
            elif entry.endswith((".pkl", ".pt")):
                color = MAGENTA
                icon = "🧠 "
            elif entry.endswith((".json", ".conf", ".yml", ".yaml")):
                color = BLUE
                icon = "⚙️ "
            elif entry.endswith(".sh"):
                color = BOLD + GREEN
                icon = "⚡ "
            else:
                color = RESET
                icon = "📄 "
            suffix = ""

        print(f"{prefix}{connector}{icon}{color}{entry}{suffix}{RESET}")

        if is_dir:
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(full_path, new_prefix, max_depth, current_depth + 1)

if __name__ == "__main__":
    target = "/Users/yashpachhade/tokenshield"
    depth = 2

    args = sys.argv[1:]
    if "--depth" in args:
        idx = args.index("--depth")
        if idx + 1 < len(args):
            depth = int(args[idx + 1])
            args.pop(idx + 1)
            args.pop(idx)

    if args and not args[0].startswith("-"):
        sub = args[0].strip("/")
        target = os.path.join(target, sub)
        node_name = sub
    else:
        node_name = "tokenshield"

    print(f"\n{BOLD}{MAGENTA}🛡️  PROJECT NODE STRUCTURE: {node_name.upper()}{RESET}")
    print(f"{CYAN}{'═' * 55}{RESET}")
    print(f"{BOLD}{CYAN}📁 {node_name}/{RESET}")
    print_tree(target, max_depth=depth)
    print(f"{CYAN}{'═' * 55}{RESET}\n")
