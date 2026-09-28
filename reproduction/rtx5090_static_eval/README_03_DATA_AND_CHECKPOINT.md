# 03. VSI-Bench 与 GeoSR3D checkpoint

## 1. 存储建议

VSI-Bench 压缩包约 5.34 GB，GeoSR3D checkpoint 约 17.3 GiB。建议将数据和模型放在大容量 NVMe 分区，不要放在空间紧张的 `/home` 分区。

```bash
export DATA_ROOT=/path/to/geosr_static
export GEOSR_REPO="$HOME/work/GeoSR-official"
```

## 2. 自动下载和解压

```bash
conda activate geosr
bash scripts/download_assets.sh "$DATA_ROOT" "$GEOSR_REPO"
```

脚本下载：

- `nyu-visionx/VSI-Bench` 中的 `test.jsonl`、`arkitscenes.zip`、`scannet.zip`、`scannetpp.zip`。
- `SuhZhang/GeoSR-Model` 中的 `GeoSR3D-Model/*`。

随后执行 ZIP CRC 检查、解压、创建官方 evaluator 所需的 `DATA/` 链接，并在 GeoSR 仓库下建立数据和模型软链接。

网络不稳定时可指定镜像：

```bash
HF_ENDPOINT=https://hf-mirror.com \
bash scripts/download_assets.sh "$DATA_ROOT" "$GEOSR_REPO"
```

Hugging Face CLI 支持断点续传。不要在另一个终端同时下载同一个目标文件，否则会争用 `.lock`。

## 3. 手动等价命令

```bash
mkdir -p "$DATA_ROOT/VSI-Bench" "$DATA_ROOT/models"

hf download nyu-visionx/VSI-Bench \
  --repo-type dataset \
  --include test.jsonl arkitscenes.zip scannet.zip scannetpp.zip \
  --local-dir "$DATA_ROOT/VSI-Bench"

hf download SuhZhang/GeoSR-Model \
  --include "GeoSR3D-Model/*" \
  --local-dir "$DATA_ROOT/models"

unzip -tq "$DATA_ROOT/VSI-Bench/arkitscenes.zip"
unzip -tq "$DATA_ROOT/VSI-Bench/scannet.zip"
unzip -tq "$DATA_ROOT/VSI-Bench/scannetpp.zip"

unzip -q -o "$DATA_ROOT/VSI-Bench/arkitscenes.zip" -d "$DATA_ROOT/VSI-Bench"
unzip -q -o "$DATA_ROOT/VSI-Bench/scannet.zip" -d "$DATA_ROOT/VSI-Bench"
unzip -q -o "$DATA_ROOT/VSI-Bench/scannetpp.zip" -d "$DATA_ROOT/VSI-Bench"
```

官方 task config 将视频路径解析为：

```text
$HF_HOME/data/VSI-Bench_HF/DATA/<dataset>/<scene_name>.mp4
```

因此脚本创建以下布局：

```text
$DATA_ROOT/VSI-Bench/DATA/arkitscenes -> ../arkitscenes
$DATA_ROOT/VSI-Bench/DATA/scannet     -> ../scannet
$DATA_ROOT/VSI-Bench/DATA/scannetpp   -> ../scannetpp
$GEOSR_REPO/data/VSI-Bench_HF         -> $DATA_ROOT/VSI-Bench
$GEOSR_REPO/data/models/GeoSR3D-Model -> $DATA_ROOT/models/GeoSR3D-Model
```

评测时设置：

```bash
export HF_HOME="$GEOSR_REPO"
```

## 4. 完整性验证

```bash
python scripts/verify_assets.py --data-root "$DATA_ROOT"
```

验证内容：

- 三个 ZIP 能通过 CRC 检查。
- `test.jsonl` 可逐行解析。
- 问题数为 5130，唯一场景数为 288。
- 每条问题引用的视频都存在且非空。
- checkpoint index 只引用四个预期 shard。
- 四个 shard 的精确字节数正确。
- 每个 safetensors shard 的 header 可读。

已验证 shard 大小：

```text
model-00001-of-00004.safetensors  4934281216
model-00002-of-00004.safetensors  4932750944
model-00003-of-00004.safetensors  4991495888
model-00004-of-00004.safetensors  3692182944
```

成功时末尾应看到：

```text
[OK] all asset checks passed
```

## 5. 临时文件和锁

只有在确认没有 `hf`、`huggingface-cli`、`aria2c` 或 `unzip` 进程访问该目录后，才能删除遗留锁：

```bash
find "$DATA_ROOT" -type f \( -name '*.lock' -o -name '*.aria2' \) -print
```

不要把 `.lock` 的存在直接当成错误；活跃下载期间它是正常的。
