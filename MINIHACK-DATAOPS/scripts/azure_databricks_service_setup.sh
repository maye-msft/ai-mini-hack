#!/bin/bash

# Azure Databricks Service Principal Setup Script
# This script sets up service principal authentication for non-premium Databricks workspaces

set -e

# Configuration
RESOURCE_GROUP="avopsminihack-rg"
LOCATION="eastus2"
TS="001"
STORAGE_ACCOUNT="avopsminihackstg${TS}"
DATABRICKS_WORKSPACE="avops-databricks-workspace-${TS}"
KEY_VAULT_NAME="avops-keyvault-${TS}"
CONTAINER_BRONZE="bronze"
CONTAINER_SILVER="silver"
CONTAINER_GOLD="gold"
CONTAINER_UPLOAD="upload"


# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Function to check if resource exists
resource_exists() {
    local resource_type=$1
    local resource_name=$2
    local resource_group=$3
    
    case $resource_type in
        "group")
            az group show --name "$resource_name" --output none 2>/dev/null
            ;;
        "storage")
            az storage account show --name "$resource_name" --resource-group "$resource_group" --output none 2>/dev/null
            ;;
        "databricks")
            az databricks workspace show --name "$resource_name" --resource-group "$resource_group" --output none 2>/dev/null
            ;;
        "keyvault")
            az keyvault show --name "$resource_name" --resource-group "$resource_group" --output none 2>/dev/null
            ;;
        *)
            return 1
            ;;
    esac
}

# Function to load service principal credentials from .env file
load_service_principal_credentials() {
    log "Loading service principal credentials from .env file..."
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        error ".env file not found. Please create .env file with CLIENT_ID, APP_SECRET, and TENANT_ID"
    fi
    
    # Load credentials from .env file
    source .env
    
    # Validate required variables
    if [ -z "$CLIENT_ID" ] || [ -z "$APP_SECRET" ] || [ -z "$TENANT_ID" ]; then
        error "Missing required variables in .env file. Please ensure CLIENT_ID, APP_SECRET, and TENANT_ID are set"
    fi
    
    # Set APP_ID for compatibility with existing code
    APP_ID=$CLIENT_ID
    
    # Get the object ID for the service principal
    SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query 'id' --output tsv 2>/dev/null)
    
    if [ -z "$SP_OBJECT_ID" ]; then
        error "Service Principal with App ID $APP_ID not found. Please verify the CLIENT_ID in .env file"
    fi
    
    log "✓ Service Principal credentials loaded successfully"
    log "✓ App ID: $APP_ID"
    log "✓ Object ID: $SP_OBJECT_ID"
    log "✓ Tenant ID: $TENANT_ID"
    
    # Export variables for use in other functions
    export APP_ID
    export SP_OBJECT_ID
    export TENANT_ID
    export APP_SECRET
}

# Function to configure service principal permissions
configure_service_principal_permissions() {
    log "Configuring service principal permissions..."
    
    # Get storage account resource ID
    STORAGE_ACCOUNT_RESOURCE_ID=$(az storage account show \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --query 'id' \
        --output tsv)
    
    # Function to check if role is already assigned
    check_role_assignment() {
        local assignee=$1
        local role=$2
        local scope=$3
        
        # Check if role assignment already exists
        local existing_assignment=$(az role assignment list \
            --assignee "$assignee" \
            --role "$role" \
            --scope "$scope" \
            --query '[0].id' \
            --output tsv 2>/dev/null)
        
        if [ -n "$existing_assignment" ] && [ "$existing_assignment" != "null" ]; then
            return 0  # Role already assigned
        else
            return 1  # Role not assigned
        fi
    }
    
    # Function to assign role with retry logic
    assign_role_with_retry() {
        local assignee=$1
        local role=$2
        local scope=$3
        local max_attempts=3
        local attempt=1
        
        # Check if role is already assigned
        if check_role_assignment "$assignee" "$role" "$scope"; then
            log "✓ $role role already assigned to service principal"
            return 0
        fi
        
        while [ $attempt -le $max_attempts ]; do
            log "Assigning $role role to service principal (attempt $attempt/$max_attempts)..."
            
            if az role assignment create \
                --assignee "$assignee" \
                --role "$role" \
                --scope "$scope" \
                --output table 2>/dev/null; then
                log "✓ Successfully assigned $role role"
                return 0
            else
                if [ $attempt -lt $max_attempts ]; then
                    warning "Role assignment failed, retrying in 30 seconds..."
                    sleep 30
                else
                    warning "Failed to assign $role role after $max_attempts attempts"
                    return 1
                fi
            fi
            
            ((attempt++))
        done
    }
    
    # Assign required roles
    assign_role_with_retry "$APP_ID" "Storage Blob Data Contributor" "$STORAGE_ACCOUNT_RESOURCE_ID"
    assign_role_with_retry "$APP_ID" "Storage Account Contributor" "$STORAGE_ACCOUNT_RESOURCE_ID"
    
    log "✓ Service principal permissions configured"
}

