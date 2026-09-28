#!/usr/bin/env python3
import argparse
import importlib
import os
from pathlib import Path
import subprocess
import sys


REQUIRED_MODULES = (
    "accelerate",
    "datasets",
    "decord",
    "deepspeed",
    "evaluate",
    "hf_transfer",
    "huggingface_hub",
    "numpy",
    "pandas",
    "pytablewriter",
    "safetensors",
    "tenacity",
    "transformers",
)


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geosr-repo", type=Path, required=True)
    args = parser.parse_args()

    if sys.version_info[:2] != (3, 11):
        fail(f"expected Python 3.11, got {sys.version.split()[0]}")

    cuda_home = Path(os.environ.get("CUDA_HOME", sys.prefix))
    nvcc = cuda_home / "bin" / "nvcc"
    if not nvcc.is_file():
        fail(f"nvcc not found at {nvcc}; export CUDA_HOME={sys.prefix}")
    nvcc_text = subprocess.check_output([str(nvcc), "--version"], text=True)
    if "release 12.8" not in nvcc_text:
        fail("expected CUDA toolkit 12.8")

    for module in REQUIRED_MODULES:
        importlib.import_module(module)

    import torch

    if torch.__version__ != "2.7.1+cu128":
        fail(f"expected torch 2.7.1+cu128, got {torch.__version__}")
    if torch.version.cuda != "12.8":
        fail(f"expected torch CUDA 12.8, got {torch.version.cuda}")
    if not torch.cuda.is_available():
        fail("torch.cuda.is_available() is false")

    for index in range(torch.cuda.device_count()):
        capability = torch.cuda.get_device_capability(index)
        print(f"[OK] GPU {index}: {torch.cuda.get_device_name(index)}, capability={capability}")
        if capability < (12, 0):
            fail(f"GPU {index} is not an RTX 50-series class device")

    import flash_attn
    from flash_attn import flash_attn_func

    if flash_attn.__version__ != "2.8.3":
        fail(f"expected flash-attn 2.8.3, got {flash_attn.__version__}")
    q = torch.randn(1, 128, 8, 64, device="cuda", dtype=torch.bfloat16)
    output = flash_attn_func(q, q, q)
    torch.cuda.synchronize()
    if not torch.isfinite(output).all():
        fail("FlashAttention produced non-finite values")
    print(f"[OK] FlashAttention GPU forward: shape={tuple(output.shape)}")

    repo = args.geosr_repo.resolve()
    if not (repo / "src" / "lmms_eval").is_dir():
        fail(f"GeoSR lmms_eval source not found under {repo}")
    sys.path.insert(0, str(repo / "src"))
    importlib.import_module("lmms_eval")
    print(f"[OK] GeoSR lmms_eval import from {repo}")
    print("[OK] all environment checks passed")


if __name__ == "__main__":
    main()
