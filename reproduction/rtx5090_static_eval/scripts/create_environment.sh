#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

GEOSR_REPO="${1:-$HOME/work/GeoSR-official}"
ENV_NAME="${ENV_NAME:-geosr}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
CUDA_VERSION="${CUDA_VERSION:-12.8}"
GEOSR_COMMIT="${GEOSR_COMMIT:-d2455359fcf62555eb04686e397aa1ab9393df9f}"

if ! command -v conda >/dev/null 2>&1; then
  echo "Error: conda is not available in PATH." >&2
  exit 1
fi

if conda env list | awk '{print $1}' | grep -Fxq "$ENV_NAME"; then
  echo "Error: conda environment already exists: $ENV_NAME" >&2
  echo "Run the verification script to reuse it, or choose another ENV_NAME." >&2
  exit 1
fi

if [[ -e "$GEOSR_REPO" ]]; then
  echo "Error: target repository path already exists: $GEOSR_REPO" >&2
  exit 1
fi

conda create -n "$ENV_NAME" "python=$PYTHON_VERSION" -y
conda install -n "$ENV_NAME" -c nvidia "cuda-toolkit=$CUDA_VERSION" -y

mkdir -p "$(dirname -- "$GEOSR_REPO")"
git clone https://github.com/SuhZhang/GeoSR.git "$GEOSR_REPO"
git -C "$GEOSR_REPO" checkout "$GEOSR_COMMIT"

PYTHON_BIN="$(conda run -n "$ENV_NAME" python -c 'import sys; print(sys.executable)')"
"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel ninja
"$PYTHON_BIN" -m pip install \
  torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 \
  --index-url https://download.pytorch.org/whl/cu128

FILTERED_REQUIREMENTS="$(mktemp)"
trap 'rm -f "$FILTERED_REQUIREMENTS"' EXIT
awk '
  /^--extra-index-url / {next}
  /^(torch|torchvision|torchaudio|flash_attn|triton|sympy)==/ {next}
  /^nvidia-/ {next}
  {print}
' "$GEOSR_REPO/requirement.txt" > "$FILTERED_REQUIREMENTS"

"$PYTHON_BIN" -m pip install -r "$FILTERED_REQUIREMENTS"
"$PYTHON_BIN" -m pip install -r "$ROOT_DIR/requirements-rtx5090.txt"

ENV_PREFIX="$(conda run -n "$ENV_NAME" python -c 'import sys; print(sys.prefix)')"
conda env config vars set -n "$ENV_NAME" CUDA_HOME="$ENV_PREFIX"

cat <<EOF

Environment created successfully.
  Conda env:  $ENV_NAME
  GeoSR repo: $GEOSR_REPO
  Commit:     $GEOSR_COMMIT

Next:
  conda activate $ENV_NAME
  python "$ROOT_DIR/scripts/verify_environment.py" --geosr-repo "$GEOSR_REPO"
EOF
