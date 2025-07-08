#!/usr/bin/env bash
# download_bdd100k.sh - Download BDD100K 10k images datasets
#
# This script downloads the following files from https://dl.cv.ethz.ch/bdd100k/data/:
#   - 10k_images_train.zip (746MB)
#   - 10k_images_val.zip (143MB)
#   - 10k_images_test.zip (164MB)
#
# Usage:
#   bash scripts/download_bdd100k.sh
#
# Downloads are resumable. Files are saved to the datasets/ directory.

set -e

DATASET_DIR="$(dirname "$0")/../datasets/raw"
BASE_URL="https://dl.cv.ethz.ch/bdd100k/data"
FILES=(
  "10k_images_train.zip"
  "10k_images_val.zip"
  # "10k_images_test.zip"
)

mkdir -p "$DATASET_DIR"

for file in "${FILES[@]}"; do
  url="$BASE_URL/$file"
  dest="$DATASET_DIR/$file"
  echo "Downloading $file to $dest ..."
  # Use wget with -c for resumable downloads
  wget -c "$url" -O "$dest"
  echo "Downloaded $file."
done

echo "All files downloaded to $DATASET_DIR."
