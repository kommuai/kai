#!/usr/bin/env bash
# Regenerate favicons from public/brand/shadou-logo.png (transparent, trimmed master).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRAND="$ROOT/public/brand"
MASTER="$BRAND/shadou-logo.png"

if [[ ! -f "$MASTER" ]]; then
  echo "Missing $MASTER"
  exit 1
fi

convert "$MASTER" -fuzz 10% -transparent white -trim +repage "$MASTER"
cp "$MASTER" "$ROOT/src/assets/shadou-logo.png"

cd "$ROOT/public"
for size in 16 32 180 192 512; do
  case $size in
    16) out=favicon-16x16.png ;;
    32) out=favicon-32x32.png ;;
    180) out=apple-touch-icon.png ;;
    192) out=brand/android-chrome-192x192.png ;;
    512) out=brand/android-chrome-512x512.png ;;
  esac
  convert "$MASTER" -resize ${size}x${size} -background none -gravity center -extent ${size}x${size} "$out"
done
convert favicon-16x16.png favicon-32x32.png favicon.ico
identify "$MASTER"
echo "Brand icons refreshed."
