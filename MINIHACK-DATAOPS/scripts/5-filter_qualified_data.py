import os
import json
import shutil
from typing import List

# Configuration
LABELS_DIR = "datasets/bdd100k/per_image/train"
IMAGES_DIR = "datasets/bdd100k/images/10k/train"  # Update this if your images are elsewhere
OUTPUT_DIR = "datasets/qualified_datasets"

# Criteria for good quality data
def is_good_quality(label_json: dict) -> bool:
    # Check for required top-level attributes
    required_attrs = ["name", "attributes", "labels"]
    for attr in required_attrs:
        if attr not in label_json:
            return False
    # Check attributes
    attr_keys = ["weather", "timeofday", "scene"]
    if not all(k in label_json["attributes"] for k in attr_keys):
        return False
    # Check labels
    if not isinstance(label_json["labels"], list) or len(label_json["labels"]) == 0:
        return False
    return True

def find_good_quality_images(labels_dir: str) -> List[str]:
    good_images = []
    for fname in os.listdir(labels_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(labels_dir, fname)
        with open(fpath, "r") as f:
            try:
                data = json.load(f)
            except Exception:
                continue
        if is_good_quality(data):
            good_images.append(data["name"])
    return good_images

def copy_images(image_names: List[str], images_dir: str, output_dir: str):
    image_output_dir = os.path.join(output_dir, "images")
    os.makedirs(image_output_dir, exist_ok=True)
    label_output_dir = os.path.join(output_dir, "labels")
    os.makedirs(label_output_dir, exist_ok=True)
    copied_count = 0
    for img_name in image_names:
        src = os.path.join(images_dir, img_name)
        dst = os.path.join(image_output_dir, img_name)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            copied_count += 1
            print(f"Copied {src} to {dst}")
        else:
            print(f"Warning: {src} not found.")
        # Copy the corresponding JSON label file
        label_file = img_name + ".json" if not img_name.endswith(".json") else img_name
        label_src = os.path.join(LABELS_DIR, label_file if label_file.endswith(".json") else img_name + ".json")
        label_dst = os.path.join(label_output_dir, label_file if label_file.endswith(".json") else img_name + ".json")
        if os.path.exists(label_src):
            shutil.copy2(label_src, label_dst)
            print(f"Copied label {label_src} to {label_dst}")
        else:
            print(f"Warning: {label_src} not found.")
    return copied_count

def main():
    good_images = find_good_quality_images(LABELS_DIR)
    print(f"Found {len(good_images)} good quality images.")
    copied_count = copy_images(good_images, IMAGES_DIR, OUTPUT_DIR)
    print(f"Copied {copied_count} good quality images to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
