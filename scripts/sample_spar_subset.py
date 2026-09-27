#!/usr/bin/env python3
"""Create a reproducible, media-complete SPAR subset.

The default strategy preserves the joint distribution of task, source, and
view-count bucket. When --media-root is supplied, only samples for which every
referenced media file exists are eligible for sampling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


KNOWN_SOURCES = ("scannetpp", "scannet", "structured3d", "rxr", "matterport3d")
TASK_KEYS = ("qa_type", "task_type", "type", "dataset_name")


def normalize_relative_path(raw: str) -> str:
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe media path: {raw!r}")
    normalized = str(path)
    if normalized in ("", "."):
        raise ValueError(f"Empty media path: {raw!r}")
    return normalized


def collect_media_paths(sample: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("image", "images", "video"):
        value = sample.get(key)
        if isinstance(value, str):
            paths.append(normalize_relative_path(value))
        elif isinstance(value, list):
            paths.extend(
                normalize_relative_path(item)
                for item in value
                if isinstance(item, str)
            )
    return paths


def infer_source(paths: Iterable[str]) -> str:
    lowered_parts = [part.lower() for path in paths for part in PurePosixPath(path).parts]
    for source in KNOWN_SOURCES:
        if source in lowered_parts:
            return source
    return "unknown"


def infer_task(sample: dict[str, Any]) -> str:
    for key in TASK_KEYS:
        value = sample.get(key)
        if isinstance(value, str) and value:
            return value
    return "unknown"


def view_bucket(count: int) -> str:
    if count <= 1:
        return "1"
    if count <= 4:
        return "2-4"
    if count <= 8:
        return "5-8"
    return "9+"


def stratum(sample: dict[str, Any]) -> tuple[str, str, str]:
    paths = collect_media_paths(sample)
    return infer_task(sample), infer_source(paths), view_bucket(len(paths))


def format_stratum(key: tuple[str, str, str]) -> str:
    return " | ".join(key)


def proportional_allocation(group_sizes: dict[tuple[str, str, str], int], total: int) -> dict[tuple[str, str, str], int]:
    population = sum(group_sizes.values())
    if total > population:
        raise ValueError(f"Requested {total} samples from an eligible population of {population}")

    exact = {key: total * size / population for key, size in group_sizes.items()}
    allocation = {key: min(size, math.floor(exact[key])) for key, size in group_sizes.items()}
    remaining = total - sum(allocation.values())

    order = sorted(
        group_sizes,
        key=lambda key: (exact[key] - math.floor(exact[key]), group_sizes[key], format_stratum(key)),
        reverse=True,
    )
    while remaining:
        progressed = False
        for key in order:
            if allocation[key] < group_sizes[key]:
                allocation[key] += 1
                remaining -= 1
                progressed = True
                if remaining == 0:
                    break
        if not progressed:
            raise RuntimeError("Unable to complete proportional allocation")
    return allocation


def stratified_sample(
    samples: list[dict[str, Any]], num_samples: int, rng: random.Random
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        groups[stratum(sample)].append(sample)

    allocation = proportional_allocation(
        {key: len(values) for key, values in groups.items()}, num_samples
    )
    selected: list[dict[str, Any]] = []
    for key in sorted(groups, key=format_stratum):
        values = list(groups[key])
        rng.shuffle(values)
        selected.extend(values[: allocation[key]])
    rng.shuffle(selected)
    return selected


def distribution(samples: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(format_stratum(stratum(sample)) for sample in samples)
    return dict(sorted(counts.items()))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--media-list", required=True, type=Path)
    parser.add_argument("--num-samples", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--strategy", choices=("stratified", "random"), default="stratified")
    parser.add_argument(
        "--media-root",
        type=Path,
        help="Restrict eligibility to samples whose referenced media all exist.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Defaults to <output>.manifest.json.",
    )
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise TypeError("Expected the input annotation to be a JSON list of objects")

    eligible: list[dict[str, Any]] = []
    incomplete_samples = 0
    media_root = args.media_root.resolve() if args.media_root else None
    for sample in data:
        paths = collect_media_paths(sample)
        if media_root is not None:
            complete = bool(paths) and all((media_root / path).is_file() for path in paths)
            if not complete:
                incomplete_samples += 1
                continue
        eligible.append(sample)

    if args.num_samples > len(eligible):
        raise ValueError(
            f"--num-samples={args.num_samples} exceeds eligible dataset size {len(eligible)}"
        )

    rng = random.Random(args.seed)
    if args.strategy == "stratified":
        sampled = stratified_sample(eligible, args.num_samples, rng)
    else:
        sampled = rng.sample(eligible, args.num_samples)

    media_paths = sorted(
        {path for sample in sampled for path in collect_media_paths(sample)}
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.media_list.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8") as stream:
        json.dump(sampled, stream, ensure_ascii=False)
        stream.write("\n")
    with args.media_list.open("w", encoding="utf-8") as stream:
        for path in media_paths:
            stream.write(path + "\n")

    manifest_path = args.manifest or args.output.with_suffix(
        args.output.suffix + ".manifest.json"
    )
    manifest = {
        "input": str(args.input.resolve()),
        "input_sha256": sha256_file(args.input),
        "output": str(args.output.resolve()),
        "seed": args.seed,
        "strategy": args.strategy,
        "requested_samples": args.num_samples,
        "input_samples": len(data),
        "eligible_samples": len(eligible),
        "incomplete_samples_excluded": incomplete_samples,
        "referenced_media_paths": len(media_paths),
        "strata": {
            "input": distribution(data),
            "eligible": distribution(eligible),
            "output": distribution(sampled),
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    print(f"Loaded samples:      {len(data)}")
    print(f"Eligible samples:    {len(eligible)}")
    print(f"Excluded incomplete: {incomplete_samples}")
    print(f"Saved subset:        {len(sampled)} -> {args.output}")
    print(f"Referenced media:    {len(media_paths)} -> {args.media_list}")
    print(f"Manifest:            {manifest_path}")


if __name__ == "__main__":
    main()
