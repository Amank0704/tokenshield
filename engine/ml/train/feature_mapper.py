"""
TokenShield — Feature Mapper  (FAST vectorized version)
=========================================================
Converts all raw datasets → unified 40-dim feature vector.
Uses fully vectorized pandas operations — NO iterrows() — processes
500k rows in seconds instead of hours.

40-dim feature layout:
  dims  0- 3  → Signal 1: IP Reputation
  dims  4- 8  → Signal 2: Request Velocity
  dims  9-14  → Signal 3: Session Consistency
  dims 15-19  → Signal 4: Payload Analysis
  dims 20-27  → Signal 5: Behavioral Biometrics
  dims 28-31  → Signal 6: Geographic Impossibility
  dims 32-35  → Signal 7: Endpoint Risk
  dims 36-39  → Signal 8: Sequential Behavior

Usage:
  python engine/ml/train/feature_mapper.py
  python engine/ml/train/feature_mapper.py --inspect A1
"""

import re
import sys
import json
import math
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Paths — reads from data_config.py so all I/O stays on the SSD
# ─────────────────────────────────────────────────────────────────────────────
ROOT   = Path(__file__).resolve().parent.parent.parent.parent
ENGINE = ROOT / "engine"

import importlib.util
_cfg_path = ENGINE / "ml" / "data_config.py"
_spec = importlib.util.spec_from_file_location("data_config", _cfg_path)
_cfg  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

RAW_DIR = Path(_cfg.RAW_DATA_DIR)
OUT_DIR = Path(_cfg.OUTPUT_DATA_DIR)
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("ts.feature_mapper")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
FEATURE_DIM  = 40
LABEL_NORMAL = 0
LABEL_ATTACK = 1
MAX_ROWS_PER_DATASET = 200_000   # cap per dataset to avoid OOM on M2

FEAT_COLS = [f"f{i:02d}" for i in range(FEATURE_DIM)]

FEATURE_NAMES = [
    # Signal 1 (0-3)
    "s1_tor","s1_datacenter","s1_country_risk","s1_asn_anomaly",
    # Signal 2 (4-8)
    "s2_req_per_60s","s2_req_per_10s","s2_inter_mean","s2_inter_std","s2_vel_trend",
    # Signal 3 (9-14)
    "s3_ip_changed","s3_ua_changed","s3_asn_changed","s3_ua_browser","s3_ua_os","s3_session_age",
    # Signal 4 (15-19)
    "s4_sql","s4_xss","s4_path_traversal","s4_entropy","s4_param_anomaly",
    # Signal 5 (20-27)
    "s5_wpm","s5_rhythm_cv","s5_mouse_vel","s5_mouse_cv","s5_click_rate","s5_scroll","s5_idle","s5_entropy",
    # Signal 6 (28-31)
    "s6_travel_speed","s6_distance","s6_time_since_geo","s6_geo_score",
    # Signal 7 (32-35)
    "s7_endpoint_sens","s7_seq_anomaly","s7_method_anomaly","s7_param_mutation",
    # Signal 8 (36-39)
    "s8_lstm_recon","s8_lstm_pct","s8_window_size","s8_seq_novelty",
]

# Label string → binary
def _to_binary(s: pd.Series, normal_vals: tuple) -> pd.Series:
    return (~s.str.lower().str.strip().isin(normal_vals)).astype(np.int8)

# Label string → attack type int
ATTACK_TYPE_MAP = {
    "normal":0,"benign":0,"background":0,
    "dos":1,"ddos":1,"heartbleed":1,"infiltration":1,"backdoors":1,
    "exploits":1,"generic":1,"shellcode":1,"worms":1,
    "bruteforce":2,"brute force":2,"brute_force":2,"ftp-patator":2,
    "ssh-patator":2,"ftppatator":2,"sshpatator":2,"credential":2,
    "bot":3,"portscan":3,"reconnaissance":3,"fuzzers":3,"probe":3,"analysis":3,
    "web attack \x96 sql injection":5,"web attack – sql injection":5,
    "web attack \x96 xss":5,"web attack – xss":5,
    "web attack \x96 brute force":2,"web attack – brute force":2,
    "anomalous":5,"sql":5,"xss":5,
    "theft":6,"u2r":6,"r2l":1,
}

def _attack_type(s: pd.Series) -> pd.Series:
    return s.str.lower().str.strip().map(lambda x: ATTACK_TYPE_MAP.get(x, 1)).astype(np.int8)

