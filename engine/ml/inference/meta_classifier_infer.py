"""
TokenShield — Supervised Meta-Classifier Inference Module
=========================================================
Thread-safe singleton for scoring 40-dim feature vectors with the trained
calibrated meta-classifier (LightGBM / HistGradientBoosting).

Usage:
    from engine.ml.inference.meta_classifier_infer import MetaClassifierInferencer

    infer = MetaClassifierInferencer.get()
    risk_prob, is_threat = infer.predict(feature_vector)
"""

import json
import logging
import threading
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
import joblib

log = logging.getLogger("ts.meta_infer")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
ENGINE = ROOT / "engine"

import importlib.util
_cfg_path = ENGINE / "ml" / "data_config.py"
_spec = importlib.util.spec_from_file_location("data_config", _cfg_path)
_cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

MODELS_DIR = ROOT / _cfg.MODELS_DIR
META_MODEL_PATH = MODELS_DIR / "meta_classifier.pkl"
META_CALIBRATOR_PATH = MODELS_DIR / "meta_calibrator.pkl"
META_EVAL_PATH = MODELS_DIR / "meta_evaluation.json"


class MetaClassifierInferencer:
    _instance: Optional["MetaClassifierInferencer"] = None
    _lock = threading.Lock()

    @classmethod
    def get(cls) -> "MetaClassifierInferencer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.calibrator = None
        self.raw_model = None
        self.threshold = 0.50

        if META_CALIBRATOR_PATH.exists():
            try:
                self.calibrator = joblib.load(META_CALIBRATOR_PATH)
                log.info("Loaded calibrated meta-classifier.")
            except Exception as e:
                log.warning(f"Failed loading calibrator: {e}")

        if self.calibrator is None and META_MODEL_PATH.exists():
            try:
                self.raw_model = joblib.load(META_MODEL_PATH)
                log.info("Loaded uncalibrated base meta-classifier.")
            except Exception as e:
                log.warning(f"Failed loading base model: {e}")

        if META_EVAL_PATH.exists():
            try:
                with open(META_EVAL_PATH) as f:
                    eval_data = json.load(f)
                self.threshold = float(eval_data.get("test", {}).get("threshold", 0.50))
            except Exception:
                pass

    def predict_probability(self, feature_vector: np.ndarray) -> float:
        """
        Returns calibrated probability of attack [0.0, 1.0].
        feature_vector: shape (40,)
        """
        x = feature_vector.reshape(1, -1).astype(np.float32)
        if self.calibrator is not None:
            return float(self.calibrator.predict_proba(x)[0, 1])
        elif self.raw_model is not None:
            return float(self.raw_model.predict_proba(x)[0, 1])
        else:
            # Fallback heuristic: weighted sum of top signals
            # S = 0.25*s1 + 0.25*s2 + 0.30*s3 + 0.40*s4 + 0.30*s5 + 0.35*s6 + 0.20*s7 + 0.35*s8
            s1 = float(np.max(feature_vector[0:4]))
            s2 = float(feature_vector[4])
            s3 = float(feature_vector[9])
            s4 = float(np.max(feature_vector[15:18]))
            s5 = float(feature_vector[20])
            s6 = float(feature_vector[28])
            s7 = float(feature_vector[32])
            s8 = float(feature_vector[36])
            heuristic = 0.25*s1 + 0.25*s2 + 0.30*s3 + 0.40*s4 + 0.30*s5 + 0.35*s6 + 0.20*s7 + 0.35*s8
            return float(min(heuristic, 1.0))

    def predict(self, feature_vector: np.ndarray) -> Tuple[float, bool]:
        prob = self.predict_probability(feature_vector)
        return prob, prob >= self.threshold

    def health(self) -> dict:
        return {
            "status": "loaded" if (self.calibrator is not None or self.raw_model is not None) else "uninitialized",
            "has_calibrator": self.calibrator is not None,
            "threshold": self.threshold
        }
