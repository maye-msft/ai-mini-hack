# Databricks notebook source
# MAGIC %run ./config

# COMMAND ----------

# Import required libraries
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import threading
from collections import defaultdict

# COMMAND ----------

# Get environment info and paths
from pyspark.sql import SparkSession
from pyspark.dbutils import DBUtils
spark = SparkSession.builder.getOrCreate()
dbutils = DBUtils(spark)

input_dir = f'{bronze_path}/train'
qualified_dir = f'{bronze_path}/qualified'
unqualified_dir = f'{bronze_path}/unqualified'

dbutils.fs.rm(qualified_dir, True)
dbutils.fs.rm(unqualified_dir, True)
dbutils.fs.mkdirs(qualified_dir)
dbutils.fs.mkdirs(unqualified_dir)

# COMMAND ----------

import json
from concurrent.futures import ThreadPoolExecutor

def validate_and_move_file(file_info, required_fields, qualified_dir, unqualified_dir):
    """Validate JSON file and move to appropriate directory"""
    file_path = file_info.path
    file_name = file_info.name
    
    try:
        # Read and validate JSON
        content = dbutils.fs.head(file_path, max_bytes=10000000)  # 10MB limit
        data = json.loads(content)
        
        # Handle both single object and array
        record_dict = data[0] if isinstance(data, list) and data else data
        
        # Validation logic
        errors = []
        
        # Check required top-level fields
        for field in required_fields:
            if field not in record_dict:
                errors.append(f"Missing required field: {field}")
        
        # Validate attributes structure
        if "attributes" in record_dict:
            attributes = record_dict["attributes"]
            if not isinstance(attributes, dict):
                errors.append("Field 'attributes' must be an object")
            else:
                required_attrs = ["weather", "timeofday", "scene"]
                for attr in required_attrs:
                    if attr not in attributes:
                        errors.append(f"Missing required attribute: {attr}")
        
        # Validate labels structure
        if "labels" in record_dict:
            labels = record_dict["labels"]
            if not isinstance(labels, list):
                errors.append("Field 'labels' must be an array")
            else:
                # Check each label object structure (limit check for performance)
                for i, label in enumerate(labels[:10]):  # Limit for performance
                    if not isinstance(label, dict):
                        errors.append(f"Label {i} must be an object")
                        continue
                    
                    # Required label fields
                    required_label_fields = ["id", "category", "box2d", "attributes"]
                    for field in required_label_fields:
                        if field not in label:
                            errors.append(f"Label {i} missing required field: {field}")
                    
                    # Validate box2d structure
                    if "box2d" in label and isinstance(label["box2d"], dict):
                        required_box_fields = ["x1", "y1", "x2", "y2"]
                        for field in required_box_fields:
                            if field not in label["box2d"]:
                                errors.append(f"Label {i} box2d missing field: {field}")
        
        is_valid = len(errors) == 0
        error_string = "; ".join(errors) if errors else ""
        
        # Move to appropriate directory
        dest_dir = qualified_dir if is_valid else unqualified_dir
        dbutils.fs.mkdirs(dest_dir)
        dbutils.fs.cp(file_path, f"{dest_dir}/{file_name}")
        
        status = "✅ QUALIFIED" if is_valid else f"❌ {error_string}"
        print(f"{file_name} -> {status}")
        
        return is_valid
        
    except Exception as e:
        # Move invalid files to unqualified
        dbutils.fs.mkdirs(unqualified_dir)
        dbutils.fs.cp(file_path, f"{unqualified_dir}/{file_name}")
        print(f"{file_name} -> ❌ ERROR: {str(e)}")
        return False

def process_json_files(input_dir, qualified_dir, unqualified_dir, required_fields, max_workers=20):
    """Process all JSON files in parallel"""
    
    # Get JSON files
    json_files = [f for f in dbutils.fs.ls(input_dir) if f.name.endswith('.json')]
    print(f"Found {len(json_files)} JSON files")
    
    if not json_files:
        return
    
    # Process in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(
            lambda f: validate_and_move_file(f, required_fields, qualified_dir, unqualified_dir),
            json_files
        ))
    
    # Summary
    qualified = sum(results)
    unqualified = len(results) - qualified
    print(f"\nSummary: {qualified} qualified, {unqualified} unqualified")


required_fields = ["video_name", "frame_index", "attributes", "labels"]

input_dir = f'{bronze_path}/train'
qualified_dir = f'{bronze_path}/qualified'
unqualified_dir = f'{bronze_path}/unqualified'

process_json_files(input_dir, qualified_dir, unqualified_dir, required_fields)

# COMMAND ----------

len(dbutils.fs.ls(qualified_dir))

# COMMAND ----------

len(dbutils.fs.ls(unqualified_dir))

# COMMAND ----------

