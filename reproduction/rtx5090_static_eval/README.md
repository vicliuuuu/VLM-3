# GeoSR3D 静态评测：RTX 5090 可复现记录

本目录记录 GeoSR3D 官方 checkpoint 在 VSI-Bench 上的完整复现流程。文档和脚本以 2 张 NVIDIA GeForce RTX 5090 的工作站为基准，但正式全量评测使用单卡，以规避本次测试中 `lmms_eval` 多卡同步停滞的问题。

## 已验证结果

| 项目 | 实测值 |
| --- | ---: |
| GeoSR commit | `d2455359fcf62555eb04686e397aa1ab9393df9f` |
| VSI-Bench 样本数 | 5130 |
| 唯一 `doc_id` | 5130 |
| 官方 README 总分 | 51.9 |
| 本次复现总分 | **51.6952** |
| 单卡全量耗时 | 约 4 小时 30 分钟 |

分项结果：

| 指标 | 分数 |
| --- | ---: |
| Object Counting | 68.1239 |
| Absolute Distance | 38.0815 |
| Object Size | 57.2403 |
| Room Size | 62.9514 |
| Relative Distance | 48.3099 |
| Relative Direction | 44.0642 |
| Route Planning | 35.5670 |
| Appearance Order | 59.2233 |

## 文档索引

1. [README_01_ENVIRONMENT.md](README_01_ENVIRONMENT.md)：创建 RTX 5090 环境。
2. [README_02_VERIFY_ENVIRONMENT.md](README_02_VERIFY_ENVIRONMENT.md)：验证 CUDA、FlashAttention、视频解码和 GeoSR 入口。
3. [README_03_DATA_AND_CHECKPOINT.md](README_03_DATA_AND_CHECKPOINT.md)：下载、解压并验证 VSI-Bench 与官方 checkpoint。
4. [README_04_EVALUATION.md](README_04_EVALUATION.md)：单样本冒烟测试和全量评测。

## 最短执行路径

以下命令均从本目录执行：

```bash
cd reproduction/rtx5090_static_eval

bash scripts/create_environment.sh "$HOME/work/GeoSR-official"
conda activate geosr

python scripts/verify_environment.py --geosr-repo "$HOME/work/GeoSR-official"

bash scripts/download_assets.sh /path/to/geosr_static "$HOME/work/GeoSR-official"
python scripts/verify_assets.py --data-root /path/to/geosr_static

LIMIT=1 bash scripts/run_vsibench.sh \
  "$HOME/work/GeoSR-official" /path/to/geosr_static

bash scripts/run_vsibench.sh \
  "$HOME/work/GeoSR-official" /path/to/geosr_static
```

不要跳过 `LIMIT=1` 冒烟测试。它会在十几秒内暴露模型加载、显存、视频路径和结果输出问题，避免全量任务运行数小时后才失败。

## 目录约定

```text
/path/to/geosr_static/
├── VSI-Bench/
│   ├── test.jsonl
│   ├── arkitscenes/
│   ├── scannet/
│   ├── scannetpp/
│   └── DATA/
├── models/
│   └── GeoSR3D-Model/
└── eval/
```

大文件不进入 Git。Git 中只保存环境约束、下载命令、验证逻辑和评测命令。
