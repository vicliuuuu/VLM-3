#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
import zipfile

from safetensors import safe_open


EXPECTED_SHARD_SIZES = {
    "model-00001-of-00004.safetensors": 4_934_281_216,
    "model-00002-of-00004.safetensors": 4_932_750_944,
    "model-00003-of-00004.safetensors": 4_991_495_888,
    "model-00004-of-00004.safetensors": 3_692_182_944,
}


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--expected-questions", type=int, default=5130)
    parser.add_argument("--expected-scenes", type=int, default=288)
    args = parser.parse_args()

    root = args.data_root.resolve()
    vsi = root / "VSI-Bench"
    model = root / "models" / "GeoSR3D-Model"

    for name in ("arkitscenes.zip", "scannet.zip", "scannetpp.zip"):
        path = vsi / name
        if not path.is_file():
            fail(f"missing archive: {path}")
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
        if bad_member is not None:
            fail(f"CRC failure in {path}: {bad_member}")
        print(f"[OK] ZIP CRC: {name}")

    annotation = vsi / "test.jsonl"
    if not annotation.is_file():
        fail(f"missing annotation: {annotation}")

    rows = []
    with annotation.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                fail(f"invalid JSON at line {line_number}: {error}")

    if len(rows) != args.expected_questions:
        fail(f"expected {args.expected_questions} questions, got {len(rows)}")

    scene_keys = {(row["dataset"], row["scene_name"]) for row in rows}
    if len(scene_keys) != args.expected_scenes:
        fail(f"expected {args.expected_scenes} scenes, got {len(scene_keys)}")

    missing_videos = []
    for dataset, scene_name in sorted(scene_keys):
        path = vsi / dataset / f"{scene_name}.mp4"
        if not path.is_file() or path.stat().st_size == 0:
            missing_videos.append(str(path))
    if missing_videos:
        fail(f"missing or empty videos: {missing_videos[:10]}")
    print(f"[OK] questions={len(rows)}, scenes={len(scene_keys)}, missing_videos=0")

    index_path = model / "model.safetensors.index.json"
    if not index_path.is_file():
        fail(f"missing checkpoint index: {index_path}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    indexed_shards = set(index["weight_map"].values())
    if indexed_shards != set(EXPECTED_SHARD_SIZES):
        fail(f"unexpected shard set: {sorted(indexed_shards)}")

    for name, expected_size in EXPECTED_SHARD_SIZES.items():
        path = model / name
        if not path.is_file():
            fail(f"missing checkpoint shard: {path}")
        actual_size = path.stat().st_size
        if actual_size != expected_size:
            fail(f"wrong size for {name}: expected {expected_size}, got {actual_size}")
        with safe_open(path, framework="pt") as handle:
            key_count = len(handle.keys())
        if key_count == 0:
            fail(f"no tensors found in {name}")
        print(f"[OK] {name}: bytes={actual_size}, tensors={key_count}")

    print("[OK] all asset checks passed")


if __name__ == "__main__":
    main()
