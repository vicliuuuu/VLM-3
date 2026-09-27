# GeoSR 静态实验数据准备与验证计划

## 目标与实验定位

目标是在约 1 TB 可用空间内，完成一个可复现的 GeoSR-style 静态实验，并验证不同 VGGT 表示层对空间任务的影响。第一阶段属于 **controlled layer-probing study**，不是对 GeoSR 论文结果的严格复现，因为训练数据会缩小，并暂时不使用 LLaVA-Hound。

核心原则：

- 最终评测固定使用 VSI-Bench，但不能用它选择 geometry layer、mask 参数或 checkpoint。
- 从 SPAR 训练数据中建立 scene-disjoint development split，用于所有模型选择。
- 所有比较方法使用完全相同的训练样本、顺序、训练步数、随机种子和评测协议。
- 报告本地 baseline 与改动方法之间的相对变化，不把缩小数据后的绝对分数与论文表格直接比较。
- 保存数据 manifest、输入哈希、抽样 seed、任务分布和 scene 分布。

## 需要先澄清的数据事实

spar_234k.json 只是 annotation，不包含训练图像。SPAR-7M 官方仓库中的 rxr.tar.gz、scannet.tar.gz、scannetpp.tar.gz 和 structured3d.tar.gz 主要包含 annotation；SPAR 官方不重新分发受第三方许可约束的原始 RGB 数据。

因此不能假设下载约 3 GB 的 SPAR 压缩包后就能得到：

~~~text
spar/scannet/images/...
spar/scannetpp/images/...
spar/structured3d/images/...
spar/rxr/images/...
~~~

正确做法是：

1. 下载 GeoSR/VG-LLM 发布的 annotation 和 spar_7m.tar.gz。
2. 检查压缩包成员，确认它是否真的含有 annotation 所引用的图片。
3. 如果不包含图片，按照上游数据集许可获取数据，并使用 SPAR 官方 preparation scripts 生成所需目录结构。
4. 先建立“media 完整的可用样本全集”，再从中抽样，避免根据缺失情况反复重抽而引入隐性偏差。

官方入口：

- GeoSR: https://github.com/SuhZhang/GeoSR
- SPAR-7M: https://huggingface.co/datasets/jasonzhango/SPAR-7M
- VG-LLM-Data: https://huggingface.co/datasets/zd11024/VG-LLM-Data
- VSI-Bench: https://huggingface.co/datasets/nyu-visionx/VSI-Bench

## 推荐目录

~~~text
/data/geosr_static/
├── GeoSR-static/
│   └── train/
├── VSI-Bench/
├── media/
│   └── spar/
├── models/
├── hf_cache/
└── manifests/
~~~

以下命令假设当前目录为：

~~~bash
cd /path/to/CVPR/VLM-3
~~~

## 一句话流程

~~~text
下载 annotation / VSI-Bench / 模型
-> 检查发布的 SPAR 包是否包含 RGB
-> 按上游许可准备缺失 media
-> 对完整 annotation 做样本级 media 审计
-> 从 media 完整全集分层抽取 55k
-> 按 scene 划分约 50k train + 5k development
-> 固定 manifest 和训练预算
-> 在 development 上做 layer probing
-> 锁定方案后仅在 VSI-Bench 上进行最终评测
~~~

## 1. 下载公开文件

脚本不会安装或升级 Python 包，也不会把 SPAR annotation archives 当作 RGB media。服务器应预先安装 Hugging Face CLI。

~~~bash
python -m pip install -U "huggingface_hub[cli]"
bash scripts/download_geosr_static_data.sh /data/geosr_static
~~~

如暂时不下载模型：

~~~bash
DOWNLOAD_MODELS=0 bash scripts/download_geosr_static_data.sh /data/geosr_static
~~~

下载内容：

~~~text
/data/geosr_static/VSI-Bench
/data/geosr_static/GeoSR-static/train/spar_234k.json
/data/geosr_static/GeoSR-static/train/llava_hound_64k.json
/data/geosr_static/GeoSR-static/train/spar_7m.tar.gz
/data/geosr_static/models
~~~

## 2. 检查发布的 SPAR 包

~~~bash
bash scripts/extract_spar_compact_media.sh /data/geosr_static
~~~

脚本会先检查 archive member：

- 如果发现图片且路径安全，才解压到 /data/geosr_static/media。
- 如果没有图片，以状态码 2 退出，并明确提示该包不能作为 media。
- 如果存在绝对路径或父目录跳转，拒绝解压。

