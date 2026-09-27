#!/usr/bin/env python3
"""Create deterministic scene-disjoint train and development splits."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


KNOWN_SOURCES = ("scannetpp", "scannet", "structured3d", "rxr", "matterport3d")


def collect_media_paths(sample: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("image", "images", "video"):
        value = sample.get(key)
        if isinstance(value, str):
            paths.append(value.replace("\\", "/"))
        elif isinstance(value, list):
            paths.extend(item.replace("\\", "/") for item in value if isinstance(item, str))
    return paths


def infer_source_and_scene(path: str) -> tuple[str, str] | None:
    parts = PurePosixPath(path).parts
    lowered = [part.lower() for part in parts]
    source = next((name for name in KNOWN_SOURCES if name in lowered), None)
    if source is None:
        return None

    for part in parts:
        if re.fullmatch(r"scene_?\d+(?:_\d+)?", part, flags=re.IGNORECASE):
            return source, part

    if "images" in lowered:
        index = lowered.index("images")
        if index + 1 < len(parts):
            return source, parts[index + 1]

    source_index = lowered.index(source)
    if source_index + 1 < len(parts):
        candidate = parts[source_index + 1]
        if candidate.lower() not in {"images", "qa_jsonl", "train", "val"}:
            return source, candidate
    return None


def scene_key(sample: dict[str, Any]) -> tuple[str, str] | None:
    keys = {
        inferred
        for path in collect_media_paths(sample)
        if (inferred := infer_source_and_scene(path)) is not None
    }
    if not keys:
        return None
    if len(keys) > 1:
        raise ValueError(f"Sample references multiple scenes: {sorted(keys)}")
    return next(iter(keys))


def task_label(sample: dict[str, Any]) -> str:
    for key in ("qa_type", "task_type", "type", "dataset_name"):
        value = sample.get(key)
        if isinstance(value, str) and value:
            return value
    return "unknown"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2 if isinstance(value, dict) else None)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--train-output", required=True, type=Path)
    parser.add_argument("--val-output", required=True, type=Path)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    if not 0.0 < args.val_ratio < 0.5:
        parser.error("--val-ratio must be between 0 and 0.5")

    with args.input.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise TypeError("Expected the input annotation to be a JSON list of objects")

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    unknown_examples: list[list[str]] = []
    for sample in data:
        key = scene_key(sample)
        if key is None:
            if len(unknown_examples) < 10:
                unknown_examples.append(collect_media_paths(sample))
            continue
        groups[key].append(sample)

    unknown_count = len(data) - sum(len(samples) for samples in groups.values())
    if unknown_count:
        preview = "\n".join(f"  {paths}" for paths in unknown_examples)
        raise ValueError(
            f"Could not infer a scene for {unknown_count} samples. "
            "Refine infer_source_and_scene before splitting. Examples:\n" + preview
        )

    by_source: dict[str, list[tuple[str, list[dict[str, Any]]]]] = defaultdict(list)
    for (source, scene), samples in groups.items():
        by_source[source].append((scene, samples))

    rng = random.Random(args.seed)
    val_keys: set[tuple[str, str]] = set()
    for source, source_groups in sorted(by_source.items()):
        candidates = list(source_groups)
        rng.shuffle(candidates)
        target = round(sum(len(samples) for _, samples in candidates) * args.val_ratio)
        current = 0
        for scene, samples in candidates:
            if len(candidates) - sum(1 for key in val_keys if key[0] == source) <= 1:
                break
            proposed = current + len(samples)
            if abs(target - proposed) < abs(target - current):
                val_keys.add((source, scene))
                current = proposed
        if target > 0 and not any(key[0] == source for key in val_keys) and len(candidates) > 1:
            scene, samples = min(candidates, key=lambda item: len(item[1]))
            val_keys.add((source, scene))

    train: list[dict[str, Any]] = []
    val: list[dict[str, Any]] = []
    train_scenes: set[tuple[str, str]] = set()
    val_scenes: set[tuple[str, str]] = set()
    for key, samples in groups.items():
        if key in val_keys:
            val.extend(samples)
            val_scenes.add(key)
        else:
            train.extend(samples)
            train_scenes.add(key)

    if train_scenes & val_scenes:
        raise AssertionError("Train/validation scene overlap detected")
    rng.shuffle(train)
    rng.shuffle(val)

    write_json(args.train_output, train)
    write_json(args.val_output, val)
    manifest_path = args.manifest or args.input.with_suffix(
        args.input.suffix + ".split_manifest.json"
    )
    manifest = {
        "input": str(args.input.resolve()),
        "input_sha256": sha256_file(args.input),
        "seed": args.seed,
        "requested_val_ratio": args.val_ratio,
        "train_samples": len(train),
        "val_samples": len(val),
        "actual_val_ratio": len(val) / len(data) if data else 0.0,
        "train_scenes": len(train_scenes),
        "val_scenes": len(val_scenes),
        "scene_overlap": 0,
        "train_tasks": dict(sorted(Counter(task_label(item) for item in train).items())),
        "val_tasks": dict(sorted(Counter(task_label(item) for item in val).items())),
    }
    write_json(manifest_path, manifest)

    print(f"Input samples: {len(data)}")
    print(f"Train samples/scenes: {len(train)} / {len(train_scenes)}")
    print(f"Validation samples/scenes: {len(val)} / {len(val_scenes)}")
    print(f"Scene overlap: {len(train_scenes & val_scenes)}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
