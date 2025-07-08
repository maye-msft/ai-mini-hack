# Databricks notebook source
# MAGIC %run ./config

# COMMAND ----------

# Import required libraries
from pyspark.sql.functions import *
from pyspark.sql.types import *

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Transformation Functions

# COMMAND ----------

def create_images_dataframe(df_raw):
    """Transform raw data into images dataframe."""
    # Check available columns to determine filename source
    columns = df_raw.columns
    
    # Create filename based on available fields
    if "name" in columns:
        filename_expr = col("name")
    elif "image_filename" in columns:
        filename_expr = col("image_filename")
    else:
        # Generate filename from video_name and frame_index
        filename_expr = concat(col("video_name"), lit("-"), col("frame_index"), lit(".jpg"))
    
    # Handle different attribute structures
    if "metadata" in columns:
        # Processed format with metadata structure
        weather_expr = col("metadata.weather")
        timeofday_expr = col("metadata.timeofday")
        scene_expr = col("metadata.scene")
    else:
        # Original format with attributes structure
        weather_expr = col("attributes.weather")
        timeofday_expr = col("attributes.timeofday")
        scene_expr = col("attributes.scene")
    
    # Handle timestamp which may not exist
    if "timestamp" in columns:
        timestamp_expr = col("timestamp")
    else:
        timestamp_expr = lit(None).cast("long")
    
    return df_raw.select(
        filename_expr.alias("filename"),
        concat(col("video_name"), lit("-"), col("frame_index")).alias("image_id"),
        col("video_name"),
        col("frame_index"),
        timestamp_expr.alias("timestamp"),
        weather_expr.alias("weather"),
        timeofday_expr.alias("timeofday"),
        scene_expr.alias("scene"),
        size(col("labels")).alias("total_labels"),
        current_date().alias("ingestion_date"),
        current_timestamp().alias("processing_date")
    ).distinct()

# COMMAND ----------

def create_labels_dataframe(df_raw):
    """Transform raw data into labels dataframe."""
    # Explode labels array
    df_labels_exploded = df_raw.select(
        concat(col("video_name"), lit("-"), col("frame_index")).alias("image_id"),
        explode(col("labels")).alias("label")
    )
    
    # Transform individual label fields
    return df_labels_exploded.select(
        col("label.id").alias("label_id"),
        col("image_id"),
        col("label.category").alias("category"),
        col("label.box2d.x1").cast(DoubleType()).alias("bbox_x1"),
        col("label.box2d.y1").cast(DoubleType()).alias("bbox_y1"),
        col("label.box2d.x2").cast(DoubleType()).alias("bbox_x2"),
        col("label.box2d.y2").cast(DoubleType()).alias("bbox_y2"),
        (col("label.box2d.x2") - col("label.box2d.x1")).cast(DoubleType()).alias("bbox_width"),
        (col("label.box2d.y2") - col("label.box2d.y1")).cast(DoubleType()).alias("bbox_height"),
        ((col("label.box2d.x2") - col("label.box2d.x1")) * 
         (col("label.box2d.y2") - col("label.box2d.y1"))).cast(DoubleType()).alias("bbox_area"),
        col("label.attributes.occluded").cast(BooleanType()).alias("is_occluded"),
        col("label.attributes.truncated").cast(BooleanType()).alias("is_truncated"),
        when(col("label.attributes.trafficLightColor") == "NA", None)
            .otherwise(col("label.attributes.trafficLightColor")).alias("traffic_light_color"),
        current_date().alias("ingestion_date"),
        current_timestamp().alias("processing_date")
    )

# COMMAND ----------

def display_transformation_summary(df_images, df_labels):
    """Display transformation summary statistics."""
    print("\n=== TRANSFORMATION SUMMARY ===")
    print(f"Total images processed: {df_images.count()}")
    print(f"Total labels processed: {df_labels.count()}")
    
    print("\n=== IMAGES TABLE SCHEMA ===")
    df_images.printSchema()
    
    print("\n=== LABELS TABLE SCHEMA ===")
    df_labels.printSchema()
    
    print("\n=== SAMPLE IMAGES DATA ===")
    df_images.show(5, truncate=False)
    
    print("\n=== SAMPLE LABELS DATA ===")
    df_labels.show(5, truncate=False)

# COMMAND ----------

def perform_data_quality_checks(df_images, df_labels):
    """Perform data quality checks on transformed data."""
    print("\n=== DATA QUALITY CHECKS ===")
    print(f"Images with null values: {df_images.filter(col('image_id').isNull()).count()}")
    print(f"Labels with null values: {df_labels.filter(col('label_id').isNull()).count()}")
    print(f"Unique weather conditions: {df_images.select('weather').distinct().count()}")
    print(f"Unique time of day values: {df_images.select('timeofday').distinct().count()}")
    print(f"Unique scene types: {df_images.select('scene').distinct().count()}")
    print(f"Unique label categories: {df_labels.select('category').distinct().count()}")

# COMMAND ----------

labels_path = f"{bronze_path}/qualified"
output_path = f"{silver_path}/bdd100k"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Read and Explore Raw Data

# COMMAND ----------

# Read all JSON files from the labels directory
df_raw = spark.read.option("multiline", "true").json(f"{labels_path}/*.json")

# Debug: Print schema to see available columns
print("Schema of the raw data:")
df_raw.printSchema()
print("\nSample data:")
df_raw.show(2, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transform Data

# COMMAND ----------

# Transform data for Images table
print("Creating images dataframe...")
df_images = create_images_dataframe(df_raw)

# COMMAND ----------

# Transform data for Labels table  
print("Creating labels dataframe...")
df_labels = create_labels_dataframe(df_raw)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save Transformed Data

# COMMAND ----------

# MAGIC %sql drop table if exists std_images_table

# COMMAND ----------

print("Writing images table as managed Delta table...")
dbutils.fs.rm(f"{silver_path}/images", True)
df_images.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("ingestion_date") \
    .option("path", f"{silver_path}/images") \
    .saveAsTable("std_images_table")

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from std_images_table

# COMMAND ----------

# MAGIC %sql drop table if exists std_labels_table

# COMMAND ----------

dbutils.fs.rm(f"{silver_path}/labels", True)

# COMMAND ----------

print("Writing labels table as managed Delta table...")
df_labels.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("ingestion_date") \
    .option("path", f"{silver_path}/labels") \
    .option("mergeSchema", "false") \
    .saveAsTable("std_labels_table")

# COMMAND ----------

# MAGIC %sql select* from std_labels_table

# COMMAND ----------

print(f"\n=== SILVER LAYER TABLES SAVED ===")
print(f"Images table: {output_path}/images")
print(f"Labels table: {output_path}/labels")

# COMMAND ----------

df_labels.printSchema()

# COMMAND ----------

df_images.printSchema()


# COMMAND ----------

