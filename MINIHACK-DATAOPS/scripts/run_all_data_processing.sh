#!/usr/bin/env bash
# run_all_data_processing.sh - Complete BDD100K data processing pipeline
#
# This script runs the complete data processing pipeline:
#   1. Download BDD100K images (train and val)
#   2. Download BDD100K labels 
#   3. Unzip all downloaded files
#   4. Extract per-image labels
#   5. Filter qualified datasets
#
# Usage:
#   bash scripts/run_all_data_processing.sh
#
# This will set up the complete dataset structure needed for the Streamlit app.

set -e

SCRIPT_DIR="$(dirname "$0")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== BDD100K Data Processing Pipeline ==="
echo "Starting complete data processing..."
echo

# Step 1: Download BDD100K images
echo "Step 1: Downloading BDD100K images..."
if [ -f "$PROJECT_ROOT/datasets/raw/10k_images_train.zip" ] && [ -f "$PROJECT_ROOT/datasets/raw/10k_images_val.zip" ]; then
    echo "✓ Images already exist, skipping download"
else
    bash "$SCRIPT_DIR/1-download_bdd100k.sh"
    echo "✓ Images downloaded"
fi
echo

# Step 2: Download BDD100K labels
echo "Step 2: Downloading BDD100K labels..."
if [ -f "$PROJECT_ROOT/datasets/raw/bdd100k_det_20_labels_trainval.zip" ]; then
    echo "✓ Labels already exist, skipping download"
else
    bash "$SCRIPT_DIR/2-download_bdd100k_labels.sh"
    echo "✓ Labels downloaded"
fi
echo

# Step 3: Unzip all files
echo "Step 3: Extracting all zip files..."
if [ -d "$PROJECT_ROOT/datasets/bdd100k/images/10k/train" ] && [ -d "$PROJECT_ROOT/datasets/bdd100k/labels/det_20" ]; then
    echo "✓ Files already extracted, skipping extraction"
else
    bash "$SCRIPT_DIR/3-unzip_bdd100k.sh"
    echo "✓ Files extracted"
fi
echo

# Step 4: Extract per-image labels
echo "Step 4: Extracting per-image labels..."
if [ -d "$PROJECT_ROOT/datasets/bdd100k/per_image/train" ] && [ "$(ls -A "$PROJECT_ROOT/datasets/bdd100k/per_image/train" 2>/dev/null)" ]; then
    echo "✓ Per-image labels already exist, skipping extraction"
else
    cd "$PROJECT_ROOT"
    python scripts/4-extract_per_image_labels.py --force
    echo "✓ Per-image labels extracted"
fi
echo

# Step 5: Filter qualified datasets
echo "Step 5: Filtering qualified datasets..."
if [ -d "$PROJECT_ROOT/datasets/qualified_datasets/images" ] && [ "$(ls -A "$PROJECT_ROOT/datasets/qualified_datasets/images" 2>/dev/null)" ]; then
    echo "✓ Qualified datasets already exist, skipping filtering"
else
    python scripts/5-filter_qualified_data.py
    echo "✓ Qualified datasets filtered"
fi
echo

echo "=== Data Processing Complete ==="
echo "✓ All data processing steps completed successfully!"
echo "✓ Qualified datasets are available in: datasets/qualified_datasets/"
echo "✓ You can now run the Streamlit app: streamlit run apps/data_explorer_app.py"
echo
