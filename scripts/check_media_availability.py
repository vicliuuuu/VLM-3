#!/usr/bin/env python3
"""Check whether media paths referenced by an annotation/media list exist.

Examples:
  python scripts/check_media_availability.py \
    --media-list /data/geosr_static/GeoSR-static/train/spar_50k_media.txt \
    --media-root /data/geosr_static/media

  python scripts/check_media_availability.py \
    --annotation /data/geosr_static/GeoSR-static/train/spar_50k.json \
    --media-root /data/geosr_static/media \
    --missing-output /data/geosr_static/missing_media.txt
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
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


def load_paths(args: argparse.Namespace) -> list[str]:
    if args.media_list:
        with args.media_list.open("r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    with args.annotation.open("r", encoding="utf-8") as f:
        data = json.load(f)
    paths: set[str] = set()
    for sample in data:
        paths.update(collect_media_paths(sample))
    return sorted(paths)


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--media-list", type=Path)
    group.add_argument("--annotation", type=Path)
    parser.add_argument("--media-root", required=True, type=Path)
    parser.add_argument("--missing-output", type=Path)
    parser.add_argument("--show", type=int, default=20)
    args = parser.parse_args()

    paths = load_paths(args)
    found: list[str] = []
    missing: list[str] = []

    for rel in paths:
        if (args.media_root / rel).exists():
            found.append(rel)
        else:
            missing.append(rel)

    prefix_counter = Counter("/".join(p.split("/")[:3]) for p in paths)
    missing_prefix_counter = Counter("/".join(p.split("/")[:3]) for p in missing)

    total = len(paths)
    found_n = len(found)
    missing_n = len(missing)
    coverage = 0.0 if total == 0 else found_n / total * 100

    print(f"Media root: {args.media_root}")
    print(f"Total required paths: {total}")
    print(f"Found: {found_n}")
    print(f"Missing: {missing_n}")
    print(f"Coverage: {coverage:.2f}%")

    print("\nRequired path prefixes:")
    for prefix, count in prefix_counter.most_common():
        print(f"  {count:8d}  {prefix}")

    if missing:
        print("\nMissing path prefixes:")
        for prefix, count in missing_prefix_counter.most_common():
            print(f"  {count:8d}  {prefix}")

        print("\nMissing examples:")
        for rel in missing[: args.show]:
            print(f"  {rel}")

    if args.missing_output:
        args.missing_output.parent.mkdir(parents=True, exist_ok=True)
        with args.missing_output.open("w", encoding="utf-8") as f:
            for rel in missing:
                f.write(rel + "\n")
        print(f"\nSaved missing list: {args.missing_output}")


if __name__ == "__main__":
    main()
