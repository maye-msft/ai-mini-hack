# Databricks notebook source
# MAGIC %run ./config

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create mapping table for object categorization
# MAGIC -- This table maps specific object types to broader categories: vehicle, traffic_sign, pedestrian
# MAGIC
# MAGIC CREATE OR REPLACE TABLE object_category_mapping (
# MAGIC     original_category STRING,
# MAGIC     mapped_category STRING,
# MAGIC     category_description STRING
# MAGIC ) USING DELTA;
# MAGIC
# MAGIC -- Insert mapping data
# MAGIC INSERT INTO object_category_mapping VALUES
# MAGIC -- Vehicle category
# MAGIC ('car', 'vehicle', 'Personal passenger vehicle'),
# MAGIC ('truck', 'vehicle', 'Commercial/cargo truck'),
# MAGIC ('bus', 'vehicle', 'Public transportation bus'),
# MAGIC ('bicycle', 'vehicle', 'Two-wheeled bicycle'),
# MAGIC ('motorcycle', 'vehicle', 'Motorized two-wheeler'),
# MAGIC ('other vehicle', 'vehicle', 'Other unspecified vehicle types'),
# MAGIC ('train', 'vehicle', 'Railway train'),
# MAGIC ('trailer', 'vehicle', 'Vehicle trailer/attachment'),
# MAGIC
# MAGIC -- Traffic infrastructure category
# MAGIC ('traffic sign', 'traffic_sign', 'Road signage and traffic signs'),
# MAGIC ('traffic light', 'traffic_sign', 'Traffic control lights'),
# MAGIC
# MAGIC -- Pedestrian category
# MAGIC ('pedestrian', 'pedestrian', 'Person walking'),
# MAGIC ('rider', 'pedestrian', 'Person riding bicycle/motorcycle'),
# MAGIC ('other person', 'pedestrian', 'Other unspecified person types');

# COMMAND ----------

# MAGIC %sql
# MAGIC
# MAGIC WITH object_context AS (
# MAGIC     SELECT 
# MAGIC         l.category as original_category,
# MAGIC         m.mapped_category,
# MAGIC         i.weather,
# MAGIC         i.timeofday,
# MAGIC         i.scene,
# MAGIC         i.image_id,
# MAGIC         l.label_id
# MAGIC     FROM std_labels_table l
# MAGIC     INNER JOIN std_images_table i ON l.image_id = i.image_id
# MAGIC     LEFT JOIN object_category_mapping m ON l.category = m.original_category
# MAGIC ),
# MAGIC
# MAGIC object_counts AS (
# MAGIC     SELECT 
# MAGIC         weather,
# MAGIC         timeofday,
# MAGIC         scene,
# MAGIC         mapped_category,
# MAGIC         image_id,
# MAGIC         COUNT(*) as objects_per_image
# MAGIC     FROM object_context
# MAGIC     WHERE mapped_category IS NOT NULL
# MAGIC     GROUP BY weather, timeofday, scene, mapped_category, image_id
# MAGIC )
# MAGIC
# MAGIC SELECT 
# MAGIC     weather,
# MAGIC     timeofday,
# MAGIC     scene,
# MAGIC     mapped_category,
# MAGIC     
# MAGIC     -- Basic statistics
# MAGIC     SUM(objects_per_image) as total_count,
# MAGIC     COUNT(*) as total_images,
# MAGIC     ROUND(AVG(objects_per_image), 2) as avg_count,
# MAGIC     ROUND(STDDEV(objects_per_image), 2) as std_dev,
# MAGIC     
# MAGIC     -- Percentiles
# MAGIC     percentile_approx(objects_per_image, 0.25) as q1_count,
# MAGIC     percentile_approx(objects_per_image, 0.5) as median_count,
# MAGIC     percentile_approx(objects_per_image, 0.75) as q3_count,
# MAGIC     
# MAGIC     -- Extremes
# MAGIC     MIN(objects_per_image) as min_count,
# MAGIC     MAX(objects_per_image) as max_count
# MAGIC     
# MAGIC FROM object_counts
# MAGIC GROUP BY weather, timeofday, scene, mapped_category
# MAGIC ORDER BY weather, timeofday, scene, mapped_category;
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC select distinct timeofday from std_images_table

# COMMAND ----------

# MAGIC %sql
# MAGIC drop table if exists srv_attribute_analysis;

# COMMAND ----------

# Simple Object Category Count
print("Creating srv_attribute_analysis...")
df_attribute_analysis = spark.sql("""
    
WITH object_context AS (
    SELECT 
        l.category as original_category,
        m.mapped_category,
        i.weather,
        i.timeofday,
        i.scene,
        i.image_id,
        l.label_id
    FROM std_labels_table l
    INNER JOIN std_images_table i ON l.image_id = i.image_id
    LEFT JOIN object_category_mapping m ON l.category = m.original_category
),

object_counts AS (
    SELECT 
        weather,
        timeofday,
        scene,
        mapped_category,
        image_id,
        COUNT(*) as objects_per_image
    FROM object_context
    WHERE mapped_category IS NOT NULL
    GROUP BY weather, timeofday, scene, mapped_category, image_id
)

SELECT 
    weather,
    timeofday,
    scene,
    mapped_category,
    
    -- Basic statistics
    SUM(objects_per_image) as total_count,
    COUNT(*) as total_images,
    ROUND(AVG(objects_per_image), 2) as avg_count,
    ROUND(STDDEV(objects_per_image), 2) as std_dev,
    
    -- Percentiles
    percentile_approx(objects_per_image, 0.25) as q1_count,
    percentile_approx(objects_per_image, 0.5) as median_count,
    percentile_approx(objects_per_image, 0.75) as q3_count,
    
    -- Extremes
    MIN(objects_per_image) as min_count,
    MAX(objects_per_image) as max_count
    
FROM object_counts
GROUP BY weather, timeofday, scene, mapped_category
ORDER BY weather, timeofday, scene, mapped_category;
""")

df_attribute_analysis.write \
    .format("delta") \
    .mode("overwrite") \
    .option("path", f"{gold_path}/srv_attribute_analysis") \
    .saveAsTable("srv_attribute_analysis")

print("✅ Attribute analysis table created successfully!")

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from srv_attribute_analysis

# COMMAND ----------

