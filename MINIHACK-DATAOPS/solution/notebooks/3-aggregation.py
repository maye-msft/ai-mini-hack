# Databricks notebook source
# MAGIC %run ./config

# COMMAND ----------

# Simple Weather Count
print("Creating srv_weather_count...")
df_weather_count = spark.sql("""
    SELECT 
        weather,
        COUNT(*) as image_count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
        current_timestamp() as created_at
    FROM std_images_table
    GROUP BY weather
    ORDER BY image_count DESC
""")

df_weather_count.write \
    .format("delta") \
    .mode("overwrite") \
    .option("path", f"{gold_path}/srv_weather_count") \
    .saveAsTable("srv_weather_count")

print("✅ Weather count table created successfully!")

# COMMAND ----------

# MAGIC %sql select * from srv_weather_count

# COMMAND ----------

# Simple Object Category Count
print("Creating srv_category_count...")
df_category_count = spark.sql("""
    SELECT 
        category,
        COUNT(*) as object_count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
        current_timestamp() as created_at
    FROM std_labels_table
    GROUP BY category
    ORDER BY object_count DESC
""")

df_category_count.write \
    .format("delta") \
    .mode("overwrite") \
    .option("path", f"{gold_path}/srv_category_count") \
    .saveAsTable("srv_category_count")

print("✅ Object category count table created successfully!")

# COMMAND ----------

# MAGIC %sql select * from srv_category_count

# COMMAND ----------

# Simple Scene Count
print("Creating srv_scene_count...")
df_scene_count = spark.sql("""
    SELECT 
        scene,
        COUNT(*) as image_count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
        current_timestamp() as created_at
    FROM std_images_table
    GROUP BY scene
    ORDER BY image_count DESC
""")

df_scene_count.write \
    .format("delta") \
    .mode("overwrite") \
    .option("path", f"{gold_path}/srv_scene_count") \
    .saveAsTable("srv_scene_count")

print("✅ Scene count table created successfully!")

# COMMAND ----------

# MAGIC %sql select * from srv_scene_count

# COMMAND ----------

# MAGIC %md
# MAGIC # BDD100K Gold Layer Aggregation Notebook
# MAGIC
# MAGIC This notebook creates gold layer aggregated tables from silver layer data,
# MAGIC providing analytical views for the BDD100K dataset.
# MAGIC
# MAGIC **Input:** Silver layer parquet files (silver_images, silver_labels)  
# MAGIC **Output:** Gold layer aggregated tables (image_stats, category_analytics, video_summary)

# COMMAND ----------

# MAGIC %run ./utils

# COMMAND ----------

# MAGIC %run ./service_principal_config

# COMMAND ----------

# Import required libraries
from pyspark.sql.functions import *
from pyspark.sql.types import *

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Layer Aggregation Functions

# COMMAND ----------

def create_gold_image_stats(df_images):
    """Create gold layer image statistics aggregated by weather, time, and scene."""
    return df_images.groupBy("weather", "timeofday", "scene") \
        .agg(
            count("image_id").alias("total_images"),
            avg("total_labels").alias("avg_labels_per_image"),
            max("total_labels").alias("max_labels_per_image"),
            min("total_labels").alias("min_labels_per_image"),
            countDistinct("video_name").alias("unique_videos")
        ) \
        .withColumn("processing_date", current_timestamp()) \
        .orderBy("weather", "timeofday", "scene")

# COMMAND ----------

def create_gold_category_analytics(df_labels):
    """Create gold layer category analytics with object detection metrics."""
    return df_labels.groupBy("category") \
        .agg(
            count("label_id").alias("total_objects"),
            countDistinct("image_id").alias("images_with_category"),
            avg("bbox_area").alias("avg_bbox_area"),
            avg("bbox_width").alias("avg_bbox_width"),
            avg("bbox_height").alias("avg_bbox_height"),
            sum(when(col("is_occluded") == True, 1).otherwise(0)).alias("occluded_count"),
            sum(when(col("is_truncated") == True, 1).otherwise(0)).alias("truncated_count"),
            (sum(when(col("is_occluded") == True, 1).otherwise(0)) * 100.0 / count("label_id")).alias("occlusion_percentage"),
            (sum(when(col("is_truncated") == True, 1).otherwise(0)) * 100.0 / count("label_id")).alias("truncation_percentage")
        ) \
        .withColumn("processing_date", current_timestamp()) \
        .orderBy(desc("total_objects"))

# COMMAND ----------

