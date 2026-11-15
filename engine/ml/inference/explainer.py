"""
TokenShield — Explainable Threat Intelligence (Phase 7)
========================================================
Generates human-readable, actionable security rationales explaining
why a request was flagged as malicious. Analyzes signal contributions,
feature deviations, and contextual attack signatures.

Usage:
    from engine.ml.inference.explainer import ThreatExplainer

    explainer = ThreatExplainer()
    explanation = explainer.explain(signals_dict, reasons_list, threat_level, threat_score)
"""

from typing import Dict, Any, List


class ThreatExplainer:
    SIGNAL_LABELS = {
        "ip_reputation": "IP Reputation (Tor / Proxy / Datacenter)",
        "request_velocity": "Request Velocity (Rate Spikes)",
        "session_consistency": "Session Consistency (IP/UA Drift)",
        "payload_analysis": "Payload Inspection (Injection / Traversal)",
        "behavioral_biometrics": "Behavioral Biometrics (Keystroke / Mouse Drift)",
        "geographic_impossibility": "Geographic Impossibility (Impossible Travel)",
        "endpoint_risk": "Target Endpoint Sensitivity",
        "sequential_behavior": "Sequential Workflow Anomaly (Path Jump)",
    }

    def explain(
        self,
        signals: Dict[str, float],
        reasons: List[str],
        threat_level: str,
        threat_score: float
    ) -> Dict[str, Any]:
        contributing_signals = []
        for sig_key, score in signals.items():
            if score >= 0.25:
                label = self.SIGNAL_LABELS.get(sig_key, sig_key)
                contributing_signals.append({
                    "signal": sig_key,
                    "name": label,
                    "score": round(score, 3),
                    "impact": "CRITICAL" if score >= 0.70 else "HIGH" if score >= 0.50 else "MODERATE"
                })

        contributing_signals.sort(key=lambda x: x["score"], reverse=True)

        # Synthesize plain-English diagnostic summary
        top_names = [s["name"] for s in contributing_signals[:3]]
        if threat_level in ("critical", "high"):
            if "tor_exit_node" in reasons and "impossible_travel" in reasons:
                narrative = (
                    "Session Hijacking in progress: Traffic detected originating from a Tor exit node "
                    "with impossible geographical travel velocity relative to previous verified location."
                )
            elif "biometric_mismatch" in reasons or "biometric_anomaly" in reasons:
                narrative = (
                    "Credential or Session Token Compromise: Active session shows biometric typing/mouse "
                    "dynamics deviating significantly from the account holder's established behavioral baseline."
                )
            elif any("sql" in r or "xss" in r for r in reasons):
                narrative = (
                    "Malicious Payload Exploit: Request parameters contain structured SQL injection or cross-site "
                    "scripting signatures targeting backend databases."
                )
            elif "sequential_anomaly" in reasons or "anomalous_navigation_sequence" in reasons:
                narrative = (
                    "Workflow Bypass / Direct Endpoint Tampering: Session abruptly accessed high-privilege/transfer "
                    "endpoints without traversing the standard authentication flow."
                )
            elif top_names:
                narrative = (
                    f"Elevated multi-signal threat (score {threat_score:.2f}) triggered primarily by: "
                    f"{', '.join(top_names)}."
                )
            else:
                narrative = f"Threat score {threat_score:.2f} exceeded safety threshold."
        elif threat_level == "medium":
            narrative = (
                f"Suspicious activity observed (score {threat_score:.2f}). Stepped-up verification (2FA/OTP) recommended. "
                f"Elevated indicators in: {', '.join(top_names) if top_names else 'traffic velocity'}."
            )
        else:
            narrative = f"Request verified safe (threat score {threat_score:.2f}). Within normal baseline parameters."

        return {
            "narrative": narrative,
            "threat_level": threat_level,
            "threat_score": threat_score,
            "contributing_signals": contributing_signals,
            "reasons": reasons,
            "recommended_action": "ENACT_FULL_MITIGATION" if threat_level in ("critical", "high") else ("CHALLENGE_2FA" if threat_level == "medium" else "ALLOW")
        }
