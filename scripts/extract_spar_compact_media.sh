#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/extract_spar_compact_media.sh /data/geosr_static
#
# This extracts SPAR-7M compact media packages into:
#   <DATA_ROOT>/media
#
# The expected result should contain paths like:
#   <DATA_ROOT>/media/spar/scannet/...

DATA_ROOT="${1:-$PWD/data}"
SPAR_DIR="$DATA_ROOT/SPAR-7M"
MEDIA_ROOT="$DATA_ROOT/media"

mkdir -p "$MEDIA_ROOT"

for name in rxr scannet scannetpp structured3d; do
  archive="$SPAR_DIR/${name}.tar.gz"
  if [[ ! -f "$archive" ]]; then
    echo "Missing archive: $archive"
    exit 1
  fi
  echo "Extracting $archive -> $MEDIA_ROOT"
  tar -xzf "$archive" -C "$MEDIA_ROOT"
done

echo "Done. Media root: $MEDIA_ROOT"
