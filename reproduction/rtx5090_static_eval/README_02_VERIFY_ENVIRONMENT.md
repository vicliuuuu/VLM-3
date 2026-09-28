# 02. 环境验证流程

环境验证分成四层。任意一层失败，都不要直接启动全量评测。

## 1. 驱动、CUDA 与 Python 包

```bash
conda activate geosr
nvidia-smi
echo "$CUDA_HOME"
nvcc --version

python scripts/verify_environment.py \
  --geosr-repo "$HOME/work/GeoSR-official"
```

脚本检查：

- Python 为 3.11。
- PyTorch 为 CUDA 构建，且能看到 GPU。
- GPU compute capability 至少为 12.0。
- `torch.version.cuda` 为 12.8。
- `CUDA_HOME/bin/nvcc` 存在。
- 关键 Python 包可导入。
- FlashAttention 在 GPU 上执行真实 BF16 forward，而不只是成功 import。
- GeoSR 本地 `lmms_eval` 模块可导入。

成功时末尾应看到：

```text
[OK] all environment checks passed
```

## 2. 视频解码

数据下载后再验证 Decord：

```bash
python - <<'PY'
import decord

path = "/path/to/geosr_static/VSI-Bench/arkitscenes/41069025.mp4"
video = decord.VideoReader(path)
print("frames:", len(video))
print("first frame shape:", video[0].shape)
PY
```

已验证样例应得到 5045 帧，第一帧形状为 `(480, 640, 3)`。

`pip check` 可能报告 `decord 0.6.0 is not supported on this platform`。这来自包元数据；以上实际解码成功才是本流程采用的功能性判据。

## 3. GeoSR 评测入口

```bash
export GEOSR_REPO="$HOME/work/GeoSR-official"
export CUDA_HOME="$CONDA_PREFIX"
export PYTHONPATH="$GEOSR_REPO/src${PYTHONPATH:+:$PYTHONPATH}"

python -m lmms_eval --help
```

必须正常显示 `--model`、`--tasks`、`--limit` 和 `--output_path` 等参数。

## 4. 单样本端到端验证

```bash
LIMIT=1 GPU_ID=0 bash scripts/run_vsibench.sh \
  "$HOME/work/GeoSR-official" /path/to/geosr_static
```

通过标准：

1. 四个 checkpoint shard 全部加载。
2. 日志显示 `FlashAttention 3 is available` 或模型明确使用 FlashAttention。
3. `Model Responding` 完成 `1/1`。
4. 命令退出码为 0。
5. 输出目录同时生成 `*_results.json` 和 `*_samples_vsibench.jsonl`。

`--limit` 结果不能作为正式指标，只用于验证链路。

## 常见错误

### `CUDA_HOME does not exist`

```bash
export CUDA_HOME="$CONDA_PREFIX"
test -x "$CUDA_HOME/bin/nvcc"
```

### `No module named lmms_eval`

```bash
export PYTHONPATH="$GEOSR_REPO/src${PYTHONPATH:+:$PYTHONPATH}"
```

### 关闭 FlashAttention 后 OOM

确认模型参数包含：

```text
use_flash_attention_2=true
```

### `No module named tenacity`、`hf_transfer` 或 `pytablewriter`

这些包已列入本目录的 RTX 5090 requirements：

```bash
python -m pip install -r requirements-rtx5090.txt
```
