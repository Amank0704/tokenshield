import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from engine.ml.inference.lstm_infer import LSTMInferencer

infer = LSTMInferencer.get()

print("=" * 60)
print("MODEL INFO")
print("=" * 60)
print("model_type:", infer.model_type)
print("threshold (currently in use):", infer.threshold)
print("p50:", infer.p50, " p95:", infer.p95, " p99:", infer.p99)
print("window:", infer.window, " input_dim:", infer.input_dim)
print()

def make_seq(category_idx, n=10, method_risk=0.0, status_risk=0.0, sensitive=0.0):
    row = [category_idx / 10.0, method_risk, status_risk, 0.0, 0.0, sensitive]
    return np.array([row for _ in range(n)], dtype=np.float32)

scenarios = {
    "dashboard_GET_x10 (normal polling)": make_seq(2, n=10),
    "api_GET_x10 (normal /api/* calls)": make_seq(8, n=10),
    "mixed_dashboard_and_api": np.array(
        [[2/10, 0.0, 0.0, 0, 0, 0]] * 5 + [[8/10, 0.0, 0.0, 0, 0, 0]] * 5,
        dtype=np.float32
    ),
    "short_seq_len1_dashboard": make_seq(2, n=1),
    "short_seq_len3_api": make_seq(8, n=3),
    "transfer_sensitive_x1": make_seq(5, n=1, sensitive=0.8),
    "all_zeros (cold buffer)": np.zeros((10, 6), dtype=np.float32),
}

print("=" * 60)
print("RAW RECONSTRUCTION ERROR (raw_mse) PER SCENARIO")
print("=" * 60)
for name, seq in scenarios.items():
    raw_mse = infer.score_sequence(seq)
    norm_score, is_anom = infer.predict(seq)
    print(f"{name:40s} raw_mse={raw_mse:.8f}  norm_score={norm_score:.4f}  is_anomaly={is_anom}")

print()
print("=" * 60)
print("INTERPRETATION")
print("=" * 60)
print("If normal scenarios (dashboard/api GET traffic) show high raw_mse")
print("relative to the current threshold, the model itself doesn't recognize")
print("this traffic shape as normal (undertrained/miscalibrated), and no")
print("small threshold tweak will fix it reliably.")
