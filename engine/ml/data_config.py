# TokenShield — Dataset Storage Configuration
# ─────────────────────────────────────────────
# Set RAW_DATA_DIR to wherever your datasets live.
# The SSD path is used by default so no data is stored on your Mac.
#
# Usage: Both download_datasets.py and feature_mapper.py read this file automatically.
# To change, just edit RAW_DATA_DIR below and re-run the scripts.

RAW_DATA_DIR = "/Volumes/yash ssd/engine/ml/data/raw"

# Output parquet files (train/val/test) — also on SSD to save Mac space
OUTPUT_DATA_DIR = "/Volumes/yash ssd/engine/ml/data/processed"

# Models directory — keep on Mac (small files, needed at runtime)
MODELS_DIR = "engine/ml/models"
