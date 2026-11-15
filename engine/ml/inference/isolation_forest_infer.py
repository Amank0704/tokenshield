"""
TokenShield — Isolation Forest Inference Module
================================================
Singleton inference wrapper used by the engine at request time.

Usage:
    from engine.ml.inference.isolation_forest_infer import IFInferencer

    infer = IFInferencer.get()
    score, is_attack = infer.predict(feature_vector)   # feature_vector: np.ndarray shape (40,)
    print(f"IF anomaly score: {score:.4f}  flagged={is_attack}")
"""

import json
import logging
import threading
from pathlib import Path

import numpy as np
import joblib

log = logging.getLogger("ts.if_infer")

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent.parent.parent
ENGINE    = ROOT / "engine"
MODELS_DIR = ROOT / "engine" / "ml" / "models"

IF_MODEL_PATH  = MODELS_DIR / "isolation_forest.pkl"
SCALER_PATH    = MODELS_DIR / "scaler.pkl"
SELECTOR_PATH  = MODELS_DIR / "feature_selector.pkl"
THRESHOLD_PATH = MODELS_DIR / "if_threshold.json"


class IFInferencer:
    """
    Thread-safe singleton wrapper around the trained IsolationForest model.

    Converts a raw 40-dim TokenShield feature vector to a continuous anomaly
    score in [0, 1]. Score is also compared to the calibrated threshold to
    give a binary is_attack flag.

    The score is NOT the final TokenShield threat score — it is Signal 2.5
    (the first-pass unsupervised filter). The LightGBM meta-classifier
    combines this with scores from all 8 signals.
    """

    _instance: "IFInferencer | None" = None
    _lock = threading.Lock()

    # ── Singleton accessor ────────────────────────────────────────────────────
    @classmethod
    def get(cls) -> "IFInferencer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Constructor ───────────────────────────────────────────────────────────
    def __init__(self) -> None:
        if not IF_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Isolation Forest model not found at {IF_MODEL_PATH}.\n"
                "Run: python engine/ml/train/train_isolation_forest.py"
            )
        self.model    = joblib.load(IF_MODEL_PATH)
        self.scaler   = joblib.load(SCALER_PATH)
        self.selector = joblib.load(SELECTOR_PATH)

        with open(THRESHOLD_PATH) as f:
            meta = json.load(f)
        self.threshold_raw = float(meta["threshold_raw"])
        self.n_features    = int(meta.get("n_features_selected", 9))
        self.trained_at    = meta.get("trained_at", "unknown")

        log.info(
            f"IFInferencer loaded — {self.n_features} features, "
            f"threshold={self.threshold_raw:.4f}, trained={self.trained_at}"
        )

    # ── Core scoring ──────────────────────────────────────────────────────────
    def _raw_anomaly_score(self, x: np.ndarray) -> float:
        """
        Returns raw IF anomaly score (higher = more anomalous).
        x: shape (40,) float32
        """
        x2d      = x.reshape(1, -1).astype(np.float32)
        x_sel    = self.selector.transform(x2d)
        x_scaled = self.scaler.transform(x_sel)
        return float(-self.model.score_samples(x_scaled)[0])

    def score(self, feature_vector: np.ndarray) -> float:
        """
        Returns anomaly score normalized to [0, 1].
        0.0 = clearly normal  |  1.0 = highly anomalous

        Normalization: raw score is divided by (threshold * 2) and clipped.
        Values > threshold map to > 0.5; scores > 2× threshold clip to 1.0.
        """
        raw = self._raw_anomaly_score(feature_vector)
        return float(min(max(raw / (self.threshold_raw * 2.0), 0.0), 1.0))

    def predict(self, feature_vector: np.ndarray) -> tuple:
        """
        Returns (anomaly_score: float, is_attack: bool).

        anomaly_score: [0, 1]  continuous score
        is_attack:     True if raw anomaly score exceeds calibrated threshold
        """
        raw      = self._raw_anomaly_score(feature_vector)
        score    = float(min(max(raw / (self.threshold_raw * 2.0), 0.0), 1.0))
        is_attack = raw > self.threshold_raw
        return score, bool(is_attack)

    def predict_batch(self, feature_matrix: np.ndarray) -> tuple:
        """
        Batch prediction for multiple feature vectors.
        feature_matrix: shape (N, 40)
        Returns (scores: np.ndarray shape(N,), flags: np.ndarray shape(N,) bool)
        """
        x_sel    = self.selector.transform(feature_matrix.astype(np.float32))
        x_scaled = self.scaler.transform(x_sel)
        raw      = -self.model.score_samples(x_scaled)
        scores   = np.clip(raw / (self.threshold_raw * 2.0), 0.0, 1.0).astype(np.float32)
        flags    = raw > self.threshold_raw
        return scores, flags

    # ── Health check ──────────────────────────────────────────────────────────
    def health(self) -> dict:
        """Returns a dict describing the loaded model. Used by /health endpoint."""
        return {
            "model":            "IsolationForest",
            "n_estimators":     self.model.n_estimators,
            "features_in":      40,
            "features_selected": self.n_features,
            "threshold":        self.threshold_raw,
            "trained_at":       self.trained_at,
            "status":           "loaded",
        }


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    inf = IFInferencer.get()
    print("\nIsolationForest Inferencer — Quick Test")
    print("=" * 50)
    print(f"Health: {inf.health()}")

    # Simulate a normal request (all zeros)
    normal_vec = np.zeros(40, dtype=np.float32)
    score, flag = inf.predict(normal_vec)
    print(f"\nNormal (zeros)  → score={score:.4f}  attack={flag}")

    # Simulate high-velocity attack (Signal 2 dims lit up)
    attack_vec = np.zeros(40, dtype=np.float32)
    attack_vec[4] = 0.95   # req_per_60s very high
    attack_vec[5] = 0.90   # req_per_10s very high
    attack_vec[15] = 0.80  # SQL injection
    score, flag = inf.predict(attack_vec)
    print(f"Attack (velocity+SQL) → score={score:.4f}  attack={flag}")

    # Speed test
    t0 = time.perf_counter()
    for _ in range(10_000):
        inf.score(normal_vec)
    ms = (time.perf_counter() - t0) / 10_000 * 1000
    print(f"\nSpeed: {ms:.3f}ms per call over 10,000 iterations")
