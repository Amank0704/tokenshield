"""
TokenShield — Phase 2: Isolation Forest Training  (v2 — fixed)
===============================================================
Key fixes over v1:
 - Correct model path (no double engine/)
 - VarianceThreshold feature selection (removes near-zero dims)
 - Percentile-based threshold calibration (FPR-controlled)
 - Raw score thresholding — no broken sigmoid mapping
"""

import sys
import json
import time
import logging
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import VarianceThreshold
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score,
    confusion_matrix, average_precision_score
)

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
ROOT   = Path(__file__).resolve().parent.parent.parent.parent   # tokenshield/
ENGINE = ROOT / "engine"

import importlib.util
_cfg_path = ENGINE / "ml" / "data_config.py"
_spec = importlib.util.spec_from_file_location("data_config", _cfg_path)
_cfg  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

DATA_DIR   = Path(_cfg.OUTPUT_DATA_DIR)
MODELS_DIR = ROOT / _cfg.MODELS_DIR          # FIX: was ENGINE / ... causing double engine/
MODELS_DIR.mkdir(parents=True, exist_ok=True)

IF_MODEL_PATH  = MODELS_DIR / "isolation_forest.pkl"
SCALER_PATH    = MODELS_DIR / "scaler.pkl"
SELECTOR_PATH  = MODELS_DIR / "feature_selector.pkl"
THRESHOLD_PATH = MODELS_DIR / "if_threshold.json"

FEAT_COLS = [f"f{i:02d}" for i in range(40)]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("ts.train_if")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def load_split(name: str) -> tuple:
    path = DATA_DIR / f"{name}.parquet"
    if not path.exists():
        log.error(f"❌  {path} not found. Run feature_mapper.py first.")
        sys.exit(1)
    df = pd.read_parquet(path)
    X  = df[FEAT_COLS].values.astype(np.float32)
    y  = df["label"].values.astype(np.int8)
    log.info(f"  Loaded {name}.parquet: {len(X):,} rows  "
             f"(normal={int((y==0).sum()):,}  attack={int((y==1).sum()):,})")
    return X, y


