#!/bin/bash
# TokenShield — Open All Dashboards Launcher

echo "🚀 Opening all TokenShield & NeoVault Dashboards in your browser..."

# Open Port 7777 Dashboards (TokenShield Standalone AI Engine)
open "http://localhost:7777"
open "http://localhost:7777/attacker-studio"

# Open Port 5001 Dashboards (NeoVault Banking & Security Center)
open "http://localhost:5001/security-engine"
open "http://localhost:5001/admin"
open "http://localhost:5001/simulation"
open "http://localhost:5001/login"

echo "✅ All 6 dashboard tabs opened successfully!"
