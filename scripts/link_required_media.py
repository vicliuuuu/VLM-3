#!/usr/bin/env python3
"""Create symlinks or copies for required media paths.

The script preserves relative paths from the media list. If a list entry is
`spar/scannet/.../0001.jpg`, then the target will be:

  <target-root>/spar/scannet/.../0001.jpg

Examples:
  python scripts/link_required_media.py \
    --media-list /data/geosr_static/GeoSR-static/train/spar_50k_media.txt \
    --source-root /data/geosr_static/media_source \
    --target-root /path/to/GeoSR/data/media \
    --mode symlink
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


def link_or_copy(src: Path, dst: Path, mode: str, overwrite: bool) -> None:
    if dst.exists() or dst.is_symlink():
        if not overwrite:
            return
        if dst.is_dir() and not dst.is_symlink():
            raise IsADirectoryError(f"Refusing to overwrite directory: {dst}")
        dst.unlink()

    dst.parent.mkdir(parents=True, exist_ok=True)
    if mode == "symlink":
        os.symlink(src, dst)
    elif mode == "hardlink":
        os.link(src, dst)
    elif mode == "copy":
        shutil.copy2(src, dst)
    else:
        raise ValueError(f"Unknown mode: {mode}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--media-list", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--target-root", required=True, type=Path)
    parser.add_argument("--mode", choices=["symlink", "hardlink", "copy"], default="symlink")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--missing-output", type=Path)
    args = parser.parse_args()

    with args.media_list.open("r", encoding="utf-8") as f:
        rel_paths = [line.strip() for line in f if line.strip()]

    linked = 0
    skipped_existing = 0
    missing: list[str] = []

    for rel in rel_paths:
        src = args.source_root / rel
        dst = args.target_root / rel
        if not src.exists():
            missing.append(rel)
            continue
        if dst.exists() or dst.is_symlink():
            if not args.overwrite:
                skipped_existing += 1
                continue
        if not args.dry_run:
            link_or_copy(src, dst, args.mode, args.overwrite)
        linked += 1

    print(f"Source root: {args.source_root}")
    print(f"Target root: {args.target_root}")
    print(f"Mode: {args.mode}")
    print(f"Requested paths: {len(rel_paths)}")
    print(f"Created: {linked}")
    print(f"Skipped existing: {skipped_existing}")
    print(f"Missing from source: {len(missing)}")

    if missing:
        print("\nMissing examples:")
        for rel in missing[:20]:
            print(f"  {rel}")

    if args.missing_output:
        args.missing_output.parent.mkdir(parents=True, exist_ok=True)
        with args.missing_output.open("w", encoding="utf-8") as f:
            for rel in missing:
                f.write(rel + "\n")
        print(f"\nSaved missing list: {args.missing_output}")


if __name__ == "__main__":
    main()
