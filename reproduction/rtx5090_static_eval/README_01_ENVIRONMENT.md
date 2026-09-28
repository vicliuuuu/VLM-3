# 01. RTX 5090 环境创建

## 1. 硬件与软件基线

本次成功运行的环境：

```text
GPU: NVIDIA GeForce RTX 5090, 32607 MiB, compute capability 12.0
Driver: 595.71.05
Python: 3.11.15
CUDA toolkit / nvcc: 12.8.93
PyTorch: 2.7.1+cu128
torchvision: 0.22.1+cu128
torchaudio: 2.7.1+cu128
FlashAttention: 2.8.3
transformers: 4.51.0
```

GeoSR 官方 `requirement.txt` 固定了 PyTorch 2.6.0+cu124 和 FlashAttention 2.7.4.post1。它们不作为本记录中的 RTX 5090 GPU 栈使用。其余官方依赖仍从该文件安装。

## 2. 自动创建环境

脚本会执行以下操作：

1. 创建 Python 3.11 的 `geosr` Conda 环境。
2. 安装 CUDA toolkit 12.8，使环境内存在 `nvcc`。
3. clone GeoSR，并 checkout 已验证 commit。
4. 安装 PyTorch cu128。
5. 过滤官方依赖文件中的 cu124 GPU 栈，再安装其余依赖。
6. 安装 [requirements-rtx5090.txt](requirements-rtx5090.txt) 中的 RTX 5090 覆盖项和官方遗漏项。

```bash
cd reproduction/rtx5090_static_eval
bash scripts/create_environment.sh "$HOME/work/GeoSR-official"
conda activate geosr
```

可以通过环境变量覆盖默认值：

```bash
ENV_NAME=geosr \
PYTHON_VERSION=3.11 \
CUDA_VERSION=12.8 \
GEOSR_COMMIT=d2455359fcf62555eb04686e397aa1ab9393df9f \
bash scripts/create_environment.sh "$HOME/work/GeoSR-official"
```

脚本默认拒绝覆盖已经存在的 Conda 环境或非空源码目录。需要复用已有环境时，不要重跑创建脚本，直接运行环境验证。

## 3. 手动等价命令

```bash
conda create -n geosr python=3.11 -y
conda activate geosr
conda install -y -c nvidia cuda-toolkit=12.8

git clone https://github.com/SuhZhang/GeoSR.git "$HOME/work/GeoSR-official"
git -C "$HOME/work/GeoSR-official" checkout d2455359fcf62555eb04686e397aa1ab9393df9f

python -m pip install --upgrade pip setuptools wheel ninja
python -m pip install \
  torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 \
  --index-url https://download.pytorch.org/whl/cu128
```

从官方依赖中排除与 RTX 5090 栈冲突的条目：

```bash
awk '
  /^--extra-index-url / {next}
  /^(torch|torchvision|torchaudio|flash_attn|triton|sympy)==/ {next}
  /^nvidia-/ {next}
  {print}
' "$HOME/work/GeoSR-official/requirement.txt" \
  > /tmp/geosr-requirements-no-gpu.txt

python -m pip install -r /tmp/geosr-requirements-no-gpu.txt
python -m pip install -r requirements-rtx5090.txt
```

把 `CUDA_HOME` 固定到当前 Conda 环境：

```bash
conda env config vars set -n geosr CUDA_HOME="$CONDA_PREFIX"
conda deactivate
conda activate geosr
```

## 4. 为什么必须使用 FlashAttention

32 帧 VSI-Bench 样本在关闭 FlashAttention 时会进入 PyTorch SDPA。实测视觉注意力曾尝试额外申请约 62 GiB 显存，单张 32 GB RTX 5090 会 OOM。

启用 `use_flash_attention_2=true` 后，同一样本约 3.75 秒完成。因此评测命令必须保留该参数。

## 5. 可复现性边界

- 本目录固定的是已验证的推理环境，不宣称所有未来驱动和包版本都产生逐 bit 相同结果。
- 官方报告 51.9，本次得到 51.6952，绝对差值约 0.20。
- 不要在环境创建后无条件执行 `pip install -U`；升级 PyTorch、Transformers 或 FlashAttention 后应重新运行全部验证。
