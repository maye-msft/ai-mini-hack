#!/usr/bin/env bash
# unzip_bdd100k.sh - Unzip all BDD100K zip files and organize dataset structure
#
# This script moves all zip files in the datasets/ directory to datasets/raw/,
# then extracts them into datasets/ and organizes the folder structure for use with the Streamlit app.
#
# Usage:
#   bash scripts/unzip_bdd100k.sh
#
# The script expects all zip files to be present in datasets/.

set -e

DATASET_DIR="$(dirname "$0")/../datasets"
RAW_DIR="$DATASET_DIR/raw"

mkdir -p "$RAW_DIR"

# Move all zip files to raw/
find "$DATASET_DIR" -maxdepth 1 -type f -name '*.zip' -exec mv {} "$RAW_DIR" \;

# Unzip all files in raw/
for zipfile in "$RAW_DIR"/*.zip; do
  echo "Unzipping $zipfile ..."
  unzip -n "$zipfile" -d "$DATASET_DIR"
  echo "Unzipped $zipfile."
done

echo "All zip files extracted to $DATASET_DIR."
