# GeoSR 静态实验数据准备计划

目标：在约 1 TB 服务器存储空间内，先完成 GeoSR 静态方向的最小可行复现实验，再做你的 geometry token layer ablation。

核心原则：

- 评测集固定使用 `VSI-Bench`。
- 所有被比较的方法使用同一份训练子集、同一训练预算。
- 如果训练数据和论文不同，不直接比较论文表格中的绝对分数，而比较你自己复现的 baseline 与你的方法之间的相对提升。

## 一句话流程

```text
下载公开 annotation / 评测集 / 模型 / SPAR compact media
-> 解压 SPAR compact media
-> 从 spar_234k.json 抽样得到 spar_50k.json 和 spar_50k_media.txt
-> 检查 media 覆盖率
-> 把可用 media 软链接到 GeoSR 训练目录
-> 跑 GeoSR-style baseline
-> 改 geometry layer 做 ablation
```

## 需要准备的数据

| 优先级 | 数据 / 文件 | 用途 | 下载地址 | 已知下载大小 | 说明 |
|---|---|---|---|---:|---|
| 必须 | `VSI-Bench`: `test.jsonl`, `scannet.zip`, `scannetpp.zip`, `arkitscenes.zip` | 静态空间推理评测集 | https://huggingface.co/datasets/nyu-visionx/VSI-Bench | 约 5.73 GB | 固定评测集，建议完整下载。 |
| 必须 | `VG-LLM-Data/train/spar_234k.json` | SPAR 训练 annotation | https://huggingface.co/datasets/zd11024/VG-LLM-Data/tree/main/train | 约 320 MB | 第一轮从这里抽 50k 或 100k。 |
| 建议 | `VG-LLM-Data/train/llava_hound_64k.json` | 作者 recipe 中的 2D/video instruction 辅助数据 | 同上 | 约 28.6 MB | 第一轮可先不使用，因为会增加视频 media 准备成本。 |
| 建议 | SPAR-7M compact media: `rxr.tar.gz`, `scannet.tar.gz`, `scannetpp.tar.gz`, `structured3d.tar.gz` | `spar_234k` 可能引用的 compact media | https://huggingface.co/datasets/jasonzhango/SPAR-7M/tree/main | 合计约 3 GB | 先下载这些包并检查覆盖率。它们不是完整原始上游数据集，而是 SPAR 处理后的 compact media。 |
| 必须 | Qwen2.5-VL-7B + VGGT-1B | 训练和 VGGT feature 提取 | https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct / https://huggingface.co/facebook/VGGT-1B | 约 20-30 GB | 建议放在数据盘的 HF cache 中。 |
| 可选 | LLaVA-Video-178K media | `llava_hound_64k` 对应视频/帧 | https://huggingface.co/datasets/lmms-lab/LLaVA-Video-178K | 完整约 1.28 TB | 1 TB 预算下不要完整下载。若后续使用，只下载引用子集。 |
| 可选 | 预提取 VGGT features | 降低在线训练显存和时间 | 本地生成 | 取决于样本数和层数 | 第一轮先跑通在线版或只预提 1 层，再扩展到 3 层。 |

## 重要判断：能否部分下载

| 问题 | 准确答案 |
|---|---|
| Hugging Face 能不能只下载一部分？ | 可以，但只能按仓库中的独立文件路径下载。 |
| 能不能只下载 `.zip` / `.tar.gz` 内部一部分样本？ | 通常不可以。必须下载整个压缩包，再解压、筛选、删除。 |
| `spar_234k.json` 下载后是否就有训练图片？ | 没有。它是 annotation，需要准备其中引用的 media。 |
| 是否一定要下载原始 ScanNet / ScanNet++ / Structured3D / RxR？ | 不一定。先下载 SPAR-7M Hugging Face 上的 compact media 包，检查是否覆盖你的子集；覆盖不足时再考虑原始上游数据。 |

## 服务器端完整步骤

下面假设服务器数据根目录为：

```bash
/data/geosr_static
```

你的代码目录为：

```bash
/path/to/CVPR
```

### 1. 下载公开数据和模型

```bash
cd /path/to/CVPR
bash scripts/download_geosr_static_data.sh /data/geosr_static
```

这个脚本会下载：

```text
/data/geosr_static/VSI-Bench
/data/geosr_static/GeoSR-static
/data/geosr_static/SPAR-7M
/data/geosr_static/models
/data/geosr_static/hf_cache
```

### 2. 解压 SPAR compact media

```bash
cd /path/to/CVPR
bash scripts/extract_spar_compact_media.sh /data/geosr_static
```

解压目标：

```text
/data/geosr_static/media
```

期望里面出现类似：

```text
/data/geosr_static/media/spar/scannet/...
/data/geosr_static/media/spar/scannetpp/...
/data/geosr_static/media/spar/structured3d/...
/data/geosr_static/media/spar/rxr/...
```

如果解压后目录层级不同，先不要移动，下一步用检查脚本看覆盖率。

### 3. 从 `spar_234k.json` 抽样

第一轮建议先抽 50k：

```bash
cd /path/to/CVPR
python scripts/sample_spar_subset.py \
  --input /data/geosr_static/GeoSR-static/train/spar_234k.json \
  --output /data/geosr_static/GeoSR-static/train/spar_50k.json \
  --media-list /data/geosr_static/GeoSR-static/train/spar_50k_media.txt \
  --num-samples 50000 \
  --seed 0
```