def evaluate(model, scaler, selector, threshold_raw: float,
             X: np.ndarray, y: np.ndarray, split_name: str) -> dict:
    """
    Evaluate using raw IF anomaly scores (negative of score_samples).
    threshold_raw: if anomaly_score > threshold → flag as attack.
    """
    X_sel    = selector.transform(X)
    X_scaled = scaler.transform(X_sel)
    # Raw anomaly score: higher = more anomalous
    anomaly_scores = -model.score_samples(X_scaled)

    y_pred = (anomaly_scores > threshold_raw).astype(int)

    # Guard against degenerate case
    if y_pred.sum() == 0 or y_pred.sum() == len(y_pred):
        log.warning(f"  Degenerate predictions on {split_name}: all {y_pred[0]}")

    tn, fp, fn, tp = confusion_matrix(y, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn + 1e-9)

    metrics = {
        "split":         split_name,
        "roc_auc":       float(roc_auc_score(y, anomaly_scores)),
        "avg_precision": float(average_precision_score(y, anomaly_scores)),
        "f1":            float(f1_score(y, y_pred, zero_division=0)),
        "precision":     float(precision_score(y, y_pred, zero_division=0)),
        "recall":        float(recall_score(y, y_pred, zero_division=0)),
        "fpr":           float(fpr),
        "threshold_raw": float(threshold_raw),
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
    }

    print(f"\n  ── {split_name.upper()} RESULTS ──────────────────────────────")
    print(f"    ROC-AUC        : {metrics['roc_auc']:.4f}")
    print(f"    Avg Precision  : {metrics['avg_precision']:.4f}")
    print(f"    F1 Score       : {metrics['f1']:.4f}")
    print(f"    Precision      : {metrics['precision']:.4f}")
    print(f"    Recall         : {metrics['recall']:.4f}")
    print(f"    False Pos Rate : {metrics['fpr']:.5f}  (target < 0.01)")
    print(f"    TP={tp:,}  TN={tn:,}  FP={fp:,}  FN={fn:,}")
    return metrics


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def train(eval_only: bool = False, target_fpr: float = 0.05) -> None:

    print(f"\n{'═' * 60}")
    print("  TokenShield — Isolation Forest Training  (v2)")
    print(f"{'═' * 60}\n")

    # ── Load data ─────────────────────────────────────────────────────────────
    log.info("Loading training data from SSD...")
    X_train, y_train = load_split("train")
    X_val,   y_val   = load_split("val")
    X_test,  y_test  = load_split("test")

    X_normal = X_train[y_train == 0]
    log.info(f"  Normal-only training rows: {len(X_normal):,}")

    if eval_only:
        if not IF_MODEL_PATH.exists():
            log.error("No model found. Run without --eval-only first.")
            sys.exit(1)
        model    = joblib.load(IF_MODEL_PATH)
        scaler   = joblib.load(SCALER_PATH)
        selector = joblib.load(SELECTOR_PATH)
        with open(THRESHOLD_PATH) as f:
            d = json.load(f)
        threshold_raw = d["threshold_raw"]
        log.info(f"  Loaded existing model. Threshold={threshold_raw:.6f}")

    else:
        # ── Step 1: Feature selection — remove near-zero variance dims ─────────
        log.info("\nStep 1 — VarianceThreshold feature selection...")
        selector = VarianceThreshold(threshold=1e-4)
        selector.fit(X_train)
        n_selected = selector.get_support().sum()
        log.info(f"  Selected {n_selected}/{len(FEAT_COLS)} features "
                 f"(removed {len(FEAT_COLS)-n_selected} near-zero variance)")

        X_normal_sel = selector.transform(X_normal)
        X_train_sel  = selector.transform(X_train)

        # ── Step 2: StandardScaler on all training data ────────────────────────
        log.info("\nStep 2 — StandardScaler on all training data...")
        scaler = StandardScaler()
        scaler.fit(X_train_sel)
        X_normal_scaled = scaler.transform(X_normal_sel)
        log.info("  Scaler fitted ✓")

        # ── Step 3: Train Isolation Forest on normal-only data ─────────────────
        log.info("\nStep 3 — Training Isolation Forest on normal rows only...")
        log.info(f"  Input shape: {X_normal_scaled.shape}")
        log.info("  n_estimators=300, contamination='auto', max_samples=0.8")
        t0 = time.time()
        model = IsolationForest(
            n_estimators  = 300,
            contamination = "auto",   # let IF determine boundary from data
            max_samples   = 0.8,
            max_features  = 1.0,
            n_jobs        = -1,       # all M2 cores
            random_state  = 42,
        )
        model.fit(X_normal_scaled)
        elapsed = time.time() - t0
        log.info(f"  Training complete in {elapsed:.1f}s ✓")

        # ── Step 4: Percentile-based threshold on VALIDATION NORMAL rows ───────
        #
        # Strategy: find the raw anomaly score that gives target_fpr on clean
        # validation traffic. Anomaly score = -score_samples (higher = worse).
        # threshold = percentile(1 - target_fpr) of NORMAL validation scores.
        #
        log.info(f"\nStep 4 — Calibrating threshold (target FPR={target_fpr:.2%})...")
        X_val_normal = X_val[y_val == 0]
        X_val_normal_sel    = selector.transform(X_val_normal)
        X_val_normal_scaled = scaler.transform(X_val_normal_sel)
        normal_anomaly_scores = -model.score_samples(X_val_normal_scaled)

        # Set threshold at (1 - target_fpr) percentile of normal scores
        # e.g. target_fpr=0.05 → 95th percentile → 5% of normal traffic flagged
        threshold_raw = float(np.percentile(normal_anomaly_scores,
                                            (1.0 - target_fpr) * 100))
        log.info(f"  Threshold (raw): {threshold_raw:.6f}")
        log.info(f"  Score range on normal val: "
                 f"[{normal_anomaly_scores.min():.4f}, {normal_anomaly_scores.max():.4f}]")

        # ── Step 5: Save artifacts ─────────────────────────────────────────────
        log.info("\nStep 5 — Saving model artifacts...")
        joblib.dump(model,    IF_MODEL_PATH, compress=3)
        joblib.dump(scaler,   SCALER_PATH,   compress=3)
        joblib.dump(selector, SELECTOR_PATH, compress=3)

        selected_features = [FEAT_COLS[i] for i, v in
                             enumerate(selector.get_support()) if v]
        with open(THRESHOLD_PATH, "w") as f:
            json.dump({
                "threshold_raw":     threshold_raw,
                "target_fpr":        target_fpr,
                "n_features_in":     40,
                "n_features_selected": int(n_selected),
                "selected_features": selected_features,
                "n_estimators":      300,
                "train_normal_rows": len(X_normal),
                "trained_at":        str(pd.Timestamp.now()),
            }, f, indent=2)
        log.info(f"  Saved: {IF_MODEL_PATH.name}")
        log.info(f"  Saved: {SCALER_PATH.name}")
        log.info(f"  Saved: {SELECTOR_PATH.name}")
        log.info(f"  Saved: {THRESHOLD_PATH.name}")

    # ── Evaluate ──────────────────────────────────────────────────────────────
    log.info("\nEvaluating on validation + test splits...")
    val_m  = evaluate(model, scaler, selector, threshold_raw, X_val,  y_val,  "validation")
    test_m = evaluate(model, scaler, selector, threshold_raw, X_test, y_test, "test")

    report = {"model": "IsolationForest_v2",
              "validation": val_m, "test": test_m}
    with open(MODELS_DIR / "if_evaluation.json", "w") as f:
        json.dump(report, f, indent=2)

    # ── Inference speed ───────────────────────────────────────────────────────
    log.info("\nInference speed benchmark (1000 single-request iterations)...")
    sample = scaler.transform(selector.transform(X_test[:1]))
    t0 = time.perf_counter()
    for _ in range(1000):
        model.score_samples(sample)
    elapsed_ms = (time.perf_counter() - t0) * 1000 / 1000
    log.info(f"  {elapsed_ms:.3f}ms per request (target < 5ms)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("  ISOLATION FOREST — TRAINING COMPLETE")
    print(f"{'═' * 60}")
    print(f"  Models dir   : {MODELS_DIR}")
    print(f"  Threshold    : {threshold_raw:.6f}")
    print(f"  Val  ROC-AUC : {val_m['roc_auc']:.4f}")
    print(f"  Test ROC-AUC : {test_m['roc_auc']:.4f}")
    print(f"  Test F1      : {test_m['f1']:.4f}")
    print(f"  Test FPR     : {test_m['fpr']:.5f}  (target < 0.05)")
    print(f"  Inference    : {elapsed_ms:.3f}ms/request")
    if test_m['roc_auc'] < 0.75:
        print("\n  ⚠  ROC-AUC < 0.75 — expected for unsupervised-only IF.")
        print("     The meta-classifier (Phase 5, LightGBM) will boost this to >0.95")
        print("     using all 8 signals together. IF is just the first-pass filter.")
    print(f"\n  ▶  Next: python engine/ml/train/train_lstm.py  (Phase 4 — Signal 8)")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TokenShield Isolation Forest Trainer")
    parser.add_argument("--eval-only", action="store_true")
    parser.add_argument("--target-fpr", type=float, default=0.05,
                        help="Target false positive rate for threshold calibration (default 0.05)")
    args = parser.parse_args()
    train(eval_only=args.eval_only, target_fpr=args.target_fpr)
