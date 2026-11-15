"""
TokenShield — ML Model Verification Script
===========================================
Tests the production ML inferencers directly:
  1. IFInferencer (Isolation Forest, 300 estimators)
  2. MetaClassifierInferencer (HistGradientBoosting + Calibrator)
"""

import sys
import time
from pathlib import Path
import numpy as np

# Ensure root is on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engine.ml.inference.isolation_forest_infer import IFInferencer
from engine.ml.inference.meta_classifier_infer import MetaClassifierInferencer

def run():
    print("═" * 78)
    print("  🛡️  TokenShield Machine Learning Models Direct Verification")
    print("═" * 78)

    t0 = time.perf_counter()
    if_infer = IFInferencer.get()
    meta_infer = MetaClassifierInferencer.get()
    load_time = (time.perf_counter() - t0) * 1000

    print(f"✅ Models initialized in {load_time:.2f} ms")
    print(f"   • Isolation Forest Threshold: {if_infer.threshold_raw:.4f}")
    print(f"   • Meta-Classifier Threshold : {meta_infer.threshold:.2f}")
    print("═" * 78)

    # 4 Scenarios: 40-dimensional feature vectors matching feature_mapper.py layout:
    # dims 0-3: IP Rep, 4-8: Velocity, 9-14: Session, 15-19: Payload, 20-27: Biometrics, 28-31: Geo, 32-35: Endpoint, 36-39: Seq
    scenarios = [
        {
            "name": "1. Benign Human User",
            "desc": "Normal session, domestic IP, 65 WPM typing, standard velocity",
            "vector": np.zeros(40, dtype=np.float32)
        },
        {
            "name": "2. Tor Session Hijack",
            "desc": "Tor exit IP (Frankfurt), IP drift, velocity spike, geo relocation",
            "vector": np.array([
                1.0, 1.0, 0.8, 0.0,
                0.9, 0.8, 0.7, 0.0, 0.0,
                0.9, 0.8, 0.7, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0,
                0.8, 0.9, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0,
                1.0, 0.9, 0.8, 0.0,
                0.8, 0.5, 0.0, 0.0,
                0.9, 0.8, 0.0, 0.0
            ], dtype=np.float32)
        },
        {
            "name": "3. Automated Bot Script",
            "desc": "180 WPM typing, zero mouse jitter, rapid-fire rate (120 req/min)",
            "vector": np.array([
                0.5, 0.2, 0.0, 0.0,
                1.0, 1.0, 0.9, 0.8, 0.0,
                0.2, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0,
                1.0, 1.0, 1.0, 0.9, 0.8, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0,
                0.5, 0.2, 0.0, 0.0,
                0.8, 0.7, 0.0, 0.0
            ], dtype=np.float32)
        },
        {
            "name": "4. Exploit Payload (SQLi)",
            "desc": "SQL injection regex trigger (UNION SELECT), high endpoint risk",
            "vector": np.array([
                0.2, 0.0, 0.0, 0.0,
                0.3, 0.2, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                1.0, 1.0, 0.9, 0.8, 0.7,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0,
                1.0, 0.9, 0.8, 0.0,
                0.7, 0.5, 0.0, 0.0
            ], dtype=np.float32)
        }
    ]

    print(f"{'SCENARIO':<26} | {'IF SCORE':<10} | {'IF ATTACK':<10} | {'META PROB':<10} | {'VERDICT':<10} | {'LATENCY'}")
    print("─" * 78)

    for sc in scenarios:
        t_start = time.perf_counter()
        
        # Isolation Forest inference
        if_score, if_attack = if_infer.predict(sc["vector"])
        
        # Meta-Classifier inference
        meta_prob, meta_threat = meta_infer.predict(sc["vector"])
        
        latency_ms = (time.perf_counter() - t_start) * 1000

        verdict = "🛑 BLOCK" if (if_attack or meta_threat) else "✅ ALLOW"
        if_flag = "ATTACK" if if_attack else "NORMAL"

        print(f"{sc['name']:<26} | {if_score:<10.4f} | {if_flag:<10} | {meta_prob:<10.2%} | {verdict:<10} | {latency_ms:.2f} ms")

    print("═" * 78)
    print("✅ Model testing completed successfully.")

if __name__ == "__main__":
    run()
