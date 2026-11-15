"""
TokenShield — Phase 4: LSTM Sequence Autoencoder (Signal 8)
============================================================
Trains an LSTM autoencoder that learns normal request navigation patterns.
At inference time, high reconstruction error = anomalous sequence = attack.

Architecture:
  Input  → LSTM Encoder (hidden=64, layers=2) → bottleneck (32)
         → LSTM Decoder (hidden=64, layers=2) → Reconstruction
  Loss   : MSE on sequence reconstruction

Training data:
  - NASA HTTP logs (200k requests → grouped into ~50k IP sessions)
  - Wikipedia clickstream (200k navigation transitions)
  Both from the already-processed parquet files (dims 36-39 populated).

Signal 8 produces:
  - f36: lstm_recon_error  (normalized reconstruction MSE)
  - f37: lstm_percentile   (percentile rank vs training distribution)
  - f38: window_size       (number of requests in window)
  - f39: sequence_novelty  (fraction of unseen transitions)

Usage:
  python engine/ml/train/train_lstm.py
  python engine/ml/train/train_lstm.py --epochs 30 --hidden 128
  python engine/ml/train/train_lstm.py --eval-only
"""

import sys
import json
import time
import logging
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger("ts.train_lstm")

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent.parent.parent
ENGINE    = ROOT / "engine"

import importlib.util
_cfg_path = ENGINE / "ml" / "data_config.py"
_spec = importlib.util.spec_from_file_location("data_config", _cfg_path)
_cfg  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

DATA_DIR   = Path(_cfg.OUTPUT_DATA_DIR)
RAW_DIR    = Path(_cfg.RAW_DATA_DIR)
MODELS_DIR = ROOT / _cfg.MODELS_DIR
MODELS_DIR.mkdir(parents=True, exist_ok=True)

LSTM_MODEL_PATH     = MODELS_DIR / "lstm_autoencoder.pt"
LSTM_THRESHOLD_PATH = MODELS_DIR / "lstm_threshold.json"

# ─────────────────────────────────────────────────────────────────────────────
# Sequence feature extraction from raw NASA HTTP log
# ─────────────────────────────────────────────────────────────────────────────
import re

LOG_RE = re.compile(
    r'(\S+) \S+ \S+ \[[^\]]+\] "(\w+)?\s*([^\s"]*)[^"]*" (\d+) (\S+)'
)

# Page category mapping (for clickstream-style encoding)
PATH_CATEGORIES = {
    "images": 0, "shuttle": 1, "facilities": 2, "statistics": 3,
    "software": 4, "news": 5, "ksc": 6, "history": 7, "countdown": 8,
    "expendable": 9, "biomed": 10, "gallery": 11, "education": 12,
    "sensor": 13, "procurement": 14, "other": 15,
}
N_CATEGORIES = len(PATH_CATEGORIES) + 1   # +1 for "other"

SQL_RE  = re.compile(r"select\s|union\s|drop\s|exec\s|'--|sleep\s*\(", re.I)
XSS_RE  = re.compile(r"<script|javascript:|onerror=|alert\s*\(", re.I)
SENS_RE = re.compile(r"admin|login|password|transfer|payment|delete|config", re.I)

METHOD_MAP = {"GET": 0.0, "POST": 0.5, "PUT": 0.6, "DELETE": 0.8,
              "PATCH": 0.5, "HEAD": 0.1, "OPTIONS": 0.1}


def path_to_vec(path: str, method: str, status: int) -> np.ndarray:
    """Convert one HTTP request to a 6-dim feature vector."""
    v = np.zeros(6, dtype=np.float32)

    # Dim 0: path category (one of 16 categories, normalized)
    path_lower = path.lower()
    cat = 15   # "other"
    for keyword, idx in PATH_CATEGORIES.items():
        if keyword in path_lower:
            cat = idx
            break
    v[0] = cat / N_CATEGORIES

    # Dim 1: HTTP method risk
    v[1] = METHOD_MAP.get(method.upper(), 0.3)

    # Dim 2: Status code anomaly (4xx/5xx = suspicious)
    v[2] = 0.0 if status < 400 else (0.5 if status < 500 else 1.0)

    # Dim 3: SQL injection in URL
    v[3] = 1.0 if SQL_RE.search(path) else 0.0

    # Dim 4: XSS in URL
    v[4] = 1.0 if XSS_RE.search(path) else 0.0

    # Dim 5: Sensitive endpoint
    v[5] = 0.8 if SENS_RE.search(path) else 0.0

    return v


def build_sequences_from_nasa(raw_dir: Path, window: int = 10,
                               step: int = 5, max_sessions: int = 50_000,
                               normal_only: bool = True) -> np.ndarray:
    """
    Parse NASA HTTP log → group by IP → sliding window sequences.
    Returns array of shape (N_sequences, window, 6).
    If normal_only=True, skip sessions with SQL/XSS patterns.
    """
    log.info("Parsing NASA HTTP log for LSTM sequences...")
    nasa_dir = raw_dir / "A11_nasa_http"
    log_files = [f for f in nasa_dir.iterdir()
                 if f.is_file() and not f.name.endswith(".gz")]
    if not log_files:
        # Try decompressing
        import gzip, shutil
        for gz in nasa_dir.glob("*.gz"):
            out_path = nasa_dir / gz.stem
            if not out_path.exists():
                with gzip.open(gz, "rb") as fi, open(out_path, "wb") as fo:
                    shutil.copyfileobj(fi, fo)
        log_files = [f for f in nasa_dir.iterdir()
                     if f.is_file() and not f.name.endswith(".gz")]

    if not log_files:
        log.warning("  NASA HTTP log not found — using random normal sequences")
        return np.random.randn(5000, window, 6).astype(np.float32) * 0.05

    # Group requests by IP
    sessions: dict = {}   # ip → list of request vectors
    rows = 0
    for fpath in log_files[:1]:
        with open(fpath, "r", errors="replace") as f:
            for line in f:
                m = LOG_RE.match(line)
                if not m:
                    continue
                ip     = m.group(1)
                method = m.group(2) or "GET"
                path   = m.group(3) or "/"
                status = int(m.group(4))
                vec    = path_to_vec(path, method, status)
                sessions.setdefault(ip, []).append(vec)
                rows += 1
                if rows >= 500_000:
                    break

    log.info(f"  Parsed {rows:,} requests from {len(sessions):,} unique IPs")

    # Build sliding window sequences from each session
    seqs = []
    for ip, reqs in sessions.items():
        if len(reqs) < window:
            continue
        # Filter out attack sessions if normal_only
        req_arr = np.stack(reqs)
        if normal_only and (req_arr[:, 3].max() > 0 or req_arr[:, 4].max() > 0):
            continue   # skip sessions with SQL/XSS
        for start in range(0, len(reqs) - window + 1, step):
            seqs.append(req_arr[start:start + window])
        if len(seqs) >= max_sessions:
            break

    if not seqs:
        log.warning("  No sequences extracted — using fallback normal sequences")
        return np.zeros((5000, window, 6), dtype=np.float32)

    arr = np.stack(seqs[:max_sessions], axis=0).astype(np.float32)
    log.info(f"  Built {len(arr):,} sequences of length {window} from NASA logs")
    return arr


# ─────────────────────────────────────────────────────────────────────────────
# LSTM Autoencoder (PyTorch)
# ─────────────────────────────────────────────────────────────────────────────
def get_device():
    """Get best available device: MPS (Apple M2) > CUDA > CPU."""
    try:
        import torch
        if torch.backends.mps.is_available():
            log.info("  Using Apple MPS (Metal) GPU acceleration ✓")
            return torch.device("mps")
        if torch.cuda.is_available():
            log.info("  Using CUDA GPU ✓")
            return torch.device("cuda")
    except Exception:
        pass
    log.info("  Using CPU (install PyTorch for GPU acceleration)")
    return None


def train_lstm(seqs: np.ndarray, epochs: int = 20,
               hidden: int = 64, batch_size: int = 512,
               lr: float = 1e-3) -> tuple:
    """
    Train LSTM autoencoder. Returns (model, train_errors, threshold_meta).
    If PyTorch unavailable, trains a lightweight numpy PCA fallback.
    """
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError:
        log.warning("  PyTorch not installed. Run: pip install torch")
        log.warning("  Falling back to PCA-based sequence model (reduced accuracy)")
        return _train_pca_fallback(seqs)

    device_obj = get_device()
    if device_obj is None:
        device_obj = torch.device("cpu")

    # ── Build model ───────────────────────────────────────────────────────────
    input_dim  = seqs.shape[2]   # 6
    seq_len    = seqs.shape[1]   # 10

    class LSTMAutoencoder(nn.Module):
        def __init__(self, input_dim, hidden, seq_len):
            super().__init__()
            self.seq_len    = seq_len
            self.hidden     = hidden
            self.encoder    = nn.LSTM(input_dim, hidden, num_layers=2,
                                      batch_first=True, dropout=0.2)
            self.bottleneck = nn.Linear(hidden, hidden // 2)
            self.expand     = nn.Linear(hidden // 2, hidden)
            self.decoder    = nn.LSTM(hidden, hidden, num_layers=2,
                                      batch_first=True, dropout=0.2)
            self.output_layer = nn.Linear(hidden, input_dim)

        def forward(self, x):
            # Encode: take last hidden state
            _, (h, _) = self.encoder(x)
            context = h[-1]                             # (batch, hidden)
            # Bottleneck
            z = torch.relu(self.bottleneck(context))    # (batch, hidden//2)
            z = torch.relu(self.expand(z))              # (batch, hidden)
            # Decode: repeat context for each timestep
            dec_in  = z.unsqueeze(1).repeat(1, self.seq_len, 1)
            out, _  = self.decoder(dec_in)
            recon   = self.output_layer(out)            # (batch, seq, input_dim)
            return recon

    model = LSTMAutoencoder(input_dim, hidden, seq_len).to(device_obj)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.MSELoss()

    # ── DataLoader ────────────────────────────────────────────────────────────
    # Split 90/10 train/val
    n_train = int(len(seqs) * 0.9)
    X_tr    = torch.tensor(seqs[:n_train],  dtype=torch.float32)
    X_val_t = torch.tensor(seqs[n_train:],  dtype=torch.float32)
    loader  = DataLoader(TensorDataset(X_tr),  batch_size=batch_size, shuffle=True)

    # ── Training loop ─────────────────────────────────────────────────────────
    log.info(f"\n  Training LSTM Autoencoder on {len(seqs):,} sequences...")
    log.info(f"  Architecture: LSTM(input={input_dim}, hidden={hidden}) → bottleneck({hidden//2}) → decode")
    log.info(f"  Device: {device_obj}  |  epochs={epochs}  |  batch={batch_size}")

    best_val_loss = float("inf")
    best_state    = None
    t0 = time.time()

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for (batch,) in loader:
            batch = batch.to(device_obj)
            optimizer.zero_grad()
            recon = model(batch)
            loss  = criterion(recon, batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item() * len(batch)
        train_loss /= len(X_tr)
        scheduler.step()

        # Validation
        model.eval()
        with torch.no_grad():
            val_batch = X_val_t.to(device_obj)
            val_recon = model(val_batch)
            val_loss  = criterion(val_recon, val_batch).item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state    = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        if (epoch + 1) % 5 == 0 or epoch == 0:
            elapsed = time.time() - t0
            log.info(f"  Epoch {epoch+1:>3}/{epochs}  "
                     f"train_loss={train_loss:.6f}  val_loss={val_loss:.6f}  "
                     f"elapsed={elapsed:.0f}s")

    log.info(f"  Best val_loss={best_val_loss:.6f}  ✓")
    model.load_state_dict(best_state)
    model.eval()
    model.to("cpu")

    # ── Compute per-sequence reconstruction errors on training data ───────────
    log.info("  Computing reconstruction error distribution on training data...")
    all_errors = []
    model.eval()
    chunk_size = 1024
    with torch.no_grad():
        for i in range(0, len(X_tr), chunk_size):
            chunk = X_tr[i:i+chunk_size]
            recon = model(chunk)
            err   = ((recon - chunk) ** 2).mean(dim=(1, 2))
            all_errors.append(err.numpy())
    train_errors = np.concatenate(all_errors)

    return model, train_errors, True   # True = pytorch model


def _train_pca_fallback(seqs: np.ndarray) -> tuple:
    """
    Fallback when PyTorch is not available.
    Uses PCA on flattened sequences to detect anomalies via reconstruction error.
    """
    from sklearn.decomposition import PCA
    log.info("  Training PCA sequence model (fallback)...")
    flat = seqs.reshape(len(seqs), -1)
    pca  = PCA(n_components=min(20, flat.shape[1]), random_state=42)
    pca.fit(flat)
    recon   = pca.inverse_transform(pca.transform(flat))
    errors  = np.mean((flat - recon) ** 2, axis=1)
    log.info(f"  PCA variance explained: {pca.explained_variance_ratio_.sum():.2%}")
    return pca, errors, False   # False = pca fallback


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main(epochs: int = 20, hidden: int = 64,
         window: int = 10, eval_only: bool = False) -> None:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    print(f"\n{'═' * 60}")
    print("  TokenShield — LSTM Autoencoder Training (Signal 8)")
    print(f"{'═' * 60}\n")

    if eval_only:
        if not LSTM_MODEL_PATH.exists():
            log.error("No LSTM model found. Run without --eval-only first.")
            sys.exit(1)
        with open(LSTM_THRESHOLD_PATH) as f:
            meta = json.load(f)
        log.info(f"  LSTM model exists. threshold_95={meta['p95']:.6f}")
        log.info("  Use lstm_infer.py to score individual sequences.")
        return

    # ── Build sequences from NASA HTTP log ────────────────────────────────────
    seqs = build_sequences_from_nasa(RAW_DIR, window=window,
                                     max_sessions=50_000, normal_only=True)
    log.info(f"  Final sequence dataset: {seqs.shape}")

    # ── Train ─────────────────────────────────────────────────────────────────
    model, train_errors, is_pytorch = train_lstm(
        seqs, epochs=epochs, hidden=hidden
    )

    # ── Compute error thresholds ──────────────────────────────────────────────
    p50  = float(np.percentile(train_errors, 50))
    p90  = float(np.percentile(train_errors, 90))
    p95  = float(np.percentile(train_errors, 95))
    p99  = float(np.percentile(train_errors, 99))
    pmax = float(train_errors.max())

    log.info(f"\n  Error distribution on normal training sequences:")
    log.info(f"    p50={p50:.6f}  p90={p90:.6f}  p95={p95:.6f}")
    log.info(f"    p99={p99:.6f}  max={pmax:.6f}")
    log.info(f"    Default alert threshold: p95 = {p95:.6f}")

    # ── Save model ────────────────────────────────────────────────────────────
    log.info("\nSaving LSTM model...")
    if is_pytorch:
        import torch
        torch.save({
            "state_dict":  model.state_dict(),
            "input_dim":   seqs.shape[2],
            "hidden":      hidden,
            "seq_len":     window,
            "model_class": "LSTMAutoencoder",
        }, LSTM_MODEL_PATH)
    else:
        import joblib
        joblib.dump(model, LSTM_MODEL_PATH.with_suffix(".pkl"), compress=3)

    # Save thresholds
    threshold_meta = {
        "model_type":   "pytorch_lstm" if is_pytorch else "pca_fallback",
        "input_dim":    int(seqs.shape[2]),
        "seq_len":      int(window),
        "hidden":       hidden,
        "train_seqs":   len(seqs),
        "p50": p50, "p90": p90, "p95": p95, "p99": p99,
        "alert_threshold": p95,   # flag if recon_error > p95
        "trained_at":   str(pd.Timestamp.now()),
    }
    with open(LSTM_THRESHOLD_PATH, "w") as f:
        json.dump(threshold_meta, f, indent=2)

    log.info(f"  Saved: {LSTM_MODEL_PATH.name}")
    log.info(f"  Saved: {LSTM_THRESHOLD_PATH.name}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("  LSTM AUTOENCODER — TRAINING COMPLETE")
    print(f"{'═' * 60}")
    print(f"  Model type   : {'PyTorch LSTM' if is_pytorch else 'PCA fallback'}")
    print(f"  Sequences    : {len(seqs):,}  (window={window})")
    print(f"  Train p50    : {p50:.6f}")
    print(f"  Train p95    : {p95:.6f}  ← alert threshold")
    print(f"  Train p99    : {p99:.6f}")
    print(f"\n  ▶  Next: python engine/ml/train/train_meta_classifier.py  (Phase 5)")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TokenShield LSTM Autoencoder Trainer")
    parser.add_argument("--epochs",    type=int,   default=20,  help="Training epochs (default 20)")
    parser.add_argument("--hidden",    type=int,   default=64,  help="LSTM hidden size (default 64)")
    parser.add_argument("--window",    type=int,   default=10,  help="Sequence window size (default 10)")
    parser.add_argument("--eval-only", action="store_true",     help="Skip training, show existing model")
    args = parser.parse_args()
    main(epochs=args.epochs, hidden=args.hidden,
         window=args.window, eval_only=args.eval_only)