def create_gold_video_summary(df_images, df_labels):
    """Create gold layer video summary with frame and object statistics."""
    # First aggregate labels by image
    labels_per_image = df_labels.groupBy("image_id") \
        .agg(
            count("label_id").alias("labels_count"),
            countDistinct("category").alias("unique_categories"),
            avg("bbox_area").alias("avg_area_per_image")
        )
    
    # Join with images and aggregate by video
    return df_images.join(labels_per_image, "image_id", "left") \
        .fillna(0, ["labels_count", "unique_categories", "avg_area_per_image"]) \
        .groupBy("video_name") \
        .agg(
            count("image_id").alias("total_frames"),
            sum("labels_count").alias("total_objects_in_video"),
            avg("labels_count").alias("avg_objects_per_frame"),
            max("unique_categories").alias("max_categories_per_frame"),
            avg("avg_area_per_image").alias("avg_bbox_area_per_video"),
            first("weather").alias("video_weather"),
            first("timeofday").alias("video_timeofday"),
            first("scene").alias("video_scene")
        ) \
        .withColumn("processing_date", current_timestamp()) \
        .orderBy(desc("total_objects_in_video"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary and Quality Check Functions

# COMMAND ----------

def display_summary_statistics(gold_image_stats, gold_category_analytics, gold_video_summary):
    """Display summary statistics for all gold tables."""
    print("\n=== GOLD LAYER SUMMARY ===")
    
    print(f"\n1. GOLD IMAGE STATS:")
    print(f"   Total weather/time/scene combinations: {gold_image_stats.count()}")
    gold_image_stats.show(10, truncate=False)
    
    print(f"\n2. GOLD CATEGORY ANALYTICS:")
    print(f"   Total object categories: {gold_category_analytics.count()}")
    gold_category_analytics.show(10, truncate=False)
    
    print(f"\n3. GOLD VIDEO SUMMARY:")
    print(f"   Total videos processed: {gold_video_summary.count()}")
    gold_video_summary.show(10, truncate=False)

# COMMAND ----------

def display_data_quality_checks(df_images, df_labels, gold_image_stats, gold_category_analytics, gold_video_summary):
    """Display data quality checks and top statistics."""
    print("\n=== DATA QUALITY CHECKS ===")
    print(f"Silver images count: {df_images.count()}")
    print(f"Silver labels count: {df_labels.count()}")
    print(f"Gold image stats records: {gold_image_stats.count()}")
    print(f"Gold category analytics records: {gold_category_analytics.count()}")
    print(f"Gold video summary records: {gold_video_summary.count()}")
    
    print("\n=== TOP STATISTICS ===")
    print("Most common weather condition:")
    gold_image_stats.groupBy("weather").sum("total_images").orderBy(desc("sum(total_images)")).show(3)
    
    print("Most frequent object category:")
    gold_category_analytics.select("category", "total_objects").orderBy(desc("total_objects")).show(5)
    
    print("Videos with most objects:")
    gold_video_summary.select("video_name", "total_objects_in_video").orderBy(desc("total_objects_in_video")).show(5)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Initialize Environment and Paths

# COMMAND ----------

# Get environment info and paths
env_info = get_environment_info()
paths = get_data_paths()

silver_path = paths["silver_path"]
gold_path = paths["gold_path"]

print("BDD100K Gold Layer Aggregation Script - Refactored Version")
print("=" * 60)
print(f"Environment: {env_info['filesystem_type']}")
print(f"Silver layer path: {silver_path}")
print(f"Gold layer path: {gold_path}")
print()

# Create output directory
create_directory(gold_path)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Initialize Spark Session

# COMMAND ----------

# Initialize Spark session
spark = setup_spark_session("BDD100K_Gold_Layer_Aggregation")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Silver Layer Data

# COMMAND ----------

print("Loading silver layer data...")

# Read silver layer tables
df_images = spark.read.parquet(f"{silver_path}/images")
df_labels = spark.read.parquet(f"{silver_path}/labels")

print(f"Loaded {df_images.count()} images and {df_labels.count()} labels")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Gold Layer Tables

# COMMAND ----------

print("Creating gold layer aggregated tables...")

# Gold Table 1: Image Statistics by Weather and Time of Day
print("Creating image_stats table...")
gold_image_stats = create_gold_image_stats(df_images)

# COMMAND ----------

# Write Gold Table 1
gold_image_stats.write \
    .format("parquet") \
    .mode("overwrite") \
    .save(f"{gold_path}/image_stats")

print("✓ Image stats table saved")

# COMMAND ----------

# Gold Table 2: Object Category Analytics
print("Creating category_analytics table...")
gold_category_analytics = create_gold_category_analytics(df_labels)

# COMMAND ----------

# Write Gold Table 2
gold_category_analytics.write \
    .format("parquet") \
    .mode("overwrite") \
    .save(f"{gold_path}/category_analytics")

print("✓ Category analytics table saved")

# COMMAND ----------

# Gold Table 3: Video-Level Summary
print("Creating video_summary table...")
gold_video_summary = create_gold_video_summary(df_images, df_labels)

# COMMAND ----------

# Write Gold Table 3
gold_video_summary.write \
    .format("parquet") \
    .mode("overwrite") \
    .save(f"{gold_path}/video_summary")

print("✓ Video summary table saved")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display Results and Quality Checks

# COMMAND ----------

# Display Results
display_summary_statistics(gold_image_stats, gold_category_analytics, gold_video_summary)
display_data_quality_checks(df_images, df_labels, gold_image_stats, gold_category_analytics, gold_video_summary)

# COMMAND ----------

print(f"\n=== GOLD LAYER TABLES SAVED ===")
print(f"Image stats: {gold_path}/image_stats")
print(f"Category analytics: {gold_path}/category_analytics")
print(f"Video summary: {gold_path}/video_summary")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Aggregation Complete
# MAGIC
# MAGIC The gold layer aggregation is complete. The Spark session remains active for continued use.