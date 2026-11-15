"""
TokenShield — 7-Layer Hierarchical Banking Security Defense Registry
====================================================================
Implements the multi-tiered defense-in-depth model used by Tier-1 financial
institutions (SWIFT CSP, BIS, RBI Cyber Framework, PCI-DSS 4.0):

  Layer 1: Perimeter Edge (Nginx/WAF blocklist & network perimeter)
  Layer 2: Device & Fingerprint Posture (Hardware/Browser identity)
  Layer 3: Geographic Intelligence (Haversine displacement & border speed)
  Layer 4: Network & Velocity Control (Rate limit, DoS, Tor/Proxy defense)
  Layer 5: Transaction & Workflow Trust (Payload inspection, SQLi, sequential jumps)
  Layer 6: Session & Identity Integrity (JWT binding, typing & mouse biometrics)
  Layer 7: AI Multi-Model Intelligence Core (Isolation Forest, LSTM, GBDT ensemble)
"""

import time
import threading
from typing import Dict, Any, List


class LayerRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self.layers = {
            1: {
                "id": 1,
                "code": "L1_PERIMETER",
                "name": "Perimeter Edge & WAF",
                "scope": "Edge reverse proxy, CIDR firewall, TLS validation",
                "status": "CLEAR",
                "score": 0.0,
                "trigger_count": 0,
                "last_incident": None,
                "color": "#00ff88"
            },
            2: {
                "id": 2,
                "code": "L2_DEVICE",
                "name": "Device & Fingerprint Posture",
                "scope": "Hardware canvas/WebGL entropy, UA consistency, bot flags",
                "status": "CLEAR",
                "score": 0.0,
                "trigger_count": 0,
                "last_incident": None,
                "color": "#00ff88"
            },
            3: {
                "id": 3,
                "code": "L3_GEOGRAPHIC",
                "name": "Geographic Intelligence",
                "scope": "Haversine supersonic transit check, high-risk jurisdiction",
                "status": "CLEAR",
                "score": 0.0,
                "trigger_count": 0,
                "last_incident": None,
                "color": "#00ff88"
            },
            4: {
                "id": 4,
                "code": "L4_NETWORK",
                "name": "Network & Velocity Defense",
                "scope": "Sliding-window rate enforcement, Tor exit & botnet isolation",
                "status": "CLEAR",
                "score": 0.0,
                "trigger_count": 0,
                "last_incident": None,
                "color": "#00ff88"
            },
            5: {
                "id": 5,
                "code": "L5_TRANSACTION",
                "name": "Transaction & Workflow Trust",
                "scope": "Payload sanitization (SQLi/XSS), navigation workflow integrity",
                "status": "CLEAR",
                "score": 0.0,
                "trigger_count": 0,
                "last_incident": None,
                "color": "#00ff88"
            },
            6: {
                "id": 6,
                "code": "L6_IDENTITY",
                "name": "Session & Identity Integrity",
                "scope": "Token hijacking detection, keystroke & mouse biometric verification",
                "status": "CLEAR",
                "score": 0.0,
                "trigger_count": 0,
                "last_incident": None,
                "color": "#00ff88"
            },
            7: {
                "id": 7,
                "code": "L7_AI_CORE",
                "name": "AI Multi-Model Intelligence",
                "scope": "Isolation Forest, Sequence LSTM, Calibrated Meta-Classifier",
                "status": "CLEAR",
                "score": 0.0,
                "trigger_count": 0,
                "last_incident": None,
                "color": "#00ff88"
            }
        }

    def evaluate_and_update(self, signals: Dict[str, float], composite_threat_score: float, incident_id: str = None) -> List[Dict[str, Any]]:
        """
        Maps signals and ML scores to the 7 defense layers, updating layer states.
        """
        s1 = signals.get("ip_reputation", 0.0)
        s2 = signals.get("request_velocity", 0.0)
        s3 = signals.get("session_consistency", 0.0)
        s4 = signals.get("payload_analysis", 0.0)
        s5 = signals.get("behavioral_biometrics", 0.0)
        s6 = signals.get("geographic_impossibility", 0.0)
        s7 = signals.get("endpoint_risk", 0.0)
        s8 = signals.get("sequential_behavior", 0.0)

        # Layer mapping calculation
        now = time.time()
        with self._lock:
            # L1: Edge Perimeter (Active edge blocking or severe IP/payload abuse)
            l1_score = max(s1 * 0.8, 0.95 if composite_threat_score >= 0.85 else 0.0)
            self._update_layer(1, l1_score, now, incident_id)

            # L2: Device & Fingerprint Posture
            l2_score = s3 if s3 >= 0.80 else s3 * 0.5
            self._update_layer(2, l2_score, now, incident_id)

            # L3: Geographic Intelligence
            l3_score = s6
            self._update_layer(3, l3_score, now, incident_id)

            # L4: Network & Velocity Control
            l4_score = max(s1, s2)
            self._update_layer(4, l4_score, now, incident_id)

            # L5: Transaction & Workflow Trust
            l5_score = max(s4, s7, s8)
            self._update_layer(5, l5_score, now, incident_id)

            # L6: Session & Identity Integrity
            l6_score = max(s3, s5)
            self._update_layer(6, l6_score, now, incident_id)

            # L7: AI Multi-Model Intelligence Core
            l7_score = composite_threat_score
            self._update_layer(7, l7_score, now, incident_id)

            return list(self.layers.values())

    def _update_layer(self, layer_id: int, score: float, timestamp: float, incident_id: str):
        layer = self.layers[layer_id]
        layer["score"] = round(float(score), 4)

        if score >= 0.80:
            layer["status"] = "CRITICAL"
            layer["color"] = "#ff3b5c"
            layer["trigger_count"] += 1
            layer["last_incident"] = incident_id
            layer["last_triggered"] = timestamp
        elif score >= 0.50:
            layer["status"] = "ALERT"
            layer["color"] = "#ffb800"
            layer["trigger_count"] += 1
            layer["last_incident"] = incident_id
            layer["last_triggered"] = timestamp
        elif score >= 0.25:
            layer["status"] = "MONITORING"
            layer["color"] = "#00d4ff"
        else:
            layer["status"] = "CLEAR"
            layer["color"] = "#00ff88"

    def get_all_layers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.layers.values())

    def reset_status(self):
        with self._lock:
            for l in self.layers.values():
                l["status"] = "CLEAR"
                l["score"] = 0.0
                l["color"] = "#00ff88"


_GLOBAL_REGISTRY = LayerRegistry()

def get_layer_registry() -> LayerRegistry:
    return _GLOBAL_REGISTRY

def evaluate_layers_status(signals: Dict[str, float], composite_score: float, incident_id: str = None) -> List[Dict[str, Any]]:
    return _GLOBAL_REGISTRY.evaluate_and_update(signals, composite_score, incident_id)