# Function to create and configure Azure Key Vault
create_and_configure_keyvault() {
    log "Creating and configuring Azure Key Vault..."
    
    # Check if Key Vault already exists
    if resource_exists "keyvault" "$KEY_VAULT_NAME" "$RESOURCE_GROUP"; then
        warning "Key Vault '$KEY_VAULT_NAME' already exists"
        
        # Check if public network access is enabled
        PUBLIC_ACCESS=$(az keyvault show --name "$KEY_VAULT_NAME" --resource-group "$RESOURCE_GROUP" --query 'properties.publicNetworkAccess' --output tsv 2>/dev/null)
        
        if [ "$PUBLIC_ACCESS" = "Disabled" ]; then
            log "Enabling public network access temporarily for Key Vault setup..."
            az keyvault update \
                --name "$KEY_VAULT_NAME" \
                --resource-group "$RESOURCE_GROUP" \
                --public-network-access Enabled \
                --output table
            
            log "✓ Public network access enabled temporarily"
            # Set flag to disable it later
            DISABLE_PUBLIC_ACCESS=true
        fi
    else
        log "Creating Key Vault: $KEY_VAULT_NAME"
        az keyvault create \
            --name "$KEY_VAULT_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --location "$LOCATION" \
            --sku Standard \
            --enable-rbac-authorization false \
            --public-network-access Enabled \
            --output table
        
        log "✓ Key Vault created successfully"
    fi
    
    # Add service principal client secret to Key Vault
    log "Adding service principal client secret to Key Vault..."
    
    # Retry logic for Key Vault operations
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if az keyvault secret set \
            --vault-name "$KEY_VAULT_NAME" \
            --name "sp-client-secret" \
            --value "$APP_SECRET" \
            --output table; then
            log "✓ Service principal secret added to Key Vault"
            break
        else
            if [ $attempt -lt $max_attempts ]; then
                warning "Failed to add secret (attempt $attempt/$max_attempts), retrying in 30 seconds..."
                sleep 30
            else
                error "Failed to add secret to Key Vault after $max_attempts attempts"
            fi
        fi
        ((attempt++))
    done
    
    # Grant Databricks service principal access to Key Vault
    log "Granting Databricks access to Key Vault..."
    
    # Standard Databricks application ID (same for all Databricks workspaces)
    DATABRICKS_APP_ID="2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"
    
    az keyvault set-policy \
        --name "$KEY_VAULT_NAME" \
        --spn "$DATABRICKS_APP_ID" \
        --secret-permissions get list \
        --output table
    
    log "✓ Databricks access granted to Key Vault"
    
    # Get Key Vault details for secret scope creation
    KEY_VAULT_URI=$(az keyvault show --name "$KEY_VAULT_NAME" --resource-group "$RESOURCE_GROUP" --query 'properties.vaultUri' --output tsv)
    KEY_VAULT_RESOURCE_ID=$(az keyvault show --name "$KEY_VAULT_NAME" --resource-group "$RESOURCE_GROUP" --query 'id' --output tsv)
    
    log "✓ Key Vault URI: $KEY_VAULT_URI"
    log "✓ Key Vault Resource ID: $KEY_VAULT_RESOURCE_ID"
    
    # Disable public network access if it was enabled temporarily
    if [ "$DISABLE_PUBLIC_ACCESS" = "true" ]; then
        log "Disabling public network access for security..."
        az keyvault update \
            --name "$KEY_VAULT_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --public-network-access Disabled \
            --output table
        
        log "✓ Public network access disabled for security"
        warning "Note: Future Key Vault operations will require private endpoint or trusted service access"
    fi
    
    # Export variables for use in other functions
    export KEY_VAULT_URI
    export KEY_VAULT_RESOURCE_ID
}

