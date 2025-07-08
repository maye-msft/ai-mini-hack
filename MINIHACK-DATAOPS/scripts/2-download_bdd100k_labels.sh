#!/usr/bin/env bash
# download_bdd100k_labels.sh - Download BDD100K label files
#
# This script downloads the following files from https://dl.cv.ethz.ch/bdd100k/data/:
#   - bdd100k_det_20_labels_trainval.zip (53M)
#   - bdd100k_drivable_labels_trainval.zip (490M)
#   - bdd100k_ins_seg_labels_trainval.zip (106M)
#   - bdd100k_lane_labels_trainval.zip (435M)
#   - bdd100k_pan_seg_labels_trainval.zip (362M)
#   - bdd100k_pose_labels_trainval.zip (16M)
#   - bdd100k_sem_seg_labels_trainval.zip (399M)
#   - LICENSE.txt (1.6K)
#
# Usage:
#   bash scripts/download_bdd100k_labels.sh
#
# Downloads are resumable. Files are saved to the datasets/ directory.

set -e

DATASET_DIR="$(dirname "$0")/../datasets/raw"
BASE_URL="https://dl.cv.ethz.ch/bdd100k/data"
FILES=(
  "bdd100k_det_20_labels_trainval.zip"
  # "bdd100k_drivable_labels_trainval.zip"
  # "bdd100k_ins_seg_labels_trainval.zip"
  # "bdd100k_lane_labels_trainval.zip"
  # "bdd100k_pan_seg_labels_trainval.zip"
  # "bdd100k_pose_labels_trainval.zip"
  # "bdd100k_sem_seg_labels_trainval.zip"
  "LICENSE.txt"
)

mkdir -p "$DATASET_DIR"

for file in "${FILES[@]}"; do
  url="$BASE_URL/$file"
  dest="$DATASET_DIR/$file"
  echo "Downloading $file to $dest ..."
  wget -c "$url" -O "$dest"
  echo "Downloaded $file."
done

echo "All label files downloaded to $DATASET_DIR."
