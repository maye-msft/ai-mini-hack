#!/usr/bin/env python3
"""
extract_per_image_labels.py - Scan datasets/bdd100k/images/10k and datasets/bdd100k/labels, group by weather/scene/timeofday, find video connections, and generate per-image JSON files.

Usage:
    python scripts/extract_per_image_labels.py [--force]

- Scans datasets/bdd100k/images/10k/*/*/*.jpg and datasets/bdd100k/labels/det_20/*.json
- Generates per-image JSON files in datasets/bdd100k/labels/det_20/per_image/<split>/
"""
import os
import json
import argparse
from pathlib import Path
from collections import defaultdict
import re

def parse_image_filename(filename):
    # Example: 0a0a0a0a-0a0a0a0a.jpg or videoName-frameIndex.jpg
    base = Path(filename).stem
    if '-' in base:
        video_name, frame_index = base.rsplit('-', 1)
        return video_name, frame_index
    return base, None

def main():
    parser = argparse.ArgumentParser(description="Scan datasets and generate per-image label JSON files, grouped by weather/scene/timeofday.")
    parser.add_argument('--force', action='store_true', help='Overwrite existing files')
    args = parser.parse_args()

    root = Path('datasets')
    images_root = root / 'bdd100k' / 'images' 
    labels_root = root / 'bdd100k' / 'labels' / 'det_20'
    per_image_root = root / 'bdd100k' / 'per_image'
    label_jsons = list(labels_root.glob('det_*.json'))

    # Load all label data
    image_label_map = {}
    meta_group = defaultdict(list)
    video_map = defaultdict(list)

    for label_json in label_jsons:
        split = label_json.stem.replace('det_', '')
        with open(label_json, 'r') as f:
            data = json.load(f)
        for frame in data:
            image_name = frame['name']
            print(f"Processing {image_name} from {label_json.name}")
            image_label_map[image_name] = frame
            # Group by weather/scene/timeofday
            attrs = frame.get('attributes', {})
            weather = attrs.get('weather', 'unknown')
            scene = attrs.get('scene', 'unknown')
            timeofday = attrs.get('timeofday', 'unknown')
            meta_group[(weather, scene, timeofday)].append(image_name)
            # Video connection
            video_name, frame_index = parse_image_filename(image_name)
            video_map[video_name].append(image_name)

    # Process images by split
    for split_dir in images_root.glob('*/*'):
        if not split_dir.is_dir():
            print(f"Skipping {split_dir} (not a directory)")
            continue
        split = split_dir.parts[-2]  # 10k or 100k
        subset = split_dir.parts[-1] # train/val/test
        out_dir = per_image_root / subset
        out_dir.mkdir(parents=True, exist_ok=True)
        for img_path in split_dir.glob('*.jpg'):
            image_name = img_path.name
            out_file = out_dir / f"{image_name}.json"
            print(f"Generating per-image label for {image_name} in {out_file}")
            if out_file.exists() and not args.force:
                print(f"Skipping {out_file} (exists, use --force to overwrite)")
                continue
            label_info = image_label_map.get(image_name, {})
            # Add grouping and video info
            video_name, frame_index = parse_image_filename(image_name)
            label_info['video_name'] = video_name
            label_info['frame_index'] = frame_index
            label_info['video_frames'] = video_map.get(video_name, [])
            with open(out_file, 'w') as out_f:
                json.dump(label_info, out_f, indent=2)

    print(f"Extracted per-image label files to {per_image_root}/<split>/, grouped and video-linked.")

if __name__ == "__main__":
    main()
