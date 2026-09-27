#!/usr/bin/env python3
"""Audit path-level and sample-level media completeness."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any


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


def sample_label(sample: dict[str, Any]) -> str:
    for key in ("qa_type", "task_type", "type", "dataset_name"):
        value = sample.get(key)
        if isinstance(value, str) and value:
            return value
    return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--media-list", type=Path)
    group.add_argument("--annotation", type=Path)
    parser.add_argument("--media-root", required=True, type=Path)
    parser.add_argument("--missing-output", type=Path)
    parser.add_argument(
        "--valid-output",
        type=Path,
        help="Write samples whose complete media set exists; requires --annotation.",
    )
    parser.add_argument("--show", type=int, default=20)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Exit with status 2 when any path or sample is incomplete.",
    )
    args = parser.parse_args()

    if args.valid_output and not args.annotation:
        parser.error("--valid-output requires --annotation")

    samples: list[dict[str, Any]] | None = None
    if args.media_list:
        with args.media_list.open("r", encoding="utf-8") as stream:
            paths = sorted(
                {normalize_relative_path(line.strip()) for line in stream if line.strip()}
            )
    else:
        with args.annotation.open("r", encoding="utf-8") as stream:
            loaded = json.load(stream)
        if not isinstance(loaded, list) or not all(isinstance(item, dict) for item in loaded):
            raise TypeError("Expected the annotation to be a JSON list of objects")
        samples = loaded
        paths = sorted({path for sample in samples for path in collect_media_paths(sample)})

    media_root = args.media_root.resolve()
    found = [path for path in paths if (media_root / path).is_file()]
    missing = [path for path in paths if not (media_root / path).is_file()]
    coverage = 0.0 if not paths else len(found) / len(paths) * 100

    print(f"Media root: {media_root}")
    print(f"Unique required paths: {len(paths)}")
    print(f"Found paths: {len(found)}")
    print(f"Missing paths: {len(missing)}")
    print(f"Path coverage: {coverage:.2f}%")

    valid_samples: list[dict[str, Any]] = []
    incomplete_samples: list[dict[str, Any]] = []
    if samples is not None:
        missing_set = set(missing)
        incomplete_by_task: Counter[str] = Counter()
        no_media = 0
        for sample in samples:
            sample_paths = collect_media_paths(sample)
            complete = bool(sample_paths) and not any(path in missing_set for path in sample_paths)
            if complete:
                valid_samples.append(sample)
            else:
                incomplete_samples.append(sample)
                incomplete_by_task[sample_label(sample)] += 1
                if not sample_paths:
                    no_media += 1

        sample_coverage = 0.0 if not samples else len(valid_samples) / len(samples) * 100
        print(f"Total samples: {len(samples)}")
        print(f"Complete samples: {len(valid_samples)}")
        print(f"Incomplete samples: {len(incomplete_samples)}")
        print(f"Samples with no media path: {no_media}")
        print(f"Sample coverage: {sample_coverage:.2f}%")
        if incomplete_by_task:
            print("\nIncomplete samples by task:")
            for task, count in incomplete_by_task.most_common():
                print(f"  {count:8d}  {task}")

    if missing:
        prefixes = Counter("/".join(path.split("/")[:3]) for path in missing)
        print("\nMissing path prefixes:")
        for prefix, count in prefixes.most_common():
            print(f"  {count:8d}  {prefix}")
        print("\nMissing examples:")
        for path in missing[: args.show]:
            print(f"  {path}")

    if args.missing_output:
        args.missing_output.parent.mkdir(parents=True, exist_ok=True)
        with args.missing_output.open("w", encoding="utf-8") as stream:
            for path in missing:
                stream.write(path + "\n")
        print(f"\nSaved missing list: {args.missing_output}")

    if args.valid_output:
        args.valid_output.parent.mkdir(parents=True, exist_ok=True)
        with args.valid_output.open("w", encoding="utf-8") as stream:
            json.dump(valid_samples, stream, ensure_ascii=False)
            stream.write("\n")
        print(f"Saved media-complete annotation: {args.valid_output}")

    incomplete = bool(missing) or bool(incomplete_samples)
    if args.require_complete and incomplete:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