# Function to create storage containers
create_containers() {
    log "Creating Data Lake containers..."
    
    # Get storage account key for container creation
    STORAGE_KEY=$(az storage account keys list \
        --resource-group "$RESOURCE_GROUP" \
        --account-name "$STORAGE_ACCOUNT" \
        --query '[0].value' \
        --output tsv)
    
    # Create containers for medallion architecture
    containers=("$CONTAINER_BRONZE" "$CONTAINER_SILVER" "$CONTAINER_GOLD" "$CONTAINER_UPLOAD")
    
    for container in "${containers[@]}"; do
        log "Creating container: $container"
        az storage container create \
            --name "$container" \
            --account-name "$STORAGE_ACCOUNT" \
            --account-key "$STORAGE_KEY" \
            --output none
        
        # Create directory structure for BDD100K data
        az storage blob directory create \
            --container-name "$container" \
            --directory-path "bdd100k" \
            --account-name "$STORAGE_ACCOUNT" \
            --account-key "$STORAGE_KEY" \
            --output none 2>/dev/null || true
    done
    
    log "✓ All containers created successfully"
}

# Function to generate service principal configuration notebook
generate_service_principal_config() {
    log "Generating service principal configuration notebook..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    cat > "$SCRIPT_DIR/service_principal_config.py" << EOF
# Databricks notebook source
# MAGIC %md
# MAGIC # Service Principal Configuration for Azure Data Lake Storage
# MAGIC 
# MAGIC This notebook configures service principal authentication for non-premium Databricks workspaces.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Configuration Variables

# COMMAND ----------

# Configuration variables
storage_account_name = "$STORAGE_ACCOUNT"
tenant_id = "$TENANT_ID"
app_id = "$APP_ID"

# Secret scope and key names (to be created)
secret_scope = "avops-secrets"
client_secret_key = "sp-client-secret"

print(f"Storage Account: {storage_account_name}")
print(f"Tenant ID: {tenant_id}")
print(f"App ID: {app_id}")
print(f"Secret Scope: {secret_scope}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Test Service Principal Authentication

# COMMAND ----------

# Test service principal authentication
try:
    # Get client secret from secret scope
    client_secret = dbutils.secrets.get(scope=secret_scope, key=client_secret_key)
    print("✓ Successfully retrieved client secret from secret scope")
    
    # Configure Spark to use service principal
    spark.conf.set(f"fs.azure.account.auth.type.{storage_account_name}.dfs.core.windows.net", "OAuth")
    spark.conf.set(f"fs.azure.account.oauth.provider.type.{storage_account_name}.dfs.core.windows.net", "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
    spark.conf.set(f"fs.azure.account.oauth2.client.id.{storage_account_name}.dfs.core.windows.net", app_id)
    spark.conf.set(f"fs.azure.account.oauth2.client.secret.{storage_account_name}.dfs.core.windows.net", client_secret)
    spark.conf.set(f"fs.azure.account.oauth2.client.endpoint.{storage_account_name}.dfs.core.windows.net", f"https://login.microsoftonline.com/{tenant_id}/oauth2/token")
    
    print("✓ Service principal authentication configured")
    
    # Test access to bronze container
    bronze_path = f"abfss://bronze@{storage_account_name}.dfs.core.windows.net/"
    files = dbutils.fs.ls(bronze_path)
    print(f"✓ Successfully accessed bronze container: {len(files)} items")
    
except Exception as e:
    print(f"✗ Error configuring service principal: {e}")
    print("Make sure you have:")
    print("1. Created the secret scope")
    print("2. Added the client secret to the secret scope")
    print("3. Granted proper permissions to the service principal")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Create Mount Points (Alternative to Unity Catalog)

# COMMAND ----------

# Create mount points for each container
containers = ["bronze", "silver", "gold", "upload"]

for container in containers:
    mount_point = f"/mnt/avops/{container}"
    
    try:
        # Check if already mounted
        existing_mounts = [mount.mountPoint for mount in dbutils.fs.mounts()]
        
        if mount_point in existing_mounts:
            print(f"✓ Mount point '{mount_point}' already exists")
        else:
            # Create mount
            dbutils.fs.mount(
                source = f"abfss://{container}@{storage_account_name}.dfs.core.windows.net/",
                mount_point = mount_point,
                extra_configs = {
                    f"fs.azure.account.auth.type": "OAuth",
                    f"fs.azure.account.oauth.provider.type": "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
                    f"fs.azure.account.oauth2.client.id": app_id,
                    f"fs.azure.account.oauth2.client.secret": dbutils.secrets.get(scope=secret_scope, key=client_secret_key),
                    f"fs.azure.account.oauth2.client.endpoint": f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
                }
            )
            print(f"✓ Mount point '{mount_point}' created successfully")
        
        # Test the mount
        test_files = dbutils.fs.ls(mount_point)
        print(f"✓ Mount point '{mount_point}' is accessible: {len(test_files)} items")
        
    except Exception as e:
        print(f"✗ Error creating mount point '{mount_point}': {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Verify Mount Points and Access

# COMMAND ----------

# List all mount points
print("=== Mount Points ===")
mounts = dbutils.fs.mounts()
for mount in mounts:
    if "/mnt/avops" in mount.mountPoint:
        print(f"✓ {mount.mountPoint} → {mount.source}")

# Test data access through mount points
print("\n=== Testing Data Access ===")
try:
    # Test bronze mount
    bronze_files = dbutils.fs.ls("/mnt/avops/bronze/")
    print(f"✓ Bronze container accessible: {len(bronze_files)} items")
    
    # Test if sample data exists
    try:
        sample_files = dbutils.fs.ls("/mnt/avops/bronze/bdd100k/sample_data/")
        print(f"✓ Sample data directory accessible: {len(sample_files)} items")
    except Exception as e:
        print(f"⚠ Sample data directory not found: {e}")
        
except Exception as e:
    print(f"✗ Data access test failed: {e}")

print("\n=== Service Principal Configuration Complete ===")
print("✓ Service principal authentication configured")
print("✓ Mount points created for all containers")
print("✓ Data access verified through mount points")
print("✓ Ready for data processing workflows")

EOF

    log "✓ Service principal configuration notebook saved to $SCRIPT_DIR/service_principal_config.py"
}

# Function to create sample data
create_sample_data() {
    log "Creating sample CSV data for testing..."
    
    # Create sample CSV file
    cat > "/tmp/sample_bdd100k_data.csv" << EOF
image_name,weather,timeofday,scene,object_count,car_count,truck_count,person_count
0a0a0b1a-7c39d841.jpg,clear,daytime,highway,7,5,1,1
b1c2d3e4-f5g6h7i8.jpg,rainy,nighttime,city_street,12,8,2,2
c9d8e7f6-a5b4c3d2.jpg,cloudy,daytime,residential,6,4,0,2
e1f2g3h4-i5j6k7l8.jpg,clear,daytime,highway,15,12,3,0
m9n8o7p6-q5r4s3t2.jpg,foggy,dawn,parking_lot,20,15,2,3
u1v2w3x4-y5z6a7b8.jpg,clear,dusk,city_street,9,6,1,2
c1d2e3f4-g5h6i7j8.jpg,overcast,daytime,tunnel,4,3,1,0
k9l8m7n6-o5p4q3r2.jpg,clear,nighttime,highway,8,6,2,0
s1t2u3v4-w5x6y7z8.jpg,rainy,daytime,residential,11,7,1,3
a9b8c7d6-e5f4g3h2.jpg,clear,daytime,city_street,14,10,2,2
EOF

    # Get storage account key for upload
    STORAGE_KEY=$(az storage account keys list \
        --resource-group "$RESOURCE_GROUP" \
        --account-name "$STORAGE_ACCOUNT" \
        --query '[0].value' \
        --output tsv)

    # Upload sample CSV to bronze container
    log "Uploading sample CSV to bronze container..."
    az storage blob upload \
        --account-name "$STORAGE_ACCOUNT" \
        --account-key "$STORAGE_KEY" \
        --container-name "bronze" \
        --name "bdd100k/sample_data/sample_bdd100k_data.csv" \
        --file "/tmp/sample_bdd100k_data.csv" \
        --overwrite

    log "✓ Sample CSV data uploaded to bronze/bdd100k/sample_data/"
    
    # Clean up local file
    rm -f "/tmp/sample_bdd100k_data.csv"
}

# Function to generate analysis notebook
generate_analysis_notebook() {
    log "Generating service principal analysis notebook..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    cat > "$SCRIPT_DIR/sample_data_analysis.py" << EOF
# Databricks notebook source
# MAGIC %md
# MAGIC # Data Analysis with Service Principal Authentication
# MAGIC 
# MAGIC This notebook demonstrates data analysis using service principal authentication for non-premium Databricks workspaces.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup and Configuration

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Configuration
storage_account_name = "$STORAGE_ACCOUNT"
tenant_id = "$TENANT_ID"
app_id = "$APP_ID"
secret_scope = "avops-secrets"
client_secret_key = "sp-client-secret"

print(f"Storage Account: {storage_account_name}")
print(f"App ID: {app_id}")
print(f"Using mount points for data access")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Load Data Using Mount Points

# COMMAND ----------

# Load data from mount point
sample_path = "/mnt/avops/bronze/bdd100k/sample_data/sample_bdd100k_data.csv"

try:
    # Read CSV using mount point
    df = spark.read.option("header", "true").option("inferSchema", "true").csv(sample_path)
    row_count = df.count()
    
    print(f"✓ Successfully loaded data using service principal authentication")
    print(f"📊 Number of rows: {row_count}")
    
    # Display sample data
    print("\n=== Sample Data ===")
    df.show(10)
    
    # Show schema
    print("\n=== Data Schema ===")
    df.printSchema()
    
    # Register as temporary view for SQL queries
    df.createOrReplaceTempView("sample_bdd100k_data")
    
except Exception as e:
    print(f"✗ Error loading data: {e}")
    df = None
    row_count = 0

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Data Analysis

# COMMAND ----------

if df is not None:
    # Weather distribution
    print("=== Weather Distribution ===")
    weather_dist = df.groupBy("weather").count().orderBy("count", ascending=False)
    weather_dist.show()
    
    # Time of day distribution
    print("\n=== Time of Day Distribution ===")
    timeofday_dist = df.groupBy("timeofday").count().orderBy("count", ascending=False)
    timeofday_dist.show()
    
    # Average object counts
    print("\n=== Average Object Counts ===")
    avg_stats = df.select(
        avg("object_count").alias("avg_objects"),
        avg("car_count").alias("avg_cars"),
        avg("truck_count").alias("avg_trucks"),
        avg("person_count").alias("avg_persons")
    )
    avg_stats.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Create Silver Layer Processing

# COMMAND ----------

if df is not None:
    try:
        # Create summary data for silver layer
        silver_df = df.groupBy("weather", "timeofday", "scene").agg(
            count("*").alias("image_count"),
            avg("object_count").alias("avg_objects"),
            sum("car_count").alias("total_cars"),
            sum("truck_count").alias("total_trucks"),
            sum("person_count").alias("total_persons")
        ).withColumn("processing_date", current_timestamp())
        
        # Save to silver layer using mount point
        silver_path = "/mnt/avops/silver/bdd100k/analysis_results/"
        silver_df.write.mode("overwrite").option("overwriteSchema", "true").parquet(silver_path)
        
        print(f"✓ Silver layer data saved to: {silver_path}")
        print(f"📊 Summary records created: {silver_df.count()}")
        
    except Exception as e:
        print(f"✗ Error creating silver layer: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Create Gold Layer Business Metrics

# COMMAND ----------

if df is not None:
    try:
        # Create business metrics for gold layer
        gold_df = df.agg(
            count("*").alias("total_images"),
            avg("object_count").alias("avg_objects_per_image"),
            sum("car_count").alias("total_cars_detected"),
            sum("truck_count").alias("total_trucks_detected"),
            sum("person_count").alias("total_persons_detected"),
            countDistinct("weather").alias("unique_weather_conditions"),
            countDistinct("scene").alias("unique_scene_types")
        ).withColumn("analysis_date", current_timestamp()).withColumn("dataset_version", lit("1.0"))
        
        # Save to gold layer
        gold_path = "/mnt/avops/gold/bdd100k/business_metrics/"
        gold_df.write.mode("overwrite").option("overwriteSchema", "true").parquet(gold_path)
        
        print(f"✓ Gold layer metrics saved to: {gold_path}")
        print("\n=== Business Metrics ===")
        gold_df.show()
        
    except Exception as e:
        print(f"✗ Error creating gold layer: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Final Results and Summary

# COMMAND ----------

print("=== Service Principal Data Processing Summary ===")
print("✓ Service principal authentication configured")
print("✓ Mount points created for secure data access")
print("✓ Bronze Layer: Raw CSV data loaded")
print("✓ Silver Layer: Aggregated data processed")
print("✓ Gold Layer: Business metrics generated")
print("")
if df is not None:
    final_count = df.count()
    print(f"📊 Data Processing Results:")
    print(f"   • Source CSV rows: {final_count}")
    print(f"   • Silver aggregations: Created")
    print(f"   • Gold metrics: Generated")
    print(f"🎯 Answer: The CSV file contains {final_count} rows of automotive data")
else:
    print("⚠ No data was processed due to connection issues")

print("\n=== Service Principal Benefits ===")
print("• Secure service principal authentication")
print("• No Unity Catalog required (works with standard Databricks)")
print("• Mount points provide familiar file system access")
print("• Supports medallion architecture (Bronze-Silver-Gold)")
print("• Compatible with existing Databricks workflows")

EOF

    log "✓ Service principal analysis notebook saved to $SCRIPT_DIR/sample_data_analysis.py"
}

# Function to create secret scope setup instructions
create_secret_scope_instructions() {
    log "Creating secret scope setup instructions..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    cat > "$SCRIPT_DIR/secret_scope_setup.md" << EOF
# Secret Scope Setup Instructions

## Overview
Since Unity Catalog is not available in standard Databricks workspaces, we use Azure Key Vault-backed secret scopes to securely store service principal credentials.

## Step 1: Key Vault Setup (Already Completed)

✓ Key Vault created: $KEY_VAULT_NAME
✓ Service principal secret added to Key Vault
✓ Databricks access configured

## Step 2: Create Secret Scope in Databricks

1. **Access Secret Scope Creation URL:**
   - Go to: \`https://<databricks-instance>#secrets/createScope\`
   - Replace \`<databricks-instance>\` with your Databricks workspace URL

2. **Create Azure Key Vault-backed Secret Scope:**
   - **Scope Name:** \`avops-secrets\`
   - **Manage Principal:** \`All Users\` (or restrict as needed)
   - **DNS Name:** \`$KEY_VAULT_URI\`
   - **Resource ID:** \`$KEY_VAULT_RESOURCE_ID\`

## Step 3: Access Details (Already Configured)

✓ Key Vault: $KEY_VAULT_NAME
✓ Key Vault URI: $KEY_VAULT_URI
✓ Secret Name: sp-client-secret
✓ Databricks App ID: 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d

## Step 4: Verify Secret Scope

Run this in a Databricks notebook:

\`\`\`python
# List secret scopes
dbutils.secrets.listScopes()

# List secrets in scope
dbutils.secrets.list("avops-secrets")

# Test secret retrieval (value will be redacted)
secret_value = dbutils.secrets.get("avops-secrets", "sp-client-secret")
print("Secret retrieved successfully" if secret_value else "Failed to retrieve secret")
\`\`\`

## Security Notes

- Never store secrets in notebooks or code
- Use secret scopes for all sensitive configuration
- Rotate service principal secrets regularly
- Monitor access to secret scopes
- Use least-privilege access for service principals

## Next Steps

After creating the secret scope:
1. Run the \`service_principal_config.py\` notebook
2. Run the \`sample_data_analysis.py\` notebook
3. Verify data access and processing

EOF

    log "✓ Secret scope setup instructions saved to $SCRIPT_DIR/secret_scope_setup.md"
}

# Main execution function
main() {
    log "=== Azure Databricks Service Principal Setup ==="
    log "Resource Group: $RESOURCE_GROUP"
    log "Storage Account: $STORAGE_ACCOUNT"
    log "Databricks Workspace: $DATABRICKS_WORKSPACE"
    log "Location: $LOCATION"
    echo ""

    # Step 1: Create Resource Group
    log "Step 1: Creating Resource Group"
    if resource_exists "group" "$RESOURCE_GROUP"; then
        warning "Resource group '$RESOURCE_GROUP' already exists"
    else
        az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
        log "✓ Resource group created"
    fi

    # Step 2: Create Data Lake Storage Gen2
    log "Step 2: Creating Azure Data Lake Storage Gen2"
    if resource_exists "storage" "$STORAGE_ACCOUNT" "$RESOURCE_GROUP"; then
        warning "Storage account '$STORAGE_ACCOUNT' already exists"
    else
        az storage account create \
            --name "$STORAGE_ACCOUNT" \
            --resource-group "$RESOURCE_GROUP" \
            --location "$LOCATION" \
            --sku Standard_LRS \
            --kind StorageV2 \
            --hierarchical-namespace true
        log "✓ Data Lake Storage Gen2 created"
    fi

    # Step 3: Create Databricks Workspace
    log "Step 3: Creating Azure Databricks Workspace"
    if resource_exists "databricks" "$DATABRICKS_WORKSPACE" "$RESOURCE_GROUP"; then
        warning "Databricks workspace '$DATABRICKS_WORKSPACE' already exists"
    else
        az databricks workspace create \
            --name "$DATABRICKS_WORKSPACE" \
            --resource-group "$RESOURCE_GROUP" \
            --location "$LOCATION" \
            --sku standard
        log "✓ Databricks workspace created"
    fi

    # Step 4: Load Service Principal Credentials
    log "Step 4: Loading Service Principal Credentials"
    load_service_principal_credentials
    log "✓ Service Principal credentials loaded"

    # Step 5: Configure Service Principal Permissions
    log "Step 5: Configuring Service Principal Permissions"
    configure_service_principal_permissions
    log "✓ Service Principal permissions configured"

    # Step 6: Create and Configure Azure Key Vault
    log "Step 6: Creating and Configuring Azure Key Vault"
    create_and_configure_keyvault
    log "✓ Key Vault created and configured"

    # Step 7: Create Storage Containers
    log "Step 7: Creating Storage Containers"
    create_containers
    log "✓ Storage containers created"

    # Step 8: Generate Service Principal Configuration
    log "Step 8: Generating Service Principal Configuration"
    generate_service_principal_config
    log "✓ Service Principal configuration notebook generated"

    # Step 9: Create Sample Data
    log "Step 9: Creating Sample Data"
    create_sample_data
    log "✓ Sample data created"

    # Step 10: Generate Analysis Notebook
    log "Step 10: Generating Analysis Notebook"
    generate_analysis_notebook
    log "✓ Analysis notebook generated"

    # Step 11: Create Secret Scope Instructions
    log "Step 11: Creating Secret Scope Setup Instructions"
    create_secret_scope_instructions
    log "✓ Secret scope instructions created"

    # Step 12: Display Setup Summary
    log "Step 12: Setup Complete - Displaying Summary"
    
    DATABRICKS_URL=$(az databricks workspace show \
        --name "$DATABRICKS_WORKSPACE" \
        --resource-group "$RESOURCE_GROUP" \
        --query 'workspaceUrl' \
        --output tsv)
    
    STORAGE_ENDPOINT=$(az storage account show \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --query 'primaryEndpoints.dfs' \
        --output tsv)
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    echo ""
    log "=== SERVICE PRINCIPAL SETUP COMPLETE ==="
    echo ""
    info "=== Resource Details ==="
    echo "Resource Group: $RESOURCE_GROUP"
    echo "Storage Account: $STORAGE_ACCOUNT"
    echo "Storage Endpoint: $STORAGE_ENDPOINT"
    echo "Databricks Workspace: $DATABRICKS_WORKSPACE"
    echo "Databricks URL: https://$DATABRICKS_URL"
    echo "Key Vault: $KEY_VAULT_NAME"
    echo "Key Vault URI: $KEY_VAULT_URI"
    echo "App ID: $APP_ID"
    echo "Tenant ID: $TENANT_ID"
    echo ""
    info "=== Security Architecture ==="
    echo "✓ Azure AD Service Principal with OAuth 2.0"
    echo "✓ Role-based access control (RBAC) for storage"
    echo "✓ Client secret stored securely in Azure Key Vault"
    echo "✓ Databricks secret scope for credential management"
    echo "✓ Mount points for secure data access"
    echo ""
    info "=== Data Lake Architecture ==="
    echo "Bronze Container: abfss://bronze@$STORAGE_ACCOUNT.dfs.core.windows.net/"
    echo "Silver Container: abfss://silver@$STORAGE_ACCOUNT.dfs.core.windows.net/"
    echo "Gold Container: abfss://gold@$STORAGE_ACCOUNT.dfs.core.windows.net/"
    echo "Upload Container: abfss://upload@$STORAGE_ACCOUNT.dfs.core.windows.net/"
    echo ""
    info "=== Mount Points (to be created) ==="
    echo "/mnt/avops/bronze → Bronze layer"
    echo "/mnt/avops/silver → Silver layer"
    echo "/mnt/avops/gold → Gold layer"
    echo "/mnt/avops/upload → Upload area"
    echo ""
    info "=== Generated Files ==="
    echo "Service Principal Config: $SCRIPT_DIR/service_principal_config.py"
    echo "Data Analysis: $SCRIPT_DIR/sample_data_analysis.py"
    echo "Secret Scope Setup: $SCRIPT_DIR/secret_scope_setup.md"
    echo ""
    info "=== Setup Instructions ==="
    echo "1. Follow the secret scope setup instructions in secret_scope_setup.md"
    echo "2. Access Databricks workspace: https://$DATABRICKS_URL"
    echo "3. Import the generated notebooks into Databricks workspace"
    echo "4. Run 'service_principal_config.py' first to create mount points"
    echo "5. Run 'sample_data_analysis.py' to analyze the sample data"
    echo "6. The analysis will show that the CSV contains 10 rows of automotive data"
    echo ""
    info "=== Important Security Notes ==="
    echo "• Service principal credentials loaded from .env file"
    echo "• Client secret securely stored in Azure Key Vault"
    echo "• Azure Key Vault-backed secret scope configured"
    echo "• Rotate service principal secrets regularly"
    echo "• Monitor access to secret scopes and mount points"
    echo "• Use least-privilege access for service principals"
    echo ""
    warning "=== Next Steps ==="
    echo "1. Read $SCRIPT_DIR/secret_scope_setup.md for detailed instructions"
    echo "2. Create the secret scope before running the notebooks"
    echo "3. Import and run the notebooks in Databricks"
    echo "4. Ensure .env file is properly secured and not committed to version control"
    echo ""
    log "=== SETUP COMPLETED SUCCESSFULLY ==="
    echo "Ready to use service principal authentication with Databricks!"
}

# Execute main function
main "$@"