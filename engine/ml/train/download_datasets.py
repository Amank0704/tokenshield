"""
TokenShield — Phase 1: Dataset Downloader
==========================================
Downloads all 23 real public datasets used to train TokenShield ML models.

Usage:
  python engine/ml/train/download_datasets.py            # download all
  python engine/ml/train/download_datasets.py --groups A # only network datasets
  python engine/ml/train/download_datasets.py --list     # see all datasets
  python engine/ml/train/download_datasets.py --dataset A1_nsl_kdd  # one dataset

Groups:
  A  (12 datasets) — Network Intrusion & Attack Traffic  → Signals 1-4, 6-7
  B  (7 datasets)  — Behavioral Biometrics               → Signal 5
  C  (4 datasets)  — Session Sequences & Web Navigation  → Signal 8 / LSTM

Total: 23 datasets | ~2.4 GB | ~5.7 million training rows
"""

import os
import sys
import json
import gzip
import shutil
import tarfile
import zipfile
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

import requests

# ─────────────────────────────────────────────────────────────────────────────
# Paths — reads from data_config.py so everything stays on the SSD
# ─────────────────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).resolve().parent.parent.parent.parent   # tokenshield/
ENGINE  = ROOT / "engine"

# Load SSD config
import importlib.util, sys as _sys
_cfg_path = ENGINE / "ml" / "data_config.py"
_spec = importlib.util.spec_from_file_location("data_config", _cfg_path)
_cfg  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

RAW_DIR  = Path(_cfg.RAW_DATA_DIR)
LOG_FILE = RAW_DIR.parent / "download_log.json"
RAW_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ENGINE / "ml" / "data" / "download.log"),
    ]
)
log = logging.getLogger("ts.download")