没有图片不是异常结论，而是说明需要从获得授权的上游数据生成 SPAR 所需 RGB layout。不要通过非官方来源复制图片来绕过数据许可。

## 3. 建立 media 完整样本全集

上游 media 准备好后，先对完整 spar_234k.json 做样本级审计：

~~~bash
python scripts/check_media_availability.py \
  --annotation /data/geosr_static/GeoSR-static/train/spar_234k.json \
  --media-root /data/geosr_static/media \
  --missing-output /data/geosr_static/manifests/spar_234k_missing_media.txt \
  --valid-output /data/geosr_static/GeoSR-static/train/spar_media_complete.json
~~~

需要同时检查：

~~~text
Path coverage
Sample coverage
Incomplete samples by task
Missing path prefixes
~~~

实验使用的是“所有引用 media 均存在”的样本，而不是仅根据唯一文件路径覆盖率判断。如果某个数据源缺失严重，应先决定是否补齐该数据源；若受 1 TB 限制只能使用部分数据源，需要把 source restriction 写进实验名称和报告。

## 4. 分层抽取候选子集

从 media 完整全集抽取 55k，随后再划分约 50k train 和 5k development：

~~~bash
python scripts/sample_spar_subset.py \
  --input /data/geosr_static/GeoSR-static/train/spar_media_complete.json \
  --output /data/geosr_static/GeoSR-static/train/spar_probe_55k.json \
  --media-list /data/geosr_static/GeoSR-static/train/spar_probe_55k_media.txt \
  --manifest /data/geosr_static/manifests/spar_probe_55k_manifest.json \
  --media-root /data/geosr_static/media \
  --num-samples 55000 \
  --strategy stratified \
  --seed 0
~~~

默认分层变量为：

~~~text
task type × data source × view-count bucket
~~~

如果 media 完整样本不足 55k，脚本会直接报错。此时应明确降低样本目标，例如统一改成 30k，而不是不断更换 seed 直到得到“看起来合适”的子集。

## 5. 建立 scene-disjoint development split

~~~bash
python scripts/split_spar_by_scene.py \
  --input /data/geosr_static/GeoSR-static/train/spar_probe_55k.json \
  --train-output /data/geosr_static/GeoSR-static/train/spar_probe_train.json \
  --val-output /data/geosr_static/GeoSR-static/train/spar_probe_dev.json \
  --manifest /data/geosr_static/manifests/spar_probe_split_manifest.json \
  --val-ratio 0.09 \
  --seed 0
~~~

scene 数量不同，因此实际样本数不会严格等于 50k/5k。manifest 必须满足：

~~~text
scene_overlap = 0
~~~

如果脚本无法从某类路径可靠解析 scene ID，它会停止并输出示例。不要把无法识别的样本随机分到 train/dev，否则同一场景可能同时出现。

此外，在正式实验前还需单独审计 SPAR train 与 VSI-Bench 的 source + scene_id 交集。若存在交集，应过滤训练场景或明确说明采用的是论文原始协议；更稳妥的主结果应使用 scene-disjoint 训练数据。

## 6. 最终完整性检查

~~~bash
python scripts/check_media_availability.py \
  --annotation /data/geosr_static/GeoSR-static/train/spar_probe_train.json \
  --media-root /data/geosr_static/media \
  --require-complete

python scripts/check_media_availability.py \
  --annotation /data/geosr_static/GeoSR-static/train/spar_probe_dev.json \
  --media-root /data/geosr_static/media \
  --require-complete
~~~

任意样本缺失 media 时，--require-complete 会返回非零状态，训练不应继续。

## 7. 链接 media

候选 55k 的 media 清单覆盖 train 和 development，可统一链接：

~~~bash
python scripts/link_required_media.py \
  --media-list /data/geosr_static/GeoSR-static/train/spar_probe_55k_media.txt \
  --source-root /data/geosr_static/media \
  --target-root /path/to/GeoSR-static/data/media \
  --mode symlink \
  --missing-output /data/geosr_static/manifests/link_missing_media.txt
~~~

链接脚本会拒绝绝对路径和父目录跳转。推荐在 GeoSR dataset config 中显式填写 spar_probe_train.json 和 spar_probe_dev.json。

不要长期把 50k 文件伪装成 spar_234k.json。如果原始代码暂时只能识别固定文件名，必须在 run name 和实验 manifest 中记录真实 annotation 路径与 SHA256。

## 8. VSI-Bench 使用协议

VSI-Bench 建议完整下载和解压：