输出：

```text
/data/geosr_static/GeoSR-static/train/spar_50k.json
/data/geosr_static/GeoSR-static/train/spar_50k_media.txt
```

`spar_50k_media.txt` 就是这 50k 样本引用的 media 清单。

### 4. 检查 SPAR compact media 是否覆盖你的子集

```bash
cd /path/to/CVPR
python scripts/check_media_availability.py \
  --media-list /data/geosr_static/GeoSR-static/train/spar_50k_media.txt \
  --media-root /data/geosr_static/media \
  --missing-output /data/geosr_static/GeoSR-static/train/spar_50k_missing_media.txt
```

你需要看输出中的：

```text
Coverage: xx.xx%
```

判断：

- 如果接近 `100%`，说明 SPAR compact media 足够覆盖当前子集。
- 如果覆盖率很低，先检查目录层级是否多了一层或少了一层。
- 如果目录层级正确但仍大量缺失，说明当前子集引用了 compact media 没覆盖的路径，需要换抽样策略、缩小子集，或准备更多上游 media。

### 5. 查看子集引用了哪些数据源

```bash
python - <<'PY'
from collections import Counter
p = "/data/geosr_static/GeoSR-static/train/spar_50k_media.txt"
c = Counter()
for line in open(p, encoding="utf-8"):
    parts = line.strip().split("/")
    c["/".join(parts[:3])] += 1
for k, v in c.most_common():
    print(f"{v:8d}  {k}")
PY
```

这一步能告诉你当前子集主要来自：

```text
spar/scannet/...
spar/scannetpp/...
spar/structured3d/...
spar/rxr/...
```

如果某一个 source 缺失特别多，可以针对它单独处理。

### 6. 软链接 media 到 GeoSR 训练目录

假设你的 GeoSR static 分支工作目录是：

```bash
/path/to/GeoSR-static
```

推荐不要复制图片，使用软链接：

```bash
cd /path/to/CVPR
python scripts/link_required_media.py \
  --media-list /data/geosr_static/GeoSR-static/train/spar_50k_media.txt \
  --source-root /data/geosr_static/media \
  --target-root /path/to/GeoSR-static/data/media \
  --mode symlink \
  --missing-output /data/geosr_static/GeoSR-static/train/link_missing_media.txt
```

然后链接 annotation：

```bash
mkdir -p /path/to/GeoSR-static/data/train
ln -sf /data/geosr_static/GeoSR-static/train/spar_50k.json \
  /path/to/GeoSR-static/data/train/spar_234k.json
```

这样做的好处是：GeoSR 原始代码仍然以为自己在读 `data/train/spar_234k.json`，但实际读的是你的 50k 子集。

### 7. 第一轮建议先不用 LLaVA-Hound

作者 static recipe 是：

```text
spar_234k + llava_hound_64k
```

但你的第一轮目标是验证 geometry layer，因此建议先只跑：

```text
spar_50k
```

也就是把训练脚本里的：

```bash
DATASETS="spar_234k,llava_hound_64k"
```

临时改成：

```bash
DATASETS="spar_234k"
```

这样可以避免准备 LLaVA-Hound 视频 media。

### 8. 评测集 VSI-Bench

VSI-Bench 建议完整下载。若 evaluator 需要解压后的目录：

```bash
cd /data/geosr_static/VSI-Bench
unzip scannet.zip
unzip scannetpp.zip
unzip arkitscenes.zip
```

## 1 TB 空间建议分配

| 组件 | 建议预算 |
|---|---:|
| VSI-Bench | 10-20 GB |
| SPAR compact media | 5-20 GB |
| 模型缓存 | 20-30 GB |
| 训练 annotation | <10 GB |
| 50k-100k 子集的 VGGT feature cache | 50-400 GB |
| checkpoints / logs / eval outputs | 50-100 GB |
| buffer | 200 GB 以上 |

目前看，若 SPAR compact media 覆盖率足够，真正占空间的会是后续的 VGGT 多层 feature cache，而不是原始 SPAR 图片。

## 脚本清单

| 脚本 | 作用 |
|---|---|
| `scripts/download_geosr_static_data.sh` | 下载 VSI-Bench、VG-LLM annotations、SPAR compact media、Qwen/VGGT 模型。 |
| `scripts/extract_spar_compact_media.sh` | 解压 `rxr/scannet/scannetpp/structured3d` compact media 到数据根目录。 |
| `scripts/sample_spar_subset.py` | 从 `spar_234k.json` 抽样，生成 `spar_50k.json` 和 media 清单。 |
| `scripts/check_media_availability.py` | 检查 media 清单在某个根目录下的覆盖率。 |
| `scripts/link_required_media.py` | 按 media 清单把文件软链接/硬链接/复制到 GeoSR 训练目录。 |

## 后续实验建议

第一轮只做：

```text
spar_50k + 完整 VSI-Bench + GeoSR-style mask/gate
```

比较：

```text
默认 VGGT 层（GeoSR 代码中是 aggregated_tokens_list[-2]）
final VGGT 层
middle VGGT 层
early VGGT 层
```

如果中间层优于默认/最终层，再扩展到：

```text
spar_100k
加入 llava_hound_64k
预提多层 VGGT features
2D visual token layer ablation
```
