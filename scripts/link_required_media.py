#!/usr/bin/env python3
"""Link or copy a validated list of relative media paths."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path, PurePosixPath


def normalize_relative_path(raw: str) -> Path:
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe media path: {raw!r}")
    if str(path) in ("", "."):
        raise ValueError(f"Empty media path: {raw!r}")
    return Path(*path.parts)


def link_or_copy(src: Path, dst: Path, mode: str, overwrite: bool) -> None:
    if dst.exists() or dst.is_symlink():
        if not overwrite:
            return
        if dst.is_dir() and not dst.is_symlink():
            raise IsADirectoryError(f"Refusing to overwrite directory: {dst}")
        dst.unlink()

    dst.parent.mkdir(parents=True, exist_ok=True)
    if mode == "symlink":
        os.symlink(src.resolve(), dst)
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
    parser.add_argument("--mode", choices=("symlink", "hardlink", "copy"), default="symlink")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--missing-output", type=Path)
    args = parser.parse_args()

    with args.media_list.open("r", encoding="utf-8") as stream:
        rel_paths = [
            normalize_relative_path(line.strip())
            for line in stream
            if line.strip()
        ]

    source_root = args.source_root.resolve()
    target_root = args.target_root.resolve()
    linked = 0
    skipped_existing = 0
    missing: list[str] = []

    for rel_path in rel_paths:
        src = source_root / rel_path
        dst = target_root / rel_path
        if not src.is_file():
            missing.append(rel_path.as_posix())
            continue
        if dst.exists() or dst.is_symlink():
            if not args.overwrite:
                skipped_existing += 1
                continue
        if not args.dry_run:
            link_or_copy(src, dst, args.mode, args.overwrite)
        linked += 1

    print(f"Source root: {source_root}")
    print(f"Target root: {target_root}")
    print(f"Mode: {args.mode}")
    print(f"Requested paths: {len(rel_paths)}")
    print(f"Created: {linked}")
    print(f"Skipped existing: {skipped_existing}")
    print(f"Missing from source: {len(missing)}")

    if missing:
        print("\nMissing examples:")
        for path in missing[:20]:
            print(f"  {path}")

    if args.missing_output:
        args.missing_output.parent.mkdir(parents=True, exist_ok=True)
        with args.missing_output.open("w", encoding="utf-8") as stream:
            for path in missing:
                stream.write(path + "\n")
        print(f"\nSaved missing list: {args.missing_output}")


if __name__ == "__main__":
    main()
