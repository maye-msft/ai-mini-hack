#!/bin/bash

# Simple script to zip BDD100K images
CURRENT_DIR=$(pwd)
IMAGES_SOURCE_DIR="$CURRENT_DIR/data/images"
LABELS_SOURCE_DIR="$CURRENT_DIR/data/labels"
IMAGES_OUTPUT_ZIP="$CURRENT_DIR/data/images.zip"
LABELS_OUTPUT_ZIP="$CURRENT_DIR/data/labels.zip"


mkdir -p data

echo "Zipping images from $IMAGES_SOURCE_DIR..."

# Check if directory exists
if [ ! -d "$IMAGES_SOURCE_DIR" ]; then
    echo "Error: Directory $IMAGES_SOURCE_DIR not found!"
    exit 1
fi

# Create zip file
cd "$IMAGES_SOURCE_DIR" 
zip -j -9 -s 50m "$IMAGES_OUTPUT_ZIP" *.*


echo "Done! Created $IMAGES_OUTPUT_ZIP"

echo "Zipping labels from $LABELS_SOURCE_DIR..."

# Check if directory exists
if [ ! -d "$LABELS_SOURCE_DIR" ]; then
    echo "Error: Directory $LABELS_SOURCE_DIR not found!"
    exit 1
fi

# Create zip file
cd "$LABELS_SOURCE_DIR" 
zip -j -9 -s 50m "$LABELS_OUTPUT_ZIP" *

echo "Done! Created $LABELS_OUTPUT_ZIP"