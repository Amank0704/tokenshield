"""
TokenShield — LSTM Sequence Inference Module (Signal 8)
========================================================
Thread-safe singleton inferencer for evaluating request sequences.
Supports both PyTorch LSTM autoencoder and PCA fallback.

Usage:
    from engine.ml.inference.lstm_infer import LSTMInferencer

    infer = LSTMInferencer.get()
    # sequence: np.ndarray shape (window_len, 6) or (N, window_len, 6)
    score, is_anom = infer.predict(sequence)
"""

import json
import logging
import threading
from pathlib import Path
from typing import Tuple, Optional

import numpy as np

log = logging.getLogger("ts.lstm_infer")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
ENGINE = ROOT / "engine"

import importlib.util
_cfg_path = ENGINE / "ml" / "data_config.py"
_spec = importlib.util.spec_from_file_location("data_config", _cfg_path)
_cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

MODELS_DIR = ROOT / _cfg.MODELS_DIR
LSTM_MODEL_PATH = MODELS_DIR / "lstm_autoencoder.pt"
PCA_MODEL_PATH = MODELS_DIR / "lstm_autoencoder.pkl"
LSTM_THRESHOLD_PATH = MODELS_DIR / "lstm_threshold.json"


class LSTMInferencer:
    _instance: Optional["LSTMInferencer"] = None
    _lock = threading.Lock()

    @classmethod
    def get(cls) -> "LSTMInferencer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.model_type = "none"
        self.model = None
        self.threshold = 0.05
        self.p50 = 0.01
        self.p95 = 0.05
        self.p99 = 0.10
        self.window = 10
        self.input_dim = 6

        # A trained threshold this small (e.g. from a training run whose sequences had
        # near-zero variance) makes norm_score saturate to 1.0 for essentially any real
        # traffic, since raw_mse / (threshold * 2.0) blows past 1.0 immediately. Floor it
        # to a sane minimum so a degenerate calibration can't flag all traffic as critical.
        MIN_SANE_THRESHOLD = 1e-3

        if not LSTM_THRESHOLD_PATH.exists():
            log.warning("LSTM threshold file not found. Run train_lstm.py first. Using default threshold.")
        else:
            with open(LSTM_THRESHOLD_PATH) as f:
                meta = json.load(f)
            self.model_type = meta.get("model_type", "unknown")
            self.threshold = float(meta.get("alert_threshold", 0.05))
            self.p50 = float(meta.get("p50", 0.01))
            self.p95 = float(meta.get("p95", 0.05))
            self.p99 = float(meta.get("p99", 0.10))
            self.window = int(meta.get("seq_len", 10))
            self.input_dim = int(meta.get("input_dim", 6))

            if self.threshold < MIN_SANE_THRESHOLD:
                log.warning(
                    f"LSTM alert_threshold from {LSTM_THRESHOLD_PATH.name} is degenerately "
                    f"small ({self.threshold}); flooring to {MIN_SANE_THRESHOLD} to avoid "
                    f"saturating every sequence to a max anomaly score."
                )
                self.threshold = MIN_SANE_THRESHOLD

        # Try loading PyTorch model
        if LSTM_MODEL_PATH.exists():
            try:
                import torch
                import torch.nn as nn

                class LSTMAutoencoder(nn.Module):
                    def __init__(self, input_dim, hidden, seq_len):
                        super().__init__()
                        self.seq_len = seq_len
                        self.hidden = hidden
                        self.encoder = nn.LSTM(input_dim, hidden, num_layers=2, batch_first=True, dropout=0.2)
                        self.bottleneck = nn.Linear(hidden, hidden // 2)
                        self.expand = nn.Linear(hidden // 2, hidden)
                        self.decoder = nn.LSTM(hidden, hidden, num_layers=2, batch_first=True, dropout=0.2)
                        self.output_layer = nn.Linear(hidden, input_dim)

                    def forward(self, x):
                        _, (h, _) = self.encoder(x)
                        context = h[-1]
                        z = torch.relu(self.bottleneck(context))
                        z = torch.relu(self.expand(z))
                        dec_in = z.unsqueeze(1).repeat(1, self.seq_len, 1)
                        out, _ = self.decoder(dec_in)
                        return self.output_layer(out)

                checkpoint = torch.load(LSTM_MODEL_PATH, map_location="cpu")
                model = LSTMAutoencoder(checkpoint["input_dim"], checkpoint["hidden"], checkpoint["seq_len"])
                model.load_state_dict(checkpoint["state_dict"])
                model.eval()
                self.model = model
                self.model_type = "pytorch_lstm"
                log.info("Loaded PyTorch LSTM Autoencoder model for Signal 8.")
            except Exception as e:
                log.warning(f"Could not load PyTorch model: {e}")

        # Try loading PCA fallback
        if self.model is None and PCA_MODEL_PATH.exists():
            try:
                import joblib
                self.model = joblib.load(PCA_MODEL_PATH)
                self.model_type = "pca_fallback"
                log.info("Loaded PCA fallback model for Signal 8.")
            except Exception as e:
                log.warning(f"Could not load PCA model: {e}")

    def score_sequence(self, seq: np.ndarray) -> float:
        """
        Compute reconstruction error MSE for a sequence.
        seq: shape (seq_len, input_dim) or (batch, seq_len, input_dim)
        """
        if self.model is None:
            # Fallback heuristic if no model trained yet:
            # check sensitive/sql/xss indicators directly in sequence vectors
            if seq.ndim == 2 and seq.shape[1] >= 6:
                return float(np.mean(seq[:, 3:6]))
            return 0.0

        if seq.ndim == 2:
            seq = np.expand_dims(seq, axis=0)

        # Pad or slice to expected seq_len and input_dim
        batch, s_len, s_dim = seq.shape
        padded = np.zeros((batch, self.window, self.input_dim), dtype=np.float32)
        copy_len = min(s_len, self.window)
        copy_dim = min(s_dim, self.input_dim)
        padded[:, -copy_len:, :copy_dim] = seq[:, -copy_len:, :copy_dim]

        if self.model_type == "pytorch_lstm":
            import torch
            with torch.no_grad():
                t_seq = torch.tensor(padded, dtype=torch.float32)
                recon = self.model(t_seq)
                err = ((recon - t_seq) ** 2).mean().item()
                return float(err)
        elif self.model_type == "pca_fallback":
            flat = padded.reshape(batch, -1)
            recon = self.model.inverse_transform(self.model.transform(flat))
            err = np.mean((flat - recon) ** 2)
            return float(err)
        else:
            return 0.0

    def predict(self, seq: np.ndarray) -> Tuple[float, bool]:
        """
        Returns (normalized_score [0, 1], is_anomaly bool).
        """
        raw_mse = self.score_sequence(seq)
        # Normalize: threshold -> 0.5, 2x threshold -> 1.0
        norm_score = float(np.clip(raw_mse / (max(self.threshold, 1e-6) * 2.0), 0.0, 1.0))
        is_anomaly = raw_mse > self.threshold
        return norm_score, bool(is_anomaly)

    def health(self) -> dict:
        return {
            "model_type": self.model_type,
            "status": "loaded" if self.model is not None else "uninitialized",
            "threshold": self.threshold,
            "p95": self.p95,
            "window": self.window,
        }
