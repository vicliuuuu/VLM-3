#!/usr/bin/env python3
"""Sample SPAR annotations and list referenced media paths.

Usage:
  python scripts/sample_spar_subset.py \
    --input /data/GeoSR-static/train/spar_234k.json \
    --output /data/GeoSR-static/train/spar_50k.json \
    --media-list /data/GeoSR-static/train/spar_50k_media.txt \
    --num-samples 50000 \
    --seed 0

The output JSON can be used as a controlled training subset. The media list
contains the relative image paths referenced by that subset, so you can prepare
only the required images under GeoSR's `data/media` root.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def collect_media_paths(sample: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("image", "images"):
        value = sample.get(key)
        if isinstance(value, str):
            paths.append(value)
        elif isinstance(value, list):
            paths.extend(x for x in value if isinstance(x, str))

    video = sample.get("video")
    if isinstance(video, str):
        paths.append(video)
    elif isinstance(video, list):
        paths.extend(x for x in video if isinstance(x, str))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--media-list", required=True, type=Path)
    parser.add_argument("--num-samples", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if args.num_samples > len(data):
        raise ValueError(f"--num-samples={args.num_samples} exceeds dataset size {len(data)}")

    rng = random.Random(args.seed)
    sampled = rng.sample(data, args.num_samples)

    media_paths: set[str] = set()
    for sample in sampled:
        media_paths.update(collect_media_paths(sample))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.media_list.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8") as f:
        json.dump(sampled, f, ensure_ascii=False)

    with args.media_list.open("w", encoding="utf-8") as f:
        for path in sorted(media_paths):
            f.write(path + "\n")

    print(f"Loaded samples:   {len(data)}")
    print(f"Saved subset:     {len(sampled)} -> {args.output}")
    print(f"Referenced media: {len(media_paths)} paths -> {args.media_list}")


if __name__ == "__main__":
    main()
