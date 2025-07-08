# Databricks notebook source
# Configuration variables
storage_account_name = "avopsminihackstg003"
tenant_id = "16b3c013-d300-468d-ac64-7eda0820b6d3"
app_id = "fd9ff89e-aea9-403b-9b1d-f04320099781"

# Secret scope and key names (to be created)
secret_scope = "avops-secrets"
client_secret_key = "sp-client-secret"


# COMMAND ----------

# Test service principal authentication
try:
    # Get client secret from secret scope
    client_secret = dbutils.secrets.get(scope=secret_scope, key=client_secret_key)
    print("✓ Successfully retrieved client secret from secret scope")
    
    # Configure Spark to use service principal
    spark.conf.set(f"fs.azure.account.auth.type", "OAuth")
    spark.conf.set(f"fs.azure.account.oauth.provider.type.{storage_account_name}.dfs.core.windows.net", "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
    spark.conf.set(f"fs.azure.account.oauth2.client.id.{storage_account_name}.dfs.core.windows.net", app_id)
    spark.conf.set(f"fs.azure.account.oauth2.client.secret.{storage_account_name}.dfs.core.windows.net", client_secret)
    spark.conf.set(f"fs.azure.account.oauth2.client.endpoint.{storage_account_name}.dfs.core.windows.net", f"https://login.microsoftonline.com/{tenant_id}/oauth2/token")
    
    print("✓ Service principal authentication configured")
    
    # bronze container
    bronze_path = f"abfss://bronze@{storage_account_name}.dfs.core.windows.net/"
    files = dbutils.fs.ls(bronze_path)
    print(f"✓ Successfully accessed bronze container: {len(files)} items")

    # silver container
    silver_path = f"abfss://silver@{storage_account_name}.dfs.core.windows.net/"
    files = dbutils.fs.ls(silver_path)
    print(f"✓ Successfully accessed silver container: {len(files)} items")
          
    # gold container
    gold_path = f"abfss://gold@{storage_account_name}.dfs.core.windows.net/"
    files = dbutils.fs.ls(gold_path)
    print(f"✓ Successfully accessed gold container: {len(files)} items")

    print("Use the variable 'bronze_path' to access the bronze container")
    print("Use the variable 'silver_path' to access the silver container")
    print("Use the variable 'gold_path' to access the gold container")

    
except Exception as e:
    print(f"✗ Error configuring service principal: {e}")
    print("Make sure you have:")
    print("1. Created the secret scope")
    print("2. Added the client secret to the secret scope")
    print("3. Granted proper permissions to the service principal")

# COMMAND ----------

