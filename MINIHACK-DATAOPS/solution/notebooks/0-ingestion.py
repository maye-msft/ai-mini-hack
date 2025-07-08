# Databricks notebook source
# MAGIC %run ./config

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.dbutils import DBUtils
spark = SparkSession.builder.getOrCreate()
dbutils = DBUtils(spark)
ingest_datasets_path = '/tmp/bdd100k'
dbutils.fs.ls(ingest_datasets_path)

# COMMAND ----------

# MAGIC %sh
# MAGIC rm -rf /tmp/bdd100k
# MAGIC mkdir -p /tmp/bdd100k

# COMMAND ----------

dbutils.fs.cp('/tmp/bdd100k/images.zip', "file:/tmp/bdd100k")
dbutils.fs.cp('/tmp/bdd100k/labels.zip', "file:/tmp/bdd100k")

# COMMAND ----------

# MAGIC %sh
# MAGIC ls /tmp/bdd100k
# MAGIC mkdir -p /tmp/bdd100k/extracted
# MAGIC unzip -o /tmp/bdd100k/images.zip -d /tmp/bdd100k/extracted
# MAGIC unzip -o /tmp/bdd100k/labels.zip -d /tmp/bdd100k/extracted
# MAGIC ls -l /tmp/bdd100k/extracted

# COMMAND ----------

# MAGIC %sh
# MAGIC rm -rf /tmp/bdd100k/extracted/__MACOSX/train/
# MAGIC ls -1 /tmp/bdd100k/extracted/train | wc -l

# COMMAND ----------

dbutils.fs.ls(bronze_path)

# COMMAND ----------

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def copy_single_file(source_file, dest_file):
    """Copy a single file from local to ABFS"""
    try:
        start_time = time.time()
        
        # Use dbutils.fs.cp for individual file copy
        dbutils.fs.cp(source_file, dest_file, recurse=False)
        
        elapsed = time.time() - start_time
        
        # Get file size for better reporting
        try:
            file_info = dbutils.fs.ls(source_file)[0]
            size_mb = file_info.size / (1024 * 1024)
            return f"✓ Copied: {os.path.basename(source_file)} ({size_mb:.1f}MB) in {elapsed:.1f}s"
        except:
            return f"✓ Copied: {os.path.basename(source_file)} in {elapsed:.1f}s"
            
    except Exception as e:
        return f"✗ Failed: {os.path.basename(source_file)} | Error: {str(e)}"

def get_all_files(source_dir):
    """Get all files recursively from source directory"""
    files_to_copy = []
    
    # Use dbutils.fs.ls to get directory contents
    def scan_directory(dir_path):
        try:
            items = dbutils.fs.ls(dir_path)
            for item in items:
                if item.isDir():
                    # Recursively scan subdirectories
                    scan_directory(item.path)
                else:
                    # Add file to copy list
                    files_to_copy.append(item.path)
        except Exception as e:
            print(f"Error scanning {dir_path}: {e}")
    
    scan_directory(source_dir)
    return files_to_copy

def copy_files_parallel(source_base, dest_base, max_workers=10):
    """Copy files from source to destination using thread pool"""
    
    print(f"Starting parallel copy from {source_base} to {dest_base}")
    print(f"Using {max_workers} workers")
    
    # Get all files to copy
    print("Scanning source directory...")
    source_files = get_all_files(source_base)
    total_files = len(source_files)
    
    if total_files == 0:
        print("No files found to copy")
        return
    
    print(f"Found {total_files} files to copy")
    
    # Create destination directory structure first
    print("Creating destination directory structure...")
    dest_dirs = set()
    for source_file in source_files:
        relative_path = source_file.replace(source_base, "").lstrip("/")
        dest_file = f"{dest_base.rstrip('/')}/{relative_path}"
        dest_dir = "/".join(dest_file.split("/")[:-1])
        dest_dirs.add(dest_dir)
    
    # Create all directories upfront
    for dest_dir in dest_dirs:
        try:
            dbutils.fs.mkdirs(dest_dir)
        except:
            pass  # Directory might already exist
    
    # Prepare file pairs for copying
    copy_tasks = []
    for source_file in source_files:
        relative_path = source_file.replace(source_base, "").lstrip("/")
        dest_file = f"{dest_base.rstrip('/')}/{relative_path}"
        copy_tasks.append((source_file, dest_file))
    
    # Execute copies in parallel
    start_time = time.time()
    completed = 0
    failed = 0
    
    print(f"Starting parallel copy with {max_workers} workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(copy_single_file, source, dest): (source, dest)
            for source, dest in copy_tasks
        }
        
        # Process completed tasks
        for future in as_completed(future_to_task):
            result = future.result()
            print(result)
            
            if result.startswith("✓"):
                completed += 1
            else:
                failed += 1
            
            # Progress update every 5 files
            if (completed + failed) % 5 == 0:
                progress = (completed + failed) / total_files * 100
                elapsed = time.time() - start_time
                rate = (completed + failed) / elapsed if elapsed > 0 else 0
                print(f"Progress: {completed + failed}/{total_files} ({progress:.1f}%) - {rate:.1f} files/sec")
    
    # Summary
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n=== Copy Summary ===")
    print(f"Total files: {total_files}")
    print(f"Completed: {completed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {completed/total_files*100:.1f}%")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average rate: {total_files/total_time:.2f} files/second")
    
    if failed > 0:
        print(f"\n⚠️  {failed} files failed to copy. Check the error messages above.")
    
    return completed, failed

# COMMAND ----------

# Define your paths
source_path = "file:/tmp/bdd100k/extracted/train"

# You can also adjust the number of workers based on your cluster resources
# More workers = faster copy but more resource usage
num_workers = 15

# Start the parallel copy
completed, failed = copy_files_parallel(source_path, bronze_path+'/train', max_workers=num_workers)

if failed == 0:
    print("🎉 All files copied successfully!")
else:
    print(f"⚠️  Copy completed with {failed} failures out of {completed + failed} total files")

# COMMAND ----------

len(dbutils.fs.ls(f'{bronze_path}/train'))

# COMMAND ----------