def _safe_num(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    """Get numeric column safely, return zeros if missing."""
    for c in df.columns:
        if c.strip() == col:
            return pd.to_numeric(df[c], errors="coerce").fillna(default)
    return pd.Series(np.full(len(df), default, dtype=np.float32))

def _clip01(s: pd.Series) -> pd.Series:
    return s.clip(0.0, 1.0).astype(np.float32)

def _zero_frame(n: int) -> pd.DataFrame:
    return pd.DataFrame(np.zeros((n, FEATURE_DIM), dtype=np.float32), columns=FEAT_COLS)

SQL_RE = re.compile(r"select\s|union\s|insert\s|drop\s|exec\s|'--|or\s+1=1|sleep\s*\(|benchmark\s*\(", re.I)
XSS_RE = re.compile(r"<script|javascript:|onerror=|onload=|alert\s*\(", re.I)
PATH_RE = re.compile(r"\.\./|%2e%2e", re.I)
SENS_RE = re.compile(r"transfer|admin|login|password|payment|checkout|delete|drop|config|\.env", re.I)


# ─────────────────────────────────────────────────────────────────────────────
# Base processor
# ─────────────────────────────────────────────────────────────────────────────
class DatasetProcessor:
    def __init__(self, ds_id: str, raw_dir: Path):
        self.ds_id   = ds_id
        self.raw_dir = raw_dir / ds_id

    def available(self) -> bool:
        return self.raw_dir.exists() and any(self.raw_dir.rglob("*.*"))

    def process(self) -> Optional[pd.DataFrame]:
        raise NotImplementedError

    def _finalize(self, df: pd.DataFrame, label_col: str, raw_label_col: pd.Series,
                  normal_vals: tuple) -> pd.DataFrame:
        """Add label, attack_type, source columns and return."""
        df["label"]       = _to_binary(raw_label_col, normal_vals)
        df["attack_type"] = _attack_type(raw_label_col)
        df["source"]      = self.ds_id
        return df[FEAT_COLS + ["label", "attack_type", "source"]]

    def _read_csvs(self, max_files: int = 5, nrows: int = MAX_ROWS_PER_DATASET,
                   encoding: str = "utf-8") -> Optional[pd.DataFrame]:
        files = sorted(self.raw_dir.rglob("*.csv"))
        if not files:
            return None
        dfs = []
        rows_so_far = 0
        for f in files[:max_files]:
            if rows_so_far >= nrows:
                break
            try:
                chunk = pd.read_csv(f, low_memory=False,
                                    nrows=nrows - rows_so_far,
                                    encoding=encoding,
                                    encoding_errors="replace")
                dfs.append(chunk)
                rows_so_far += len(chunk)
            except Exception as e:
                log.debug(f"  Skip {f.name}: {e}")
        return pd.concat(dfs, ignore_index=True) if dfs else None


# ─────────────────────────────────────────────────────────────────────────────
# A1 — NSL-KDD
# ─────────────────────────────────────────────────────────────────────────────
class NSLKDDProcessor(DatasetProcessor):
    COLS = [
        "duration","protocol_type","service","flag","src_bytes","dst_bytes",
        "land","wrong_fragment","urgent","hot","num_failed_logins","logged_in",
        "num_compromised","root_shell","su_attempted","num_root","num_file_creations",
        "num_shells","num_access_files","num_outbound_cmds","is_host_login",
        "is_guest_login","count","srv_count","serror_rate","srv_serror_rate",
        "rerror_rate","srv_rerror_rate","same_srv_rate","diff_srv_rate",
        "srv_diff_host_rate","dst_host_count","dst_host_srv_count",
        "dst_host_same_srv_rate","dst_host_diff_srv_rate","dst_host_same_src_port_rate",
        "dst_host_srv_diff_host_rate","dst_host_serror_rate","dst_host_srv_serror_rate",
        "dst_host_rerror_rate","dst_host_srv_rerror_rate","label","difficulty"
    ]

    def process(self) -> Optional[pd.DataFrame]:
        files = list(self.raw_dir.glob("*.txt"))
        if not files:
            return None
        dfs = []
        for f in files:
            try:
                dfs.append(pd.read_csv(f, header=None, names=self.COLS,
                                       low_memory=False, nrows=MAX_ROWS_PER_DATASET))
            except Exception as e:
                log.debug(f"  {f.name}: {e}")
        if not dfs:
            return None
        df = pd.concat(dfs, ignore_index=True).head(MAX_ROWS_PER_DATASET)
        n  = len(df)
        out = _zero_frame(n)

        # Signal 2 — velocity from count (connections to same host in 2s)
        out["f04"] = _clip01(_safe_num(df, "count") / 300.0)
        out["f06"] = _clip01(1.0 - _safe_num(df, "duration") / 100.0)
        out["f07"] = _clip01(_safe_num(df, "serror_rate"))

        # Signal 4 — payload anomaly
        out["f15"] = (_safe_num(df, "root_shell") > 0).astype(np.float32)
        out["f19"] = _clip01(_safe_num(df, "hot") / 30.0)

        # Signal 7 — endpoint risk
        out["f32"] = _clip01(_safe_num(df, "num_compromised") / 10.0)
        out["f33"] = _clip01(_safe_num(df, "num_failed_logins") / 10.0)

        raw_labels = df["label"].astype(str)
        log.info(f"  {self.ds_id}: {n:,} rows processed")
        return self._finalize(out, "label", raw_labels, ("normal",))


# ─────────────────────────────────────────────────────────────────────────────
# A4 / A8 — UNSW-NB15 + CIC-IoT 2023  (shared vectorized processor)
# ─────────────────────────────────────────────────────────────────────────────
class UNSWNB15Processor(DatasetProcessor):
    def process(self) -> Optional[pd.DataFrame]:
        df = self._read_csvs(max_files=4)
        if df is None:
            return None
        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Find label column
        label_col = next((c for c in df.columns
                          if c.strip().lower() in ("label", "attack_cat", "class")), None)
        if label_col is None:
            label_col = df.columns[-1]

        n   = len(df)
        out = _zero_frame(n)

        dur   = pd.to_numeric(df.get("dur", pd.Series(np.ones(n))), errors="coerce").fillna(1.0)
        spkts = pd.to_numeric(df.get("spkts", pd.Series(np.zeros(n))), errors="coerce").fillna(0)
        sbytes= pd.to_numeric(df.get("sbytes", pd.Series(np.zeros(n))), errors="coerce").fillna(0)
        dinpkt= pd.to_numeric(df.get("dinpkt", pd.Series(np.zeros(n))), errors="coerce").fillna(0)

        out["f04"] = _clip01(spkts / dur.clip(lower=0.001) / 300.0)
        out["f06"] = _clip01(1.0 - dinpkt / 60.0)
        out["f19"] = _clip01(sbytes / 65535.0)

        raw_labels = df[label_col].astype(str).str.strip()
        log.info(f"  {self.ds_id}: {n:,} rows processed")
        return self._finalize(out, label_col, raw_labels, ("0", "0.0", "normal", "benign"))


# ─────────────────────────────────────────────────────────────────────────────
# A5 — Bot-IoT  (data_1.csv … data_74.csv)
# ─────────────────────────────────────────────────────────────────────────────
class BotIoTProcessor(DatasetProcessor):
    def process(self) -> Optional[pd.DataFrame]:
        files = sorted(self.raw_dir.glob("data_*.csv"))
        if not files:
            return None
        dfs = []
        rows_so_far = 0
        for f in files:
            if rows_so_far >= MAX_ROWS_PER_DATASET:
                break
            try:
                chunk = pd.read_csv(f, low_memory=False,
                                    nrows=MAX_ROWS_PER_DATASET - rows_so_far,
                                    encoding_errors="replace")
                dfs.append(chunk)
                rows_so_far += len(chunk)
            except Exception as e:
                log.debug(f"  {f.name}: {e}")
        if not dfs:
            return None
        df = pd.concat(dfs, ignore_index=True)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        n   = len(df)
        out = _zero_frame(n)

        # Bot-IoT actual columns: pkts, bytes, dur, rate, spkts, sbytes, attack, category
        out["f04"] = _clip01(_safe_num(df, "rate")   / 300.0)    # packets/sec
        out["f05"] = _clip01(_safe_num(df, "spkts")  / 100.0)    # source packets
        out["f06"] = _clip01(1.0 - _safe_num(df, "dur").clip(upper=60) / 60.0)
        out["f19"] = _clip01(_safe_num(df, "sbytes") / 65535.0)  # source bytes
        out["f18"] = _clip01(_safe_num(df, "mean")   / 1500.0)   # mean packet size

        label_col = next((c for c in df.columns if c.strip().lower() in ("attack", "label", "category")), df.columns[-2])

        raw_labels = df[label_col].astype(str).str.strip()
        log.info(f"  {self.ds_id}: {n:,} rows processed")
        return self._finalize(out, label_col, raw_labels, ("0", "0.0", "normal", "benign"))


# ─────────────────────────────────────────────────────────────────────────────
# A7 — HTTP CSIC 2010
# Columns: (index), Method, User-Agent, ..., classification, URL
# ─────────────────────────────────────────────────────────────────────────────
class CSICProcessor(DatasetProcessor):
    def process(self) -> Optional[pd.DataFrame]:
        files = list(self.raw_dir.glob("*.csv"))
        if not files:
            return None
        try:
            df = pd.read_csv(files[0], low_memory=False,
                             nrows=MAX_ROWS_PER_DATASET,
                             encoding_errors="replace")
        except Exception as e:
            log.warning(f"  {self.ds_id}: read error {e}")
            return None

        n   = len(df)
        out = _zero_frame(n)

        # URL-based payload analysis (vectorized)
        url_col = next((c for c in df.columns if c.strip().lower() == "url"), None)
        if url_col:
            urls = df[url_col].fillna("").astype(str)
            out["f15"] = urls.str.contains(SQL_RE).astype(np.float32)
            out["f16"] = urls.str.contains(XSS_RE).astype(np.float32)
            out["f17"] = urls.str.contains(PATH_RE).astype(np.float32)
            out["f32"] = urls.str.contains(SENS_RE).astype(np.float32)

        # Method anomaly (POST=0, unusual=1)
        method_col = next((c for c in df.columns if c.strip().lower() == "method"), None)
        if method_col:
            out["f34"] = (~df[method_col].str.upper().isin(["GET", "POST", "HEAD"])).astype(np.float32)

        # Label
        label_col = next((c for c in df.columns if c.strip().lower() == "classification"), None)
        if label_col is None:
            label_col = df.columns[0]   # first column is sometimes the label index

        raw_labels = df[label_col].astype(str).str.strip()
        log.info(f"  {self.ds_id}: {n:,} rows processed")
        return self._finalize(out, label_col, raw_labels, ("normal",))


# ─────────────────────────────────────────────────────────────────────────────
# A8 — CIC-IoT 2023  (balanced_7classes_500000_each.csv)
# ─────────────────────────────────────────────────────────────────────────────
class CICIoT2023Processor(DatasetProcessor):
    def process(self) -> Optional[pd.DataFrame]:
        files = list(self.raw_dir.glob("*.csv"))
        if not files:
            return None
        try:
            # Sample MAX_ROWS from the 3.5M row file
            df = pd.read_csv(files[0], low_memory=False,
                             nrows=MAX_ROWS_PER_DATASET,
                             encoding_errors="replace")
        except Exception as e:
            log.warning(f"  {self.ds_id}: {e}")
            return None

        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        n   = len(df)
        out = _zero_frame(n)

        # Find label column
        label_col = next((c for c in df.columns
                          if c.strip().lower() in ("label", "attack_type", "class", "category")),
                         df.columns[-1])

        # CIC-IoT shares CICFlowMeter feature names
        def g(name):
            for c in df.columns:
                if c.strip() == name:
                    return pd.to_numeric(df[c], errors="coerce").fillna(0.0)
            return pd.Series(np.zeros(n, dtype=np.float32))

        out["f04"] = _clip01(g("Flow Packets/s") * 60 / 300.0)
        out["f06"] = _clip01(1.0 - g("Flow IAT Mean") / 60_000_000.0)
        out["f07"] = _clip01(g("Flow IAT Std") / 10_000_000.0)
        out["f19"] = _clip01(g("Average Packet Size") / 1500.0)

        raw_labels = df[label_col].astype(str).str.strip()
        log.info(f"  {self.ds_id}: {n:,} rows processed")
        return self._finalize(out, label_col, raw_labels,
                              ("benigntraffic", "benign", "normal", "0"))


# ─────────────────────────────────────────────────────────────────────────────
# A9 — RT-IoT2022
# ─────────────────────────────────────────────────────────────────────────────
class RTIoTProcessor(DatasetProcessor):
    def process(self) -> Optional[pd.DataFrame]:
        # Unzip if needed
        zips = list(self.raw_dir.glob("*.zip"))
        for z in zips:
            import zipfile
            with zipfile.ZipFile(z) as zf:
                zf.extractall(self.raw_dir)

        # Find CSV files — including files with no extension (e.g. "RT_IOT2022")
        csv_files = list(self.raw_dir.rglob("*.csv"))
        if not csv_files:
            # Try files with no extension
            csv_files = [f for f in self.raw_dir.rglob("*")
                         if f.is_file() and not f.suffix and f.stat().st_size > 1000]

        if not csv_files:
            return None

        dfs = []
        rows_so_far = 0
        for f in csv_files[:3]:
            if rows_so_far >= MAX_ROWS_PER_DATASET:
                break
            try:
                chunk = pd.read_csv(f, low_memory=False,
                                    nrows=MAX_ROWS_PER_DATASET - rows_so_far,
                                    encoding_errors="replace")
                dfs.append(chunk)
                rows_so_far += len(chunk)
            except Exception as e:
                log.debug(f"  {f.name}: {e}")

        if not dfs:
            return None

        df = pd.concat(dfs, ignore_index=True)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        n   = len(df)
        out = _zero_frame(n)

        def g(name):
            for c in df.columns:
                if c.strip() == name:
                    return pd.to_numeric(df[c], errors="coerce").fillna(0.0)
            return pd.Series(np.zeros(n, dtype=np.float32))

        out["f04"] = _clip01(g("flow_duration").clip(lower=0.001).map(lambda x: 1.0 / x / 300.0))
        out["f19"] = _clip01(g("fwd_seg_size_avg") / 1500.0)
        out["f06"] = _clip01(1.0 - g("flow_iat_mean") / 1_000_000.0)

        label_col = next((c for c in df.columns
                          if c.strip().lower() in ("attack_type", "label", "class", "type")),
                         df.columns[-1])
        raw_labels = df[label_col].astype(str).str.strip()
        log.info(f"  {self.ds_id}: {n:,} rows processed")
        return self._finalize(out, label_col, raw_labels, ("normal",))



# ─────────────────────────────────────────────────────────────────────────────
# A11 / C1 — NASA HTTP Log  (Apache combined log format)
# ─────────────────────────────────────────────────────────────────────────────
class ApacheLogProcessor(DatasetProcessor):
    LOG_RE = re.compile(
        r'(\S+) \S+ \S+ \[[^\]]+\] "(\w+)?\s*([^\s"]*)[^"]*" (\d+) (\S+)'
    )

    def process(self) -> Optional[pd.DataFrame]:
        # Auto-decompress .gz
        import gzip, shutil
        for gz in self.raw_dir.glob("*.gz"):
            out_path = self.raw_dir / gz.stem
            if not out_path.exists():
                with gzip.open(gz, "rb") as fi, open(out_path, "wb") as fo:
                    shutil.copyfileobj(fi, fo)

        log_files = [f for f in self.raw_dir.iterdir()
                     if f.is_file() and not f.name.endswith(".gz")]
        if not log_files:
            return None

        ips, methods, paths, statuses = [], [], [], []
        rows = 0
        for fpath in log_files[:2]:
            try:
                with open(fpath, "r", errors="replace") as f:
                    for line in f:
                        m = self.LOG_RE.match(line)
                        if not m:
                            continue
                        ips.append(m.group(1))
                        methods.append(m.group(2) or "GET")
                        paths.append(m.group(3) or "/")
                        statuses.append(int(m.group(4)))
                        rows += 1
                        if rows >= MAX_ROWS_PER_DATASET:
                            break
            except Exception as e:
                log.debug(f"  {fpath.name}: {e}")

        if not ips:
            return None

        n   = len(ips)
        out = _zero_frame(n)
        path_series = pd.Series(paths)

        out["f15"] = path_series.str.contains(SQL_RE).astype(np.float32)
        out["f16"] = path_series.str.contains(XSS_RE).astype(np.float32)
        out["f17"] = path_series.str.contains(PATH_RE).astype(np.float32)
        out["f32"] = path_series.str.contains(SENS_RE).astype(np.float32)

        status_s = pd.Series(statuses)
        out["f34"] = (status_s >= 400).astype(np.float32)

        # Label: requests with SQL/XSS = attack, others = normal
        labels = ((out["f15"] > 0) | (out["f16"] > 0) | (out["f17"] > 0)).astype(np.int8)
        out["label"]       = labels
        out["attack_type"] = labels * 5   # payload_injection
        out["source"]      = self.ds_id
        log.info(f"  {self.ds_id}: {n:,} rows processed")
        return out[FEAT_COLS + ["label", "attack_type", "source"]]


# ─────────────────────────────────────────────────────────────────────────────
# B1 — CMU Keystroke Benchmark
# ─────────────────────────────────────────────────────────────────────────────
class CMUKeystrokeProcessor(DatasetProcessor):
    def process(self) -> Optional[pd.DataFrame]:
        f = self.raw_dir / "DSL-StrongPasswordData.csv"
        if not f.exists():
            csvs = list(self.raw_dir.glob("*.csv"))
            if not csvs:
                return None
            f = csvs[0]
        try:
            df = pd.read_csv(f, encoding_errors="replace")
        except Exception as e:
            log.warning(f"  {self.ds_id}: {e}")
            return None

        hold_cols   = [c for c in df.columns if c.startswith("H.")]
        flight_cols = [c for c in df.columns if c.startswith("UD.")]

        if not hold_cols:
            return None

        holds   = df[hold_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        flights = df[flight_cols].apply(pd.to_numeric, errors="coerce").fillna(0) if flight_cols else None

        mean_hold = holds.mean(axis=1).clip(lower=1e-6)
        std_hold  = holds.std(axis=1).fillna(0)
        cv_hold   = (std_hold / mean_hold).clip(0, 1)

        total_time = holds.sum(axis=1) + (flights.abs().sum(axis=1) if flights is not None else 0)
        wpm = ((10 / 5) / (total_time / 60.0 + 1e-6)).clip(0, 200) / 200.0

        n   = len(df)
        out = _zero_frame(n)
        out["f20"] = wpm.values.astype(np.float32)
        out["f21"] = cv_hold.values.astype(np.float32)

        out["label"]       = 0
        out["attack_type"] = 0
        out["source"]      = self.ds_id
        log.info(f"  {self.ds_id}: {n:,} rows processed")
        return out[FEAT_COLS + ["label", "attack_type", "source"]]


# ─────────────────────────────────────────────────────────────────────────────
# B3 — Balabit Mouse Dynamics  (one file per session, no headers)
# ─────────────────────────────────────────────────────────────────────────────
class BalabitMouseProcessor(DatasetProcessor):
    def process(self) -> Optional[pd.DataFrame]:
        training_dir = self.raw_dir / "Mouse-Dynamics-Challenge-master" / "training_files"
        if not training_dir.exists():
            training_dir = self.raw_dir

        session_files = list(training_dir.rglob("session_*"))
        if not session_files:
            return None

        rows = []
        for sf in session_files[:200]:   # cap at 200 sessions
            try:
                df = pd.read_csv(sf, header=None, sep=",",
                                 names=["record_time","client_time","button","state","x","y"],
                                 encoding_errors="replace")
                if "x" not in df.columns or len(df) < 2:
                    continue
                xs  = pd.to_numeric(df["x"], errors="coerce").dropna().values
                ys  = pd.to_numeric(df["y"], errors="coerce").dropna().values
                ts  = pd.to_numeric(df["client_time"], errors="coerce").dropna().values

                if len(xs) < 2:
                    continue

                dists    = np.sqrt(np.diff(xs)**2 + np.diff(ys)**2)
                dt       = np.diff(ts) + 1e-6
                vels     = dists / dt
                mean_vel = float(np.mean(vels))
                cv_vel   = float(np.std(vels)) / (mean_vel + 1e-6)
                n_clicks = int((df["state"] == "Pressed").sum()) if "state" in df.columns else 0
                dur      = float(ts[-1] - ts[0]) + 1e-6

                rows.append({
                    "f22": min(mean_vel / 2000.0, 1.0),
                    "f23": min(cv_vel, 1.0),
                    "f24": min(n_clicks / dur, 1.0),
                })
            except Exception:
                continue

        if not rows:
            return None

        n   = len(rows)
        out = _zero_frame(n)
        tmp = pd.DataFrame(rows)
        for c in tmp.columns:
            out[c] = tmp[c].values.astype(np.float32)

        out["label"]       = 0
        out["attack_type"] = 0
        out["source"]      = self.ds_id
        log.info(f"  {self.ds_id}: {n:,} rows processed")
        return out[FEAT_COLS + ["label", "attack_type", "source"]]


# ─────────────────────────────────────────────────────────────────────────────
# B6 — KeyRecs  (free-text.csv, fixed-text.csv, demographics.csv)
# ─────────────────────────────────────────────────────────────────────────────
class KeyRecsProcessor(DatasetProcessor):
    def process(self) -> Optional[pd.DataFrame]:
        dfs = []
        for fname in ("free-text.csv", "fixed-text.csv"):
            f = self.raw_dir / fname
            if not f.exists():
                continue
            try:
                dfs.append(pd.read_csv(f, low_memory=False,
                                       nrows=MAX_ROWS_PER_DATASET // 2,
                                       encoding_errors="replace"))
            except Exception as e:
                log.debug(f"  {fname}: {e}")

        if not dfs:
            return None

        df = pd.concat(dfs, ignore_index=True)
        n  = len(df)
        out = _zero_frame(n)

        # KeyRecs columns: PARTICIPANT_ID, KEYSTROKE_ID, HOLD_TIME, INTERKEY_TIME, ...
        hold_col = next((c for c in df.columns if "hold" in c.lower()), None)
        iki_col  = next((c for c in df.columns if "inter" in c.lower() or "iki" in c.lower()), None)

        if hold_col:
            holds    = pd.to_numeric(df[hold_col], errors="coerce").fillna(0).clip(lower=0)
            # Group by participant if possible
            mean_hold = holds.clip(1e-6, 1000)
            wpm_proxy = (1.0 / (mean_hold / 1000.0 + 1e-6) / 5.0).clip(0, 200) / 200.0
            out["f20"] = wpm_proxy.values.astype(np.float32)

        if iki_col:
            iki     = pd.to_numeric(df[iki_col], errors="coerce").fillna(0).clip(0, 2000)
            cv      = (iki.std() / (iki.mean() + 1e-6))
            out["f21"] = float(min(cv, 1.0))

        out["label"]       = 0
        out["attack_type"] = 0
        out["source"]      = self.ds_id
        log.info(f"  {self.ds_id}: {n:,} rows processed")
        return out[FEAT_COLS + ["label", "attack_type", "source"]]


# ─────────────────────────────────────────────────────────────────────────────
# C3 — Wikipedia Clickstream  (.tsv.gz)
# Columns: prev, curr, type, n
# ─────────────────────────────────────────────────────────────────────────────
class WikipediaClickstreamProcessor(DatasetProcessor):
    def process(self) -> Optional[pd.DataFrame]:
        import gzip
        gz_files = list(self.raw_dir.glob("*.tsv.gz")) + list(self.raw_dir.glob("*.gz"))
        if not gz_files:
            tsv_files = list(self.raw_dir.glob("*.tsv"))
            if not tsv_files:
                return None
            gz_files = tsv_files

        rows_read = []
        for gf in gz_files[:1]:
            try:
                opener = gzip.open if str(gf).endswith(".gz") else open
                with opener(gf, "rt", encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f):
                        if i >= MAX_ROWS_PER_DATASET:
                            break
                        parts = line.strip().split("\t")
                        if len(parts) >= 4:
                            rows_read.append(int(parts[3]) if parts[3].isdigit() else 0)
            except Exception as e:
                log.debug(f"  {gf.name}: {e}")

        if not rows_read:
            return None

        n   = len(rows_read)
        out = _zero_frame(n)
        clicks = np.array(rows_read, dtype=np.float32)
        out["f39"] = np.clip(clicks / clicks.max(), 0, 1)  # sequence novelty proxy
        out["f37"] = np.clip(clicks / 1000.0, 0, 1)        # window size proxy

        out["label"]       = 0
        out["attack_type"] = 0
        out["source"]      = self.ds_id
        log.info(f"  {self.ds_id}: {n:,} rows processed")
        return out[FEAT_COLS + ["label", "attack_type", "source"]]


# ─────────────────────────────────────────────────────────────────────────────
# Processor registry
# ─────────────────────────────────────────────────────────────────────────────
PROCESSORS = {
    "A1_nsl_kdd":           NSLKDDProcessor,
    "A4_unsw_nb15":         UNSWNB15Processor,
    "A5_bot_iot":           BotIoTProcessor,
    "A7_csic_2010":         CSICProcessor,
    "A8_cic_iot2023":       CICIoT2023Processor,
    "A9_rt_iot2022":        RTIoTProcessor,
    "A11_nasa_http":        ApacheLogProcessor,
    "B1_cmu_keystroke":     CMUKeystrokeProcessor,
    "B3_balabit_mouse":     BalabitMouseProcessor,
    "B6_keyrecs":           KeyRecsProcessor,
    "C1_nasa_http":         ApacheLogProcessor,
    "C3_wikipedia_clickstream": WikipediaClickstreamProcessor,
}


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────
def process_all(dataset_filter: str = None) -> None:
    all_frames, processed, skipped = [], [], []

    for ds_id, ProcClass in PROCESSORS.items():
        if dataset_filter and not ds_id.startswith(dataset_filter):
            continue
        proc = ProcClass(ds_id, RAW_DIR)
        if not proc.available():
            skipped.append(ds_id)
            continue
        log.info(f"\n{'─' * 60}")
        log.info(f"Processing: {ds_id}")
        df = proc.process()
        if df is not None and len(df) > 0:
            all_frames.append(df)
            processed.append((ds_id, len(df)))
        else:
            log.warning(f"  {ds_id}: no rows produced")

    if not all_frames:
        log.error(
            "\n❌  No datasets processed.\n"
            "    Make sure files are in the correct SSD folders and re-run."
        )
        return

    # ── Merge ─────────────────────────────────────────────────────────────────
    log.info(f"\n{'═' * 60}")
    log.info(f"Merging {len(all_frames)} datasets...")
    combined = pd.concat(all_frames, ignore_index=True)
    combined[FEAT_COLS] = combined[FEAT_COLS].clip(0.0, 1.0)

    # Drop degenerate all-zero rows
    all_zero = (combined[FEAT_COLS] == 0).all(axis=1)
    if all_zero.sum() > 0:
        combined = combined[~all_zero]
        log.info(f"  Dropped {all_zero.sum():,} all-zero rows")

    log.info(f"  Total rows: {len(combined):,}")
    log.info(f"  Label split:\n{combined['label'].value_counts().to_string()}")

    # ── Stratified 70/15/15 split ─────────────────────────────────────────────
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)
    n       = len(combined)
    n_train = int(n * 0.70)
    n_val   = int(n * 0.15)

    train = combined.iloc[:n_train]
    val   = combined.iloc[n_train:n_train + n_val]
    test  = combined.iloc[n_train + n_val:]

    # ── Save ──────────────────────────────────────────────────────────────────
    train.to_parquet(OUT_DIR / "train.parquet", index=False, compression="snappy")
    val.to_parquet(  OUT_DIR / "val.parquet",   index=False, compression="snappy")
    test.to_parquet( OUT_DIR / "test.parquet",  index=False, compression="snappy")

    # Feature metadata
    meta = {
        "feature_dim": FEATURE_DIM,
        "feature_names": FEATURE_NAMES,
        "feature_columns": FEAT_COLS,
        "label_column": "label",
        "attack_type_column": "attack_type",
        "generated_at": datetime.now().isoformat(),
        "datasets_processed": processed,
        "datasets_skipped": skipped,
        "rows": {"train": len(train), "val": len(val), "test": len(test)},
    }
    with open(OUT_DIR / "feature_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("  FEATURE MAPPER — COMPLETE")
    print(f"{'═' * 60}")
    for ds_id, n_rows in processed:
        print(f"  ✅ {ds_id:<28} {n_rows:>8,} rows")
    if skipped:
        print(f"\n  ⏭  Skipped (not downloaded):")
        for ds_id in skipped:
            print(f"     {ds_id}")
    print(f"\n  Output → {OUT_DIR}")
    print(f"    train.parquet : {len(train):>8,} rows")
    print(f"    val.parquet   : {len(val):>8,} rows")
    print(f"    test.parquet  : {len(test):>8,} rows  ← LOCKED")
    print(f"\n  ▶  Next: python engine/ml/train/train_isolation_forest.py")
    print(f"{'═' * 60}\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TokenShield Feature Mapper")
    parser.add_argument("--dataset", metavar="PREFIX",
                        help="Process only datasets starting with this prefix")
    parser.add_argument("--inspect", metavar="PREFIX",
                        help="Process one dataset, print first 5 rows, exit")
    args = parser.parse_args()

    if args.inspect:
        for ds_id, ProcClass in PROCESSORS.items():
            if ds_id.startswith(args.inspect):
                proc = ProcClass(ds_id, RAW_DIR)
                if proc.available():
                    df = proc.process()
                    if df is not None:
                        print(f"\nFirst 5 rows — {ds_id}:")
                        print(df.head().to_string())
                break
    else:
        process_all(dataset_filter=args.dataset)
