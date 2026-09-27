#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/download_geosr_static_data.sh /path/to/geosr_data
#
# Downloads public annotations, VSI-Bench, and model weights. It deliberately
# does not claim to download SPAR RGB media: SPAR's official per-source
# archives contain annotations, while the underlying images remain subject to
# the licenses of ScanNet, ScanNet++, Structured3D, and related datasets.

DATA_ROOT="${1:-$PWD/data}"
DOWNLOAD_MODELS="${DOWNLOAD_MODELS:-1}"
HF_HOME_DIR="${HF_HOME:-$DATA_ROOT/hf_cache}"

mkdir -p "$DATA_ROOT" "$HF_HOME_DIR"
export HF_HOME="$HF_HOME_DIR"

if command -v hf >/dev/null 2>&1; then
  HF_CMD=(hf download)
elif command -v huggingface-cli >/dev/null 2>&1; then
  HF_CMD=(huggingface-cli download)
else
  echo "Missing Hugging Face CLI."
  echo 'Install it once with: python -m pip install -U "huggingface_hub[cli]"'
  exit 1
fi

echo "[1/3] Downloading VSI-Bench evaluation files"
mkdir -p "$DATA_ROOT/VSI-Bench"
"${HF_CMD[@]}" nyu-visionx/VSI-Bench --repo-type dataset \
  test.jsonl scannet.zip scannetpp.zip arkitscenes.zip \
  --local-dir "$DATA_ROOT/VSI-Bench"

echo "[2/3] Downloading released static training annotations"
mkdir -p "$DATA_ROOT/GeoSR-static"
"${HF_CMD[@]}" zd11024/VG-LLM-Data --repo-type dataset \
  train/spar_234k.json train/llava_hound_64k.json train/spar_7m.tar.gz \
  --local-dir "$DATA_ROOT/GeoSR-static"

if [[ "$DOWNLOAD_MODELS" == "1" ]]; then
  echo "[3/3] Downloading model snapshots"
  mkdir -p "$DATA_ROOT/models/Qwen2.5-VL-7B-Instruct"
  mkdir -p "$DATA_ROOT/models/VGGT-1B"
  "${HF_CMD[@]}" Qwen/Qwen2.5-VL-7B-Instruct \
    --local-dir "$DATA_ROOT/models/Qwen2.5-VL-7B-Instruct"
  "${HF_CMD[@]}" facebook/VGGT-1B \
    --local-dir "$DATA_ROOT/models/VGGT-1B"
else
  echo "[3/3] Skipping model snapshots (DOWNLOAD_MODELS=$DOWNLOAD_MODELS)"
fi

cat <<EOF

Download complete.
Data root: $DATA_ROOT
HF cache:  $HF_HOME

Important:
  - No command above guarantees SPAR RGB media.
  - Inspect GeoSR-static/train/spar_7m.tar.gz before treating it as media.
  - Obtain any missing upstream RGB data under the corresponding dataset terms.
  - Run check_media_availability.py before sampling a training subset.
EOF
