#!/usr/bin/env bash
set -euo pipefail

PIPELINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_DIR="$PIPELINE_DIR/raw"

echo "==> Downloading Baseball Databank..."
if [ -d "$RAW_DIR/baseballdatabank" ]; then
  echo "    Already exists, pulling latest..."
  git -C "$RAW_DIR/baseballdatabank" pull --ff-only
else
  git clone --depth 1 https://github.com/cbwinslow/baseballdatabank.git "$RAW_DIR/baseballdatabank"
fi

echo "==> Downloading GeoNames cities1000..."
GEONAMES_DIR="$RAW_DIR/geonames"
mkdir -p "$GEONAMES_DIR"
if [ -f "$GEONAMES_DIR/cities1000.txt" ]; then
  echo "    Already exists, skipping."
else
  curl -L "https://download.geonames.org/export/dump/cities1000.zip" -o "$GEONAMES_DIR/cities1000.zip"
  unzip -o "$GEONAMES_DIR/cities1000.zip" -d "$GEONAMES_DIR"
  rm "$GEONAMES_DIR/cities1000.zip"
fi

echo "==> Downloading GeoNames countryInfo..."
if [ -f "$GEONAMES_DIR/countryInfo.txt" ]; then
  echo "    Already exists, skipping."
else
  curl -L "https://download.geonames.org/export/dump/countryInfo.txt" -o "$GEONAMES_DIR/countryInfo.txt"
fi

echo "==> Done. Raw data available at: $RAW_DIR"
