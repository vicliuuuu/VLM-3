#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/download_geosr_static_data.sh /path/to/geosr_data
#
# This script downloads public assets needed for the first static GeoSR-style
# experiment, including SPAR-7M compact media packages. It does not download
# full upstream raw datasets such as full LLaVA-Video-178K.

DATA_ROOT="${1:-$PWD/data}"
HF_HOME_DIR="${HF_HOME:-$DATA_ROOT/hf_cache}"

mkdir -p "$DATA_ROOT" "$HF_HOME_DIR"
export DATA_ROOT
export HF_HOME="$HF_HOME_DIR"

echo "[1/5] Installing / checking Hugging Face CLI"
python -m pip install -U "huggingface_hub[cli]"

echo "[2/5] Downloading VSI-Bench evaluation files"
mkdir -p "$DATA_ROOT/VSI-Bench"
huggingface-cli download nyu-visionx/VSI-Bench --repo-type dataset \
  test.jsonl scannet.zip scannetpp.zip arkitscenes.zip \
  --local-dir "$DATA_ROOT/VSI-Bench"

echo "[3/5] Downloading GeoSR/VG-LLM static training annotations"
mkdir -p "$DATA_ROOT/GeoSR-static"
huggingface-cli download zd11024/VG-LLM-Data --repo-type dataset \
  train/spar_234k.json train/llava_hound_64k.json train/spar_7m.tar.gz \
  --local-dir "$DATA_ROOT/GeoSR-static"

echo "[4/5] Downloading SPAR-7M compact media packages"
mkdir -p "$DATA_ROOT/SPAR-7M"
huggingface-cli download jasonzhango/SPAR-7M --repo-type dataset \
  rxr.tar.gz scannet.tar.gz scannetpp.tar.gz structured3d.tar.gz \
  --local-dir "$DATA_ROOT/SPAR-7M"

echo "[5/5] Downloading model snapshots"
mkdir -p "$DATA_ROOT/models"
python - <<'PY'
import os
from huggingface_hub import snapshot_download

data_root = os.environ.get("DATA_ROOT")
if data_root is None:
    data_root = os.path.join(os.getcwd(), "data")

models_dir = os.path.join(data_root, "models")
os.makedirs(models_dir, exist_ok=True)

snapshot_download(
    repo_id="Qwen/Qwen2.5-VL-7B-Instruct",
    local_dir=os.path.join(models_dir, "Qwen2.5-VL-7B-Instruct"),
)
snapshot_download(
    repo_id="facebook/VGGT-1B",
    local_dir=os.path.join(models_dir, "VGGT-1B"),
)
PY

echo "Done."
echo "Data root: $DATA_ROOT"
echo "HF cache:  $HF_HOME"
echo
echo "Next steps:"
echo "  1. Unzip VSI-Bench archives if your evaluator expects folders."
echo "  2. Extract SPAR compact media packages into a media root."
echo "  3. Use scripts/sample_spar_subset.py to create a small SPAR training subset."
echo "  4. Use scripts/check_media_availability.py to verify media coverage."
