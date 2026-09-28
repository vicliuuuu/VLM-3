#!/usr/bin/env bash
set -euo pipefail

GEOSR_REPO="${1:?Usage: run_vsibench.sh GEOSR_REPO DATA_ROOT}"
DATA_ROOT="${2:?Usage: run_vsibench.sh GEOSR_REPO DATA_ROOT}"
GPU_ID="${GPU_ID:-0}"
LIMIT="${LIMIT:-}"
OUTPUT_NAME="${OUTPUT_NAME:-official_geosr3d_vsibench_full}"
MODEL_PATH="$DATA_ROOT/models/GeoSR3D-Model"
OUTPUT_PATH="$DATA_ROOT/eval/$OUTPUT_NAME"

if [[ ! -f "$MODEL_PATH/config.json" ]]; then
  echo "Error: checkpoint not found at $MODEL_PATH" >&2
  exit 1
fi
if [[ ! -f "$DATA_ROOT/VSI-Bench/test.jsonl" ]]; then
  echo "Error: VSI-Bench not found at $DATA_ROOT/VSI-Bench" >&2
  exit 1
fi

mkdir -p "$DATA_ROOT/VSI-Bench/DATA" "$GEOSR_REPO/data/models" "$OUTPUT_PATH"
ln -sfn ../arkitscenes "$DATA_ROOT/VSI-Bench/DATA/arkitscenes"
ln -sfn ../scannet "$DATA_ROOT/VSI-Bench/DATA/scannet"
ln -sfn ../scannetpp "$DATA_ROOT/VSI-Bench/DATA/scannetpp"
ln -sfn "$DATA_ROOT/VSI-Bench" "$GEOSR_REPO/data/VSI-Bench_HF"
ln -sfn "$MODEL_PATH" "$GEOSR_REPO/data/models/GeoSR3D-Model"

export CUDA_VISIBLE_DEVICES="$GPU_ID"
export HF_HOME="$GEOSR_REPO"
export CUDA_HOME="${CUDA_HOME:-$CONDA_PREFIX}"
export PYTHONPATH="$GEOSR_REPO/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"

ARGS=(
  --model geosr3d
  --model_args "pretrained=$MODEL_PATH,use_flash_attention_2=true,max_num_frames=32,max_length=12800"
  --tasks vsibench
  --batch_size 1
  --log_samples
  --output_path "$OUTPUT_PATH"
  --verbosity INFO
)
if [[ -n "$LIMIT" ]]; then
  ARGS+=(--limit "$LIMIT")
fi

cd "$GEOSR_REPO"
python -m lmms_eval "${ARGS[@]}"
