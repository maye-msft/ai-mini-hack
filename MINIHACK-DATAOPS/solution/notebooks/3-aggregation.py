# Databricks notebook source
# MAGIC %run ./config

# COMMAND ----------

# MAGIC %sql
# MAGIC
# MAGIC drop table if exists srv_weather_count;
# MAGIC drop table if exists srv_category_count;
# MAGIC drop table if exists srv_scene_count;

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