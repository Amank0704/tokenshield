"""
TokenShield — Phase 5: Supervised Meta-Classifier Training
===========================================================
Trains a gradient-boosted decision tree ensemble (LightGBM / HistGradientBoosting)
on the unified 40-dimensional feature vector.
Combines all 8 signal dimensions with Platt probability calibration.

Inputs:
  - train.parquet on SSD
  - val.parquet on SSD
  - test.parquet on SSD (locked evaluation)

Outputs:
  - engine/ml/models/meta_classifier.pkl
  - engine/ml/models/meta_calibrator.pkl
  - engine/ml/models/meta_evaluation.json
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

from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score,
    confusion_matrix, average_precision_score, classification_report
)

log = logging.getLogger("ts.train_meta")

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent.parent
ENGINE = ROOT / "engine"

import importlib.util
_cfg_path = ENGINE / "ml" / "data_config.py"
_spec = importlib.util.spec_from_file_location("data_config", _cfg_path)
_cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

DATA_DIR = Path(_cfg.OUTPUT_DATA_DIR)
MODELS_DIR = ROOT / _cfg.MODELS_DIR
MODELS_DIR.mkdir(parents=True, exist_ok=True)

META_MODEL_PATH = MODELS_DIR / "meta_classifier.pkl"
META_CALIBRATOR_PATH = MODELS_DIR / "meta_calibrator.pkl"
META_EVAL_PATH = MODELS_DIR / "meta_evaluation.json"

FEAT_COLS = [f"f{i:02d}" for i in range(40)]


def load_split(name: str) -> tuple:
    path = DATA_DIR / f"{name}.parquet"
    if not path.exists():
        log.error(f"❌  {path} not found. Run feature_mapper.py first.")
        sys.exit(1)
    df = pd.read_parquet(path)
    X = df[FEAT_COLS].values.astype(np.float32)
    y = df["label"].values.astype(np.int8)
    log.info(f"  Loaded {name}.parquet: {len(X):,} rows (normal={int((y==0).sum()):,}, attack={int((y==1).sum()):,})")
    return X, y


def get_classifier():
    """
    Returns (classifier, model_family_name)
    Prefers LightGBM if installed; falls back to scikit-learn's native HistGradientBoosting.
    """
    try:
        import lightgbm as lgb
        log.info("  Using LightGBM classifier.")
        clf = lgb.LGBMClassifier(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=63,
            max_depth=8,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced"
        )
        return clf, "LightGBM"
    except ImportError:
        from sklearn.ensemble import HistGradientBoostingClassifier
        log.info("  Using scikit-learn HistGradientBoostingClassifier (LightGBM equivalent).")
        clf = HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.05,
            max_leaf_nodes=63,
            max_depth=8,
            random_state=42,
            class_weight="balanced"
        )
        return clf, "HistGradientBoosting"


def evaluate(model, X: np.ndarray, y: np.ndarray, split_name: str, threshold: float = 0.5) -> dict:
    probs = model.predict_proba(X)[:, 1]
    y_pred = (probs >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn + 1e-9)

    metrics = {
        "split": split_name,
        "roc_auc": float(roc_auc_score(y, probs)),
        "avg_precision": float(average_precision_score(y, probs)),
        "f1": float(f1_score(y, y_pred, zero_division=0)),
        "precision": float(precision_score(y, y_pred, zero_division=0)),
        "recall": float(recall_score(y, y_pred, zero_division=0)),
        "fpr": float(fpr),
        "threshold": threshold,
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
    }

    print(f"\n  ── {split_name.upper()} RESULTS ──────────────────────────────")
    print(f"    ROC-AUC        : {metrics['roc_auc']:.4f}")
    print(f"    Avg Precision  : {metrics['avg_precision']:.4f}")
    print(f"    F1 Score       : {metrics['f1']:.4f}")
    print(f"    Precision      : {metrics['precision']:.4f}")
    print(f"    Recall         : {metrics['recall']:.4f}")
    print(f"    False Pos Rate : {metrics['fpr']:.5f}")
    print(f"    TP={tp:,}  TN={tn:,}  FP={fp:,}  FN={fn:,}")
    return metrics


def train():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    print(f"\n{'═' * 60}")
    print("  TokenShield — Meta-Classifier Training (Phase 5)")
    print(f"{'═' * 60}\n")

    log.info("Loading dataset splits from SSD...")
    X_train, y_train = load_split("train")
    X_val, y_val = load_split("val")
    X_test, y_test = load_split("test")

    clf, model_name = get_classifier()

    log.info(f"\nTraining base classifier ({model_name}) on {len(X_train):,} rows...")
    t0 = time.time()
    clf.fit(X_train, y_train)
    t_train = time.time() - t0
    log.info(f"  Training finished in {t_train:.1f}s ✓")

    # Platt Calibration
    log.info("\nCalibrating output probabilities (Platt scaling / Sigmoid)...")
    calibrator = CalibratedClassifierCV(estimator=clf, cv="prefit", method="sigmoid")
    calibrator.fit(X_val, y_val)
    log.info("  Calibration complete ✓")

    # Evaluation
    val_m = evaluate(calibrator, X_val, y_val, "validation")
    test_m = evaluate(calibrator, X_test, y_test, "test")

    # Save artifacts
    log.info("\nSaving model artifacts...")
    joblib.dump(clf, META_MODEL_PATH, compress=3)
    joblib.dump(calibrator, META_CALIBRATOR_PATH, compress=3)

    report = {
        "model_type": model_name,
        "calibrator": "CalibratedClassifierCV(sigmoid)",
        "features": 40,
        "training_time_sec": round(t_train, 2),
        "validation": val_m,
        "test": test_m,
        "trained_at": str(pd.Timestamp.now())
    }
    with open(META_EVAL_PATH, "w") as f:
        json.dump(report, f, indent=2)

    log.info(f"  Saved: {META_MODEL_PATH.name}")
    log.info(f"  Saved: {META_CALIBRATOR_PATH.name}")
    log.info(f"  Saved: {META_EVAL_PATH.name}")

    print(f"\n{'═' * 60}")
    print("  META-CLASSIFIER — TRAINING COMPLETE")
    print(f"{'═' * 60}")
    print(f"  Model Name   : {model_name}")
    print(f"  Test ROC-AUC : {test_m['roc_auc']:.4f}")
    print(f"  Test F1      : {test_m['f1']:.4f}")
    print(f"  Test Precision: {test_m['precision']:.4f}")
    print(f"  Test Recall  : {test_m['recall']:.4f}")
    print(f"  Test FPR     : {test_m['fpr']:.5f}")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    train()
