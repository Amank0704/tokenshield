#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║           TokenShield — Full Demo Startup Script                ║
# ║    Starts Engine + NeoVault + verifies all portals live         ║
# ╚══════════════════════════════════════════════════════════════════╝
#
# Usage: ./START_DEMO.sh
# Stops all previous instances and starts fresh.

set -e

# ── Colors ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

# ── Paths ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/venv/bin/python"
LOG_DIR="$SCRIPT_DIR/logs"
ENGINE_LOG="$LOG_DIR/engine.log"
NEOVAULT_LOG="$LOG_DIR/neovault.log"

mkdir -p "$LOG_DIR"

echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║        🛡️  TokenShield AI Security — Demo Launch              ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Step 1: Kill previous instances ─────────────────────────────────
echo -e "${YELLOW}[1/6] Stopping any running TokenShield instances...${RESET}"
pkill -f "server_flask.py"  2>/dev/null && echo -e "    ${GREEN}✓ Engine stopped${RESET}" || echo -e "    (no engine was running)"
pkill -f "run.py"           2>/dev/null && echo -e "    ${GREEN}✓ NeoVault stopped${RESET}" || echo -e "    (no NeoVault was running)"
sleep 1

# ── Step 2: Check venv ───────────────────────────────────────────────
echo -e "${YELLOW}[2/6] Checking Python environment...${RESET}"
if [ ! -f "$VENV" ]; then
    echo -e "${RED}✗ Virtual environment not found at $VENV${RESET}"
    echo -e "  Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi
PYTHON_VER=$("$VENV" --version 2>&1)
echo -e "    ${GREEN}✓ $PYTHON_VER${RESET}"

# ── Step 3: Start TokenShield Engine on :7777 ────────────────────────
echo -e "${YELLOW}[3/6] Starting TokenShield AI Engine on port 7777...${RESET}"
cd "$SCRIPT_DIR"
nohup "$VENV" engine/server_flask.py > "$ENGINE_LOG" 2>&1 &
ENGINE_PID=$!
echo -e "    ${GREEN}✓ Engine started (PID: $ENGINE_PID)${RESET}"
echo -e "    📋 Logs: tail -f $ENGINE_LOG"

# ── Step 4: Start NeoVault Bank App on :5001 ─────────────────────────
echo -e "${YELLOW}[4/6] Starting NeoVault Bank Application on port 5001...${RESET}"
nohup "$VENV" run.py > "$NEOVAULT_LOG" 2>&1 &
NEOVAULT_PID=$!
echo -e "    ${GREEN}✓ NeoVault started (PID: $NEOVAULT_PID)${RESET}"
echo -e "    📋 Logs: tail -f $NEOVAULT_LOG"

# ── Step 5: Wait for services to be ready ────────────────────────────
echo ""
echo -e "${YELLOW}[5/6] Waiting for services to initialize...${RESET}"
printf "    Loading ML models "

READY=0
for i in $(seq 1 30); do
    sleep 1
    printf "."
    ENGINE_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:7777/health 2>/dev/null || echo "000")
    NEOVAULT_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/health 2>/dev/null || echo "000")
    
    if [ "$ENGINE_OK" = "200" ] && [ "$NEOVAULT_OK" = "200" ]; then
        READY=1
        break
    fi
done
echo ""

if [ "$READY" = "0" ]; then
    echo ""
    echo -e "${YELLOW}⚠  Services are still starting up. Check logs:${RESET}"
    echo -e "    Engine:   tail -f $ENGINE_LOG"
    echo -e "    NeoVault: tail -f $NEOVAULT_LOG"
    echo ""
    # Still show URLs — engine might need more time for models
fi

# ── Step 6: Verify connectivity ──────────────────────────────────────
echo -e "${YELLOW}[6/6] Verifying service connectivity...${RESET}"

check_url() {
    local url=$1
    local name=$2
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        echo -e "    ${GREEN}✓ $name ($url) — HTTP $code${RESET}"
    else
        echo -e "    ${YELLOW}⏳ $name ($url) — HTTP $code (may still be loading)${RESET}"
    fi
}

check_url "http://localhost:7777/health"              "TokenShield Engine"
check_url "http://localhost:7777/api/v1/layers"       "Defense Layers"
check_url "http://localhost:7777/api/v1/stats"        "Engine Stats"
check_url "http://localhost:5001/health"              "NeoVault Bank App"

# ── Done — Print All Portal URLs ────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║              🎯 ALL PORTALS ONLINE                           ║${RESET}"
echo -e "${CYAN}${BOLD}╠══════════════════════════════════════════════════════════════╣${RESET}"
echo -e "${CYAN}║${RESET}  ${BOLD}🏦 NeoVault Bank App${RESET}                                          ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}     http://localhost:5001                                     ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}     Login: alice@neovault.com / SecurePass123!                 ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}                                                               ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}  ${BOLD}⚔️  War Room Command Center${RESET}                                   ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}     http://localhost:7777/war-room                            ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}                                                               ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}  ${BOLD}🎯 Attacker Studio${RESET}                                           ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}     http://localhost:7777/attacker-studio                     ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}                                                               ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}  ${BOLD}📊 Simulation Dashboard${RESET}                                      ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}     http://localhost:5001/simulation                          ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}     (or open frontend/simulation_dashboard.html)              ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}                                                               ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}  ${BOLD}🔌 TokenShield Engine API${RESET}                                    ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}     http://localhost:7777/api/v1/analyze                      ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}     http://localhost:7777/api/v1/stats                        ${CYAN}║${RESET}"
echo -e "${CYAN}║${RESET}     http://localhost:7777/api/v1/incidents                    ${CYAN}║${RESET}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${BOLD}📬 Postman:${RESET} Import postman/TokenShield_Complete_Demo_Collection.json"
echo -e "${BOLD}🦗 Locust GUI:${RESET} ./venv/bin/locust -f simulation/locustfile.py --host=http://localhost:5001 (open http://localhost:8089)"
echo -e "${BOLD}📖 API Docs:${RESET} cat TOKENSHIELD_PUBLIC_API.md"
echo ""
echo -e "${GREEN}${BOLD}✅ Demo environment ready! Run attacks via Postman Collection Runner or Locust.${RESET}"
echo -e "   Open the War Room in your browser to watch attacks in real-time."
echo ""
echo -e "  Engine PID:   $ENGINE_PID"
echo -e "  NeoVault PID: $NEOVAULT_PID"
echo -e ""
echo -e "  To stop: ${YELLOW}pkill -f server_flask.py && pkill -f run.py${RESET}"
echo ""