# ─────────────────────────────────────────────────────────────────────────────
# Dataset Registry — all 23 real public datasets
# ─────────────────────────────────────────────────────────────────────────────
DATASETS = {

    # ═════════════════════════════════════════════════════════════════════════
    # GROUP A — Network Intrusion & Attack Traffic
    # Source: Real packet captures / flow records from actual networks
    # Mapped to: Signals 1 (IP), 2 (Velocity), 3 (Session), 4 (Payload), 6 (Geo), 7 (Endpoint)
    # ═════════════════════════════════════════════════════════════════════════

    "A1_nsl_kdd": {
        "group": "A",
        "name": "NSL-KDD",
        "institution": "University of New Brunswick",
        "mode": "direct",
        "urls": [
            "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain+.txt",
            "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest+.txt",
        ],
        "filenames": ["KDDTrain+.txt", "KDDTest+.txt"],
        "format": "kdd_csv",
        "label_column": "label",        # last col, no header
        "label_normal": "normal",
        "size_mb": 25,
        "signals": [1, 2, 3, 4, 6, 7],
        "notes": "41 features, 125k normal + 59 attack types. Canonical IDS baseline.",
    },

    "A2_cic_ids2017": {
        "group": "A",
        "name": "CIC-IDS2017",
        "institution": "University of New Brunswick",
        "mode": "manual",
        "manual_url": "https://www.unb.ca/cic/datasets/ids-2017.html",
        "manual_instructions": (
            "1. Visit https://www.unb.ca/cic/datasets/ids-2017.html\n"
            "2. Click 'Download Dataset' → enter your email → confirm\n"
            "3. Download 'MachineLearningCSV.zip' (~450MB)\n"
            "4. Extract all CSV files into: engine/ml/data/raw/A2_cic_ids2017/\n"
            "   Files: Monday-WorkingHours.pcap_ISCX.csv, Tuesday... Friday..."
        ),
        "format": "cicflowmeter_csv",
        "label_column": " Label",       # note the leading space in CIC headers
        "label_normal": "BENIGN",
        "size_mb": 450,
        "signals": [1, 2, 3, 4, 6, 7],
        "notes": "80 CICFlowMeter features, 7 days, 14 attack types. Priority dataset.",
    },

    "A3_cic_ids2018": {
        "group": "A",
        "name": "CIC-IDS2018",
        "institution": "University of New Brunswick",
        "mode": "manual",
        "manual_url": "https://www.unb.ca/cic/datasets/ids-2018.html",
        "manual_instructions": (
            "1. Visit https://www.unb.ca/cic/datasets/ids-2018.html\n"
            "2. Click 'Download Dataset' → enter email\n"
            "3. Download 'Processed Traffic Data for ML Algorithms.zip'\n"
            "4. Extract. Use ONLY first 3 days to stay under 500MB:\n"
            "   Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv\n"
            "   Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv\n"
            "   Friday-16-02-2018_TrafficForML_CICFlowMeter.csv\n"
            "5. Place in: engine/ml/data/raw/A3_cic_ids2018/"
        ),
        "format": "cicflowmeter_csv",
        "label_column": "Label",
        "label_normal": "BENIGN",
        "size_mb": 500,
        "signals": [1, 2, 3, 4, 6, 7],
        "notes": "10 days, 80 features, adds Infiltration + Botnet. Use 3-day subset.",
    },

    "A4_unsw_nb15": {
        "group": "A",
        "name": "UNSW-NB15",
        "institution": "UNSW Canberra",
        "mode": "kaggle",
        "kaggle_dataset": "mrwellsdavid/unsw-nb15",
        "format": "csv",
        "label_column": "label",
        "label_normal": 0,
        "size_mb": 100,
        "signals": [1, 2, 3, 4, 6, 7],
        "notes": "49 features, 9 attack families. Kaggle mirror is more reliable than UNSW direct.",
    },

    "A5_bot_iot": {
        "group": "A",
        "name": "Bot-IoT 5% Subset",
        "institution": "UNSW Canberra",
        "mode": "kaggle",
        "kaggle_dataset": "vigneshvenkateswaran/bot-iot",
        "format": "csv",
        "label_column": "label",
        "label_normal": 0,
        "size_mb": 1000,
        "signals": [1, 2, 4, 6, 7],
        "notes": "46 features, 4 IoT attack categories. sample_frac=0.05 during processing.",
    },

    "A6_ctu13": {
        "group": "A",
        "name": "CTU-13 Botnet",
        "institution": "Stratosphere Lab, Prague",
        "mode": "kaggle",
        "kaggle_dataset": "dhoogla/ctu13",
        "format": "binetflow",
        "label_column": "Label",
        "label_normal": "BACKGROUND",
        "size_mb": 200,
        "signals": [1, 2, 3, 6],
        "notes": "13 botnet scenarios. Kaggle mirror of Stratosphere Lab CTU-13.",
    },

    "A7_csic_2010": {
        "group": "A",
        "name": "HTTP CSIC 2010",
        "institution": "Spanish National Research Council",
        "mode": "kaggle",
        "kaggle_dataset": "ispangler/csic-2010-web-application-attacks",
        "format": "http_csv",
        "label_column": "classification",
        "label_normal": "Normal",
        "size_mb": 25,
        "signals": [4],
        "notes": "36k normal + 25k anomalous HTTP requests. Best for SQLi/XSS payload training.",
    },

    "A8_cic_iot2023": {
        "group": "A",
        "name": "CIC IoT 2023",
        "institution": "University of New Brunswick",
        "mode": "kaggle",
        "kaggle_dataset": "kibremogesf/kibremoges",
        "manual_url": "https://www.unb.ca/cic/datasets/iotdataset-2023.html",
        "manual_instructions": (
            "1. Visit https://www.unb.ca/cic/datasets/iotdataset-2023.html\n"
            "2. Click 'Download' → select 'CSV files' (not PCAPs)\n"
            "3. Download any 2-3 attack category CSVs (~500MB total)\n"
            "4. Place in: engine/ml/data/raw/A8_cic_iot2023/"
        ),
        "format": "cicflowmeter_csv",
        "label_column": "MappedLabel",
        "label_normal": "Benign",
        "size_mb": 500,
        "signals": [1, 2, 3, 4, 6, 7],
        "notes": "33 attack scenarios on 105 real IoT devices. Most modern CIC dataset.",
    },

    "A9_rt_iot2022": {
        "group": "A",
        "name": "RT-IoT2022",
        "institution": "JSSATE / UCI ML Repository",
        "mode": "direct",
        "urls": [
            "https://archive.ics.uci.edu/static/public/942/rt-iot2022.zip",
        ],
        "filenames": ["rt_iot2022.zip"],
        "format": "csv",
        "label_column": "Attack_type",
        "label_normal": "Normal",
        "size_mb": 160,
        "signals": [1, 2, 3, 6, 7],
        "notes": "Real-time IoT bidirectional traffic with Zeek + Flowmeter features.",
    },

    "A10_cert_insider": {
        "group": "A",
        "name": "CERT Insider Threat v6.2",
        "institution": "Carnegie Mellon University",
        "mode": "manual",
        "manual_url": "https://kilthub.cmu.edu/articles/dataset/Insider_Threat_Test_Dataset/12841247",
        "manual_instructions": (
            "1. Visit https://kilthub.cmu.edu/articles/dataset/Insider_Threat_Test_Dataset/12841247\n"
            "2. Click 'Download All' (no login required for public version)\n"
            "3. Extract and place in: engine/ml/data/raw/A10_cert_insider/\n"
            "   Key files: http.csv, logon.csv, device.csv, email.csv, answers/\n"
            "   answers/ folder contains ground truth (insider_threat labels)"
        ),
        "format": "cert_csv",
        "label_column": "insider",
        "label_normal": 0,
        "size_mb": 500,
        "signals": [2, 3, 7],
        "notes": "HTTP + logon + file + email logs with ground-truth insider threat labels.",
    },

    "A11_nasa_http": {
        "group": "A",
        "name": "NASA HTTP Log 1995",
        "institution": "NASA Kennedy Space Center",
        "mode": "direct",
        "urls": [
            "http://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz",
        ],
        "fallback_urls": [
            "http://ita.ee.lbl.gov/traces/NASA_access_log_Aug95.gz",
        ],
        "filenames": ["NASA_access_log_Jul95.gz"],
        "format": "apache_log",
        "label_column": None,           # normal traffic only — no labels needed
        "label_normal": None,
        "size_mb": 20,
        "signals": [8],
        "notes": "3.5M real Apache log entries. Normal traffic baseline for LSTM Signal 8.",
    },

    "A12_secrepo": {
        "group": "A",
        "name": "SecRepo Honeypot Logs",
        "institution": "SecRepo.com",
        "mode": "manual",
        "manual_url": "https://secrepo.com",
        "manual_instructions": (
            "1. Visit https://secrepo.com and create a free account\n"
            "2. Navigate to 'Log Files' → 'Web Server Logs'\n"
            "3. Download any Apache/Nginx access log files\n"
            "4. Place in: engine/ml/data/raw/A12_secrepo/"
        ),
        "format": "apache_log",
        "label_column": None,
        "label_normal": None,
        "size_mb": 50,
        "signals": [4, 8],
        "notes": "Real honeypot logs. Mix of normal and attack traffic.",
    },

    # ═════════════════════════════════════════════════════════════════════════
    # GROUP B — Behavioral Biometrics
    # Source: Real humans typing/clicking in controlled research studies
    # Mapped to: Signal 5 (Behavioral Biometrics)
    # ═════════════════════════════════════════════════════════════════════════

    "B1_cmu_keystroke": {
        "group": "B",
        "name": "CMU Keystroke Dynamics Benchmark",
        "institution": "Carnegie Mellon University",
        "mode": "direct",
        "urls": [
            "http://www.cs.cmu.edu/~keystroke/DSL-StrongPasswordData.csv",
        ],
        "filenames": ["DSL-StrongPasswordData.csv"],
        "format": "csv",
        "label_column": "subject",
        "label_normal": None,           # all are normal — used for user profiling
        "size_mb": 5,
        "signals": [5],
        "notes": "51 users × 400 password entries. Hold time + inter-key latency. Gold standard.",
    },

    "B2_aalto_keystrokes": {
        "group": "B",
        "name": "Aalto Keystrokes (Kaggle mirror, 10% sample)",
        "institution": "Aalto University, Finland",
        "mode": "kaggle",
        "kaggle_dataset": "ahmedshahriarsakib/keystrokes",
        "format": "aalto_csv",
        "label_column": "PARTICIPANT_ID",
        "label_normal": None,
        "sample_fraction": 0.10,        # use 10% = ~400MB, ~13.6M keystrokes
        "size_mb": 4000,
        "signals": [5],
        "notes": "168,000 volunteers on real keyboards. Use Kaggle mirror (original site 404).",
    },

    "B3_balabit_mouse": {
        "group": "B",
        "name": "Balabit Mouse Dynamics Challenge",
        "institution": "Balabit Corp.",
        "mode": "direct",
        "urls": [
            "https://github.com/balabit/Mouse-Dynamics-Challenge/archive/refs/heads/master.zip",
        ],
        "filenames": ["balabit_mouse_master.zip"],
        "format": "balabit_csv",
        "label_column": "session_id",
        "label_normal": None,
        "size_mb": 200,
        "signals": [5],
        "notes": "10 users, session mouse movements + click timing + velocity.",
    },

    "B4_mendeley_kmt": {
        "group": "B",
        "name": "Behaviour Biometrics KMT (Edge Hill Univ.)",
        "institution": "Edge Hill University",
        "mode": "manual",
        "manual_url": "https://data.mendeley.com/datasets/c4r6c89n6p/1",
        "manual_instructions": (
            "1. Visit https://data.mendeley.com/datasets/c4r6c89n6p/1\n"
            "2. Click 'Download All' (Mendeley requires browser session — script can't auth)\n"
            "3. Extract ZIP and place all CSV files in: engine/ml/data/raw/B4_mendeley_kmt/"
        ),
        "format": "csv",
        "label_column": "participant_id",
        "label_normal": None,
        "size_mb": 30,
        "signals": [5],
        "notes": "Keyboard + Mouse + Touchscreen during simulated online payment task.",
    },

    "B5_mendeley_ueba": {
        "group": "B",
        "name": "Keystroke + Mouse for UEBA",
        "group": "B",
        "name": "Keystroke + Mouse for UEBA",
        "institution": "Mendeley Data",
        "mode": "manual",
        "manual_url": "https://data.mendeley.com/datasets/f78jsh6zp9/2",
        "manual_instructions": (
            "1. Visit https://data.mendeley.com/datasets/f78jsh6zp9/2\n"
            "2. Click 'Download All' (Mendeley requires browser session — script can't auth)\n"
            "3. Place all CSV files in: engine/ml/data/raw/B5_mendeley_ueba/"
        ),
        "format": "csv",
        "label_column": "user_id",
        "label_normal": None,
        "size_mb": 20,
        "signals": [5],
        "notes": "11 users in webchat app. Designed specifically for UEBA research.",
    },

    "B6_keyrecs": {
        "group": "B",
        "name": "KeyRecs Keystroke Dataset 2023",
        "institution": "Zenodo / Academic",
        "mode": "zenodo",
        "zenodo_record_id": "7886743",      # corrected — DOI: 10.5281/zenodo.7886743
        "format": "csv",
        "label_column": "participant_id",
        "label_normal": None,
        "size_mb": 50,
        "signals": [5],
        "notes": "100 participants, fixed + free-text typing, demographic metadata.",
    },

    "B7_greyc": {
        "group": "B",
        "name": "GREYC Keystroke Dataset",
        "institution": "University of Caen Normandie, France",
        "mode": "manual",
        "manual_url": "https://www.epayment.greyc.fr/",
        "manual_instructions": (
            "1. Visit https://www.epayment.greyc.fr/\n"
            "2. Find 'Keystroke Dynamics Datasets' section\n"
            "3. Download the public GREYC-NISLAB dataset (no registration)\n"
            "4. Place in: engine/ml/data/raw/B7_greyc/"
        ),
        "format": "csv",
        "label_column": "user_id",
        "label_normal": None,
        "size_mb": 15,
        "signals": [5],
        "notes": "133 subjects × 5 sessions. Multi-session behavioral drift tracking.",
    },

    # ═════════════════════════════════════════════════════════════════════════
    # GROUP C — Session Sequences & Web Navigation
    # Source: Real web server logs showing how humans navigate
    # Mapped to: Signal 8 (Sequential Behavior / LSTM Autoencoder)
    # ═════════════════════════════════════════════════════════════════════════

    "C1_nasa_http": {
        "group": "C",
        "name": "NASA HTTP Log 1995 (sequence use)",
        "institution": "NASA Kennedy Space Center",
        "mode": "direct",
        "urls": [
            "http://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz",
        ],
        "filenames": ["NASA_access_log_Jul95.gz"],
        "format": "apache_log",
        "label_column": None,
        "label_normal": None,
        "size_mb": 20,
        "signals": [8],
        "notes": "Same raw data as A11 but processed into sequence windows for LSTM.",
    },

    "C2_msnbc_clickstream": {
        "group": "C",
        "name": "MSNBC.com Anonymous Web Data",
        "institution": "UCI ML Repository / Microsoft Research",
        "mode": "direct",
        "urls": [
            "https://archive.ics.uci.edu/static/public/159/msnbc+com+anonymous+web+data.zip",
        ],
        "filenames": ["msnbc_clickstream.zip"],
        "format": "msnbc_sequence",
        "label_column": None,
        "label_normal": None,
        "size_mb": 30,
        "signals": [8],
        "notes": "989,818 user sessions with sequential page category navigation.",
    },

    "C3_wikipedia_clickstream": {
        "group": "C",
        "name": "Wikipedia EN Clickstream (Jan 2024)",
        "institution": "Wikimedia Foundation",
        "mode": "direct",
        "urls": [
            "https://dumps.wikimedia.org/other/clickstream/2024-01/clickstream-enwiki-2024-01.tsv.gz",
        ],
        "filenames": ["wikipedia_clickstream_2024_01.tsv.gz"],
        "format": "tsv",
        "label_column": None,
        "label_normal": None,
        "size_mb": 100,
        "signals": [8],
        "notes": "Real monthly page-to-page navigation chains. Shows human browsing sequences.",
    },

    "C4_caida": {
        "group": "C",
        "name": "CAIDA Anonymized Internet Traces",
        "institution": "CAIDA / UCSD",
        "mode": "manual",
        "manual_url": "https://www.caida.org/catalog/datasets/passive-2020/",
        "manual_instructions": (
            "1. Visit https://www.caida.org/catalog/datasets/passive-2020/\n"
            "2. Register for free research access (academic email preferred)\n"
            "3. Download equinix-chicago.dirA.20200814-125910.UTC.anon.pcap.gz (~50MB)\n"
            "4. Install tshark: brew install --cask wireshark\n"
            "5. Extract timing features:\n"
            "   tshark -r <pcap> -T fields -e frame.time_relative -e ip.src "
            "-e ip.dst -e tcp.dstport -e frame.len > engine/ml/data/raw/C4_caida/flows.tsv\n"
            "6. Place flows.tsv in: engine/ml/data/raw/C4_caida/"
        ),
        "format": "caida_tsv",
        "label_column": None,
        "label_normal": None,
        "size_mb": 50,
        "signals": [2, 8],
        "notes": "Real backbone internet traffic for velocity + inter-request timing.",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Download helpers
# ─────────────────────────────────────────────────────────────────────────────

def download_file(url: str, dest: Path, chunk_size: int = 131072) -> bool:
    """Stream-download a file with progress. Returns True on success."""
    try:
        headers = {"User-Agent": "TokenShield-Researcher/1.0"}
        resp = requests.get(url, stream=True, timeout=120, headers=headers)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r    {dest.name}: {pct:.1f}% ({downloaded//1024//1024}MB)", end="")
        print()
        log.info(f"  ✓ Downloaded {dest.name} ({downloaded//1024//1024}MB)")
        return True
    except Exception as e:
        log.warning(f"  ✗ Download failed [{url}]: {e}")
        return False


def decompress_file(path: Path, dest_dir: Path) -> None:
    """Decompress .gz / .zip / .tar.gz into dest_dir."""
    name = path.name.lower()
    log.info(f"  Decompressing: {path.name} → {dest_dir.name}/")
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(path) as tf:
            tf.extractall(dest_dir)
    elif name.endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            zf.extractall(dest_dir)
    elif name.endswith(".gz"):
        out = dest_dir / path.stem          # strip .gz
        with gzip.open(path, "rb") as f_in, open(out, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        log.info(f"  ✓ Decompressed → {out.name}")
    else:
        log.info(f"  (No decompression needed for {path.name})")


def kaggle_download(dataset_slug: str, dest: Path) -> bool:
    """Download via Kaggle CLI. Requires ~/.kaggle/kaggle.json."""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        log.warning(
            f"\n  ⚠  KAGGLE API KEY NOT FOUND\n"
            f"     To download '{dataset_slug}':\n"
            f"     1. Visit https://www.kaggle.com/account → 'Create API Token'\n"
            f"     2. Save downloaded kaggle.json to ~/.kaggle/kaggle.json\n"
            f"     3. chmod 600 ~/.kaggle/kaggle.json\n"
            f"     4. pip install kaggle\n"
            f"     5. Re-run this script\n"
        )
        return False
    dest.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["kaggle", "datasets", "download", "-d", dataset_slug, "-p", str(dest), "--unzip"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log.warning(f"  ✗ Kaggle failed: {result.stderr.strip()}")
        return False
    log.info(f"  ✓ Kaggle downloaded: {dataset_slug}")
    return True


def zenodo_download(record_id: str, dest: Path) -> bool:
    """Download from Zenodo by record ID via public API."""
    try:
        api_url = f"https://zenodo.org/api/records/{record_id}"
        r = requests.get(api_url, timeout=30)
        r.raise_for_status()
        record = r.json()
        files = record.get("files", [])
        if not files:
            log.warning(f"  ✗ Zenodo record {record_id} has no files")
            return False
        dest.mkdir(parents=True, exist_ok=True)
        for file_info in files:
            fname = file_info["key"]
            furl = file_info["links"]["self"]
            ok = download_file(furl, dest / fname)
            if not ok:
                return False
        return True
    except Exception as e:
        log.warning(f"  ✗ Zenodo download failed: {e}")
        return False


def print_manual_box(ds_id: str, ds: dict) -> None:
    """Print a clear, formatted manual download instruction box."""
    width = 64
    bar = "─" * width
    print(f"\n  ╔{bar}╗")
    print(f"  ║  ⚠  MANUAL DOWNLOAD REQUIRED{' ' * (width - 30)}║")
    print(f"  ╠{bar}╣")
    print(f"  ║  Dataset : {ds['name']:<{width - 12}}║")
    print(f"  ║  Group   : {ds['group']}{' ' * (width - 13)}║")
    print(f"  ╠{bar}╣")
    for line in ds.get("manual_instructions", "").split("\n"):
        print(f"  ║  {line:<{width - 2}}║")
    print(f"  ╠{bar}╣")
    dest = f"engine/ml/data/raw/{ds_id}/"
    print(f"  ║  Place files in: {dest:<{width - 18}}║")
    print(f"  ╚{bar}╝\n")


# ─────────────────────────────────────────────────────────────────────────────
# Per-dataset download orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def download_one(ds_id: str, ds: dict, force: bool = False) -> dict:
    """Download one dataset. Returns a status dict for logging."""
    dest = RAW_DIR / ds_id
    dest.mkdir(parents=True, exist_ok=True)

    result = {
        "dataset_id": ds_id,
        "name": ds["name"],
        "group": ds["group"],
        "mode": ds["mode"],
        "timestamp": datetime.now().isoformat(),
        "dest": str(dest),
        "status": "pending",
        "files": [],
        "error": None,
    }

    log.info(f"\n{'━' * 68}")
    log.info(f"  [{ds['group']}] {ds['name']}")
    log.info(f"  Institution : {ds['institution']}")
    log.info(f"  Mode        : {ds['mode']}")
    log.info(f"  Signals     : {ds['signals']}")
    log.info(f"  Destination : {dest}")

    # Skip if already present (unless --force)
    existing = [f for f in dest.iterdir() if f.is_file()] if dest.exists() else []
    if existing and not force:
        log.info(f"  ✓ Already present ({len(existing)} files). Skipping. Use --force to re-download.")
        result["status"] = "cached"
        result["files"] = [str(f) for f in existing]
        return result

    # ── DIRECT HTTP ──────────────────────────────────────────────────────────
    if ds["mode"] == "direct":
        urls = ds.get("urls", [])
        names = ds.get("filenames", [Path(u).name for u in urls])
        all_ok = True
        for url, fname in zip(urls, names):
            fpath = dest / fname
            ok = download_file(url, fpath)
            if not ok:
                for fb in ds.get("fallback_urls", []):
                    ok = download_file(fb, fpath)
                    if ok:
                        break
            if ok and any(fname.lower().endswith(x) for x in (".gz", ".zip", ".tar.gz", ".tgz")):
                decompress_file(fpath, dest)
            if ok:
                result["files"].append(str(fpath))
            else:
                all_ok = False
        result["status"] = "ok" if all_ok else ("partial" if result["files"] else "failed")

    # ── KAGGLE ───────────────────────────────────────────────────────────────
    elif ds["mode"] == "kaggle":
        ok = kaggle_download(ds["kaggle_dataset"], dest)
        if ok:
            result["files"] = [str(f) for f in dest.rglob("*.csv")]
            result["status"] = "ok"
        else:
            result["status"] = "failed_kaggle"
            # Try fallback mode
            if ds.get("fallback_mode") == "manual":
                print_manual_box(ds_id, ds)
                result["status"] = "manual_required"

    # ── ZENODO ───────────────────────────────────────────────────────────────
    elif ds["mode"] == "zenodo":
        ok = zenodo_download(ds["zenodo_record_id"], dest)
        if ok:
            result["files"] = [str(f) for f in dest.rglob("*") if Path(f).is_file()]
            result["status"] = "ok"
        else:
            result["status"] = "failed_zenodo"

    # ── MANUAL ───────────────────────────────────────────────────────────────
    elif ds["mode"] == "manual":
        print_manual_box(ds_id, ds)
        result["status"] = "manual_required"

    log.info(f"  Status: {result['status']}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run(groups: list = None, single: str = None, force: bool = False) -> None:
    """Download datasets. groups=None means all groups."""
    header = "═" * 70
    print(f"\n{header}")
    print("  TokenShield — Dataset Downloader  v1.0")
    print(f"  Total: 23 real public datasets | ~2.4 GB | ~5.7M training rows")
    print(f"{header}\n")

    targets = {}
    if single:
        if single not in DATASETS:
            log.error(f"Unknown dataset id: '{single}'. Use --list to see all.")
            sys.exit(1)
        targets = {single: DATASETS[single]}
    else:
        for ds_id, ds in DATASETS.items():
            if groups is None or ds["group"] in groups:
                targets[ds_id] = ds

    log.info(f"Downloading {len(targets)} dataset(s)...")
    all_results = []
    for ds_id, ds in targets.items():
        result = download_one(ds_id, ds, force=force)
        all_results.append(result)

    # ── Save log ──────────────────────────────────────────────────────────────
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump({"generated_at": datetime.now().isoformat(), "runs": all_results}, f, indent=2)

    # ── Summary ───────────────────────────────────────────────────────────────
    ok      = [r for r in all_results if r["status"] in ("ok", "cached")]
    manual  = [r for r in all_results if r["status"] == "manual_required"]
    failed  = [r for r in all_results if r["status"] not in ("ok", "cached", "manual_required")]

    print(f"\n{'═' * 70}")
    print("  DOWNLOAD SUMMARY")
    print(f"{'═' * 70}")
    print(f"  ✅ Automated  : {len(ok)}")
    print(f"  ⚠  Manual    : {len(manual)}")
    print(f"  ❌ Failed     : {len(failed)}")
    print(f"  📄 Log        : {LOG_FILE}")

    if manual:
        print("\n  ── MANUAL DOWNLOADS STILL NEEDED ─────────────────────────────")
        for r in manual:
            ds = DATASETS[r["dataset_id"]]
            print(f"    [{r['group']}] {r['name']}")
            print(f"        URL: {ds.get('manual_url', 'see instructions above')}")

    if failed:
        print("\n  ── FAILED (retry with --force) ────────────────────────────────")
        for r in failed:
            print(f"    [{r['group']}] {r['name']}  status={r['status']}")

    print(f"\n  Raw data saved to: {RAW_DIR}")
    print("  ▶  Next step: python engine/ml/train/feature_mapper.py")
    print(f"{'═' * 70}\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TokenShield Dataset Downloader — downloads all 23 real public datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--groups", nargs="+", choices=["A", "B", "C"],
                        help="Download only specific groups (default: all)")
    parser.add_argument("--dataset", metavar="ID",
                        help="Download a single dataset by ID (e.g. A1_nsl_kdd)")
    parser.add_argument("--force", action="store_true",
                        help="Re-download even if files already exist")
    parser.add_argument("--list", action="store_true",
                        help="List all datasets and exit")
    args = parser.parse_args()

    if args.list:
        print(f"\n{'ID':<28} {'Grp':<4} {'Mode':<10} {'MB':>6}  Name")
        print("─" * 80)
        for ds_id, ds in DATASETS.items():
            print(f"{ds_id:<28} {ds['group']:<4} {ds['mode']:<10} {ds['size_mb']:>6}  {ds['name']}")
        print(f"\nTotal: {len(DATASETS)} datasets")
        sys.exit(0)

    run(groups=args.groups, single=args.dataset, force=args.force)
