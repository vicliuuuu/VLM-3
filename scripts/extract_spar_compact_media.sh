#!/usr/bin/env bash
set -euo pipefail

# Compatibility helper for inspecting the released SPAR package.
#
# Usage:
#   bash scripts/extract_spar_compact_media.sh /data/geosr_static
#   bash scripts/extract_spar_compact_media.sh /data/geosr_static /path/to/archive.tar.gz
#
# The script extracts only when the archive actually contains image files. It
# refuses unsafe archive members and avoids presenting annotation-only archives
# as RGB media.

DATA_ROOT="${1:-$PWD/data}"
ARCHIVE="${2:-$DATA_ROOT/GeoSR-static/train/spar_7m.tar.gz}"
MEDIA_ROOT="$DATA_ROOT/media"
MEMBERS_FILE="$(mktemp)"
trap 'rm -f "$MEMBERS_FILE"' EXIT

if [[ ! -f "$ARCHIVE" ]]; then
  echo "Missing archive: $ARCHIVE"
  exit 1
fi

tar -tzf "$ARCHIVE" > "$MEMBERS_FILE"

if awk '
  /^\// { bad=1 }
  {
    n=split($0, parts, "/")
    for (i=1; i<=n; i++) {
      if (parts[i] == "..") bad=1
    }
  }
  END { exit bad ? 0 : 1 }
' "$MEMBERS_FILE"; then
  echo "Refusing to extract archive with absolute or parent-traversal members."
  exit 1
fi

IMAGE_COUNT="$(awk '
  BEGIN { IGNORECASE=1; count=0 }
  /\.(jpg|jpeg|png|webp|bmp)$/ { count++ }
  END { print count }
' "$MEMBERS_FILE")"

echo "Archive: $ARCHIVE"
echo "Members: $(wc -l < "$MEMBERS_FILE")"
echo "Image members: $IMAGE_COUNT"
echo "First members:"
sed -n '1,20p' "$MEMBERS_FILE"

if [[ "$IMAGE_COUNT" -eq 0 ]]; then
  cat <<'EOF'

No image files were found, so this archive is not being extracted as media.
Prepare RGB inputs from the licensed upstream datasets using SPAR's official
layout scripts, then place them under <DATA_ROOT>/media.
EOF
  exit 2
fi

mkdir -p "$MEDIA_ROOT"
tar -xzf "$ARCHIVE" -C "$MEDIA_ROOT"
echo "Extracted image-containing package to: $MEDIA_ROOT"
