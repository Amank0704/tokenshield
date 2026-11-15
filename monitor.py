#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║              TOKENSHIELD — LIVE PASSIVE MONITOR (T3 window)              ║
║                                                                          ║
║  This script does NOTHING on its own. It logs in nobody, steals no      ║
║  tokens, sends no attacks. It only WATCHES the real engine and prints   ║
║  what happens the instant a real incident is created by YOUR manual     ║
║  actions (browser login, DevTools token copy, curl from second device). ║
║                                                                          ║
║  Run this in its own terminal window (T3) BEFORE you start the demo,    ║
║  and leave it running the whole time.                                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Usage:  ./venv/bin/python monitor.py                                   ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
import sys
import time
import requests
from datetime import datetime

ENGINE_URL = "http://127.0.0.1:7777"
POLL_SECONDS = 1.0
STATS_EVERY = 10  # print a stats summary line every N polls

GREEN  = "\033[92m"; RED    = "\033[91m"; YELLOW = "\033[93m"
CYAN   = "\033[96m"; BOLD   = "\033[1m";  DIM    = "\033[2m"; RESET = "\033[0m"


def now():
    return datetime.now().strftime("%H:%M:%S")


def signal_bar(name, score, width=26):
    try:
        v = float(score)
    except (TypeError, ValueError):
        v = 0.0
    bar = "█" * int(v * width) + "░" * (width - int(v * width))
    c = RED if v >= 0.7 else YELLOW if v >= 0.3 else GREEN
    print(f"      {DIM}{name:<28}{RESET} [{c}{bar}{RESET}] {v:.2f}")


def print_incident(inc):
    lvl    = str(inc.get("threat_level", "?")).upper()
    action = str(inc.get("action", "?")).upper()
    score  = inc.get("threat_score", inc.get("anomaly_score", 0))
    ip     = inc.get("ip", "?")
    path   = inc.get("path", "?")
    reasons = inc.get("reasons", [])
    signals = inc.get("signals", {})
    expl   = inc.get("explanation", {})
    narr   = expl.get("narrative") or expl.get("summary") or ""

    c = RED if action == "BLOCK" else (YELLOW if action == "CHALLENGE" else GREEN)
    print(f"\n{c}{BOLD}{'━'*72}{RESET}")
    print(f"{c}{BOLD}  [{now()}]  NEW INCIDENT  →  {action}   score={score}   level={lvl}{RESET}")
    print(f"{c}{BOLD}{'━'*72}{RESET}")
    print(f"  {DIM}IP:{RESET}   {ip}")
    print(f"  {DIM}Path:{RESET} {path}")
    if reasons:
        print(f"  {DIM}Reasons:{RESET} {', '.join(reasons)}")
    if signals:
        print(f"  {DIM}Signal breakdown:{RESET}")
        for k, v in signals.items():
            signal_bar(k, v)
    if narr:
        print(f"  {DIM}Explanation:{RESET} {str(narr)[:260]}")
    print()


def fetch(path):
    try:
        r = requests.get(f"{ENGINE_URL}{path}", timeout=4)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def wait_for_engine():
    print(f"{CYAN}Waiting for TokenShield Engine at {ENGINE_URL}...{RESET}")
    while True:
        h = fetch("/health")
        if h:
            print(f"{GREEN}✓ Engine is up.{RESET}\n")
            return
        time.sleep(1)


def print_header():
    print(f"""{CYAN}{BOLD}
╔══════════════════════════════════════════════════════════════════════╗
║          TOKENSHIELD — LIVE MONITOR (passive, watch-only)            ║
║   This window triggers nothing. It only shows what YOU cause live.   ║
╚══════════════════════════════════════════════════════════════════════╝
{RESET}""")


def main():
    print_header()
    wait_for_engine()

    seen_ids = set()
    poll_count = 0

    # Prime seen_ids with whatever incidents already exist so we only show NEW ones
    initial = fetch("/api/v1/incidents")
    if initial:
        for inc in initial.get("incidents", []):
            key = inc.get("id") or (inc.get("session_id"), inc.get("timestamp"))
            seen_ids.add(key)
    print(f"{DIM}Baseline: {len(seen_ids)} pre-existing incident(s) ignored. Watching for new ones...{RESET}\n")

    try:
        while True:
            poll_count += 1
            data = fetch("/api/v1/incidents")
            if data:
                for inc in data.get("incidents", []):
                    key = inc.get("id") or (inc.get("session_id"), inc.get("timestamp"))
                    if key not in seen_ids:
                        seen_ids.add(key)
                        print_incident(inc)

            if poll_count % STATS_EVERY == 0:
                stats = fetch("/api/v1/stats")
                if stats:
                    perf = stats.get("performance", {})
                    print(f"{DIM}[{now()}] inspections={stats.get('total_inspections',0)}  "
                          f"allowed={stats.get('allowed_count',0)}  "
                          f"blocked={stats.get('blocked_count',0)}  "
                          f"challenged={stats.get('challenged_count',0)}  "
                          f"avg_latency={perf.get('avg_latency_ms',0):.1f}ms{RESET}")

            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print(f"\n{CYAN}Monitor stopped.{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