~~~bash
cd /data/geosr_static/VSI-Bench
unzip scannet.zip
unzip scannetpp.zip
unzip arkitscenes.zip
~~~

正确使用顺序：

1. 先用 GeoSR 官方 checkpoint 跑一次 VSI-Bench，确认 evaluator、数据路径和指标实现正确。
2. 在 spar_probe_dev.json 上选择 geometry layer、mask 设置和 checkpoint。
3. 锁定配置后再运行 VSI-Bench。
4. 不根据 VSI-Bench 分任务结果回头调整 layer 或超参数。

## 9. 第一阶段实验矩阵

统一使用 SPAR probe train、相同训练步数和相同 seed：

~~~text
no-geometry control
default GeoSR geometry representation
early VGGT layer
middle VGGT layer
late VGGT layer
final VGGT layer
fixed multi-level geometry control
~~~

第一阶段只使用 SPAR 时，结果名称应写为：

~~~text
GeoSR-style SPAR-probe baseline
~~~

而不是“GeoSR reproduction”。加入完整 spar_234k + llava_hound_64k 并复现官方训练预算后，才适合讨论论文级复现误差。

Layer probing 的目标不是只判断“哪个层平均分最高”，而是检查不同任务是否出现稳定的 layer preference。至少分别报告：

~~~text
depth / absolute distance / relative distance
relative direction
object size / room size
route planning
appearance order
overall
~~~

## 10. VGGT feature cache 预算

不要直接按“50k 样本 × 若干层”缓存原始 VGGT token。以 518 × 518、patch size 14、hidden size 约 2048、bf16 粗略估算：

~~~text
1369 tokens × 2048 × 2 bytes ≈ 5.6 MB / frame / layer
~~~

若平均每个样本 4 帧，50k 样本的单层原始 token 理论量级可超过 1 TB。实际值会受到重复视觉输入、token merging、帧数和存储格式影响，因此原先的 50-400 GB 不能作为默认预算。

推荐顺序：

1. 第一轮在线运行 VGGT，先不做全量 cache。
2. 用 100-500 个真实样本测量平均帧数、token shape、dtype、吞吐和落盘体积。
3. cache 以“唯一且有序的视觉输入 + preprocessing hash”为 key，而不是以 QA sample 为 key。
4. 多个 QA 共享同一视觉输入时只保存一份 feature。
5. 若必须缓存，优先保存选定层，并使用分片文件，避免产生几十万个小文件。
6. 只有 projector 固定时才能安全缓存 projector 之后的表示；若 projector 参与训练，应缓存 projector 之前的 VGGT feature。

## 1 TB 空间策略

| 组件 | 建议 |
|---|---|
| VSI-Bench | 完整保留 |
| SPAR annotation | 完整保留，体积较小 |
| 上游 RGB media | 按许可和实际可用 source 规划，先实测 |
| Qwen2.5-VL-7B + VGGT-1B | 单独保留一份模型快照，避免 cache 重复 |
| VGGT feature cache | 第一阶段不做全量 cache |
| checkpoints | 只保留关键 step 和 best-on-development |
| buffer | 至少预留 150-200 GB |

如果获得授权的上游 RGB media 本身超过预算，应缩小并固定 source 范围，而不是依赖一个并不存在的 3 GB compact-media 假设。

## 脚本清单

| 脚本 | 作用 |
|---|---|
| scripts/download_geosr_static_data.sh | 下载 VSI-Bench、训练 annotation 和模型，不声称下载 SPAR RGB media。 |
| scripts/extract_spar_compact_media.sh | 检查发布包是否真的包含图片，只在安全且含图片时解压。 |
| scripts/check_media_availability.py | 同时检查路径覆盖率和样本完整率，可输出 media-complete annotation。 |
| scripts/sample_spar_subset.py | 从 media 完整全集做分层抽样，并保存 SHA256 和分布 manifest。 |
| scripts/split_spar_by_scene.py | 生成 scene-disjoint train/development split。 |
| scripts/link_required_media.py | 安全地链接、硬链接或复制经过验证的相对 media 路径。 |

## 第一阶段完成标准

进入 geometry layer ablation 前，应同时满足：

- 官方 checkpoint 可以在本地 VSI-Bench evaluator 上正常评测。
- train/development scene overlap 为 0。
- train 和 development 的 sample-level media coverage 均为 100%。
- 所有方法读取同一 annotation SHA256。
- 数据分布、seed、训练步数和代码 commit 已记录。
- layer 和 checkpoint 只根据 development 选择。
- VSI-Bench 只用于锁定配置后的最终结果。
