#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${1:?Usage: download_assets.sh DATA_ROOT GEOSR_REPO}"
GEOSR_REPO="${2:?Usage: download_assets.sh DATA_ROOT GEOSR_REPO}"

mkdir -p "$DATA_ROOT/VSI-Bench" "$DATA_ROOT/models"

if command -v hf >/dev/null 2>&1; then
  HF=(hf download)
elif command -v huggingface-cli >/dev/null 2>&1; then
  HF=(huggingface-cli download)
else
  echo "Error: Hugging Face CLI not found." >&2
  exit 1
fi

echo "[1/5] Downloading VSI-Bench"
"${HF[@]}" nyu-visionx/VSI-Bench --repo-type dataset \
  --include test.jsonl arkitscenes.zip scannet.zip scannetpp.zip \
  --local-dir "$DATA_ROOT/VSI-Bench"

echo "[2/5] Verifying ZIP CRC"
for archive in arkitscenes.zip scannet.zip scannetpp.zip; do
  unzip -tq "$DATA_ROOT/VSI-Bench/$archive"
done

echo "[3/5] Extracting VSI-Bench"
for archive in arkitscenes.zip scannet.zip scannetpp.zip; do
  unzip -q -o "$DATA_ROOT/VSI-Bench/$archive" -d "$DATA_ROOT/VSI-Bench"
done

echo "[4/5] Downloading official GeoSR3D checkpoint"
"${HF[@]}" SuhZhang/GeoSR-Model \
  --include "GeoSR3D-Model/*" \
  --local-dir "$DATA_ROOT/models"

echo "[5/5] Creating evaluator links"
mkdir -p "$DATA_ROOT/VSI-Bench/DATA" "$GEOSR_REPO/data/models"
ln -sfn ../arkitscenes "$DATA_ROOT/VSI-Bench/DATA/arkitscenes"
ln -sfn ../scannet "$DATA_ROOT/VSI-Bench/DATA/scannet"
ln -sfn ../scannetpp "$DATA_ROOT/VSI-Bench/DATA/scannetpp"
ln -sfn "$DATA_ROOT/VSI-Bench" "$GEOSR_REPO/data/VSI-Bench_HF"
ln -sfn "$DATA_ROOT/models/GeoSR3D-Model" "$GEOSR_REPO/data/models/GeoSR3D-Model"

echo "Assets are ready under: $DATA_ROOT"
