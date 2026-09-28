# 04. 官方 checkpoint 评测

## 1. 冒烟测试

```bash
conda activate geosr
cd reproduction/rtx5090_static_eval

LIMIT=1 GPU_ID=0 bash scripts/run_vsibench.sh \
  "$HOME/work/GeoSR-official" /path/to/geosr_static
```

在已验证机器上，单样本生成约 3.75 秒。首次启动还包括约数秒的 checkpoint 加载时间。

## 2. 全量评测

不设置 `LIMIT` 即运行全部 5130 题：

```bash
GPU_ID=0 OUTPUT_NAME=official_geosr3d_vsibench_full \
bash scripts/run_vsibench.sh \
  "$HOME/work/GeoSR-official" /path/to/geosr_static
```

脚本使用的核心参数与官方脚本一致：

```text
--model geosr3d
--model_args pretrained=<checkpoint>,use_flash_attention_2=true,max_num_frames=32,max_length=12800
--tasks vsibench
--batch_size 1
```

额外启用 `--log_samples`，便于检查 5130 条预测，不会改变模型输入或指标计算。

## 3. 输出验证

```bash
python scripts/verify_results.py \
  --result-dir /path/to/geosr_static/eval/official_geosr3d_vsibench_full \
  --expected-samples 5130
```

脚本检查：

- 存在唯一的 `*_results.json`。
- 存在唯一的 `*_samples_vsibench.jsonl`。
- 样本数和唯一 `doc_id` 均为 5130。
- `vsibench_score` 及八个分项指标均存在且为有限数值。

## 4. 本次实测结果

```text
vsibench_score   51.6952
vsi_obj_count    68.1239
vsi_abs_dist     38.0815
vsi_obj_size     57.2403
vsi_room_size    62.9514
vsi_rel_dist     48.3099
vsi_rel_dir      44.0642
vsi_route_plan   35.5670
vsi_appr_order   59.2233
```

官方 README 给出的总分为 51.9。本次差值约 0.20 分，5130 条样本全部完成，可以认为评测流程和 checkpoint 复现成功。

## 5. 多卡说明

本次尝试 `accelerate launch --multi_gpu --num_processes 2` 时，两张卡均成功加载模型，但进程在任务构建后的分布式同步点停滞。因此最终结果使用单张 RTX 5090 产生。

在没有重新验证前，不要直接把全量命令改成 DDP。若需要并行加速，应把 JSONL 划分为互斥子集、分别推理，再使用同一官方聚合函数合并全部样本；不能简单平均两个子集的八项分数。
