# DataOps Hackathon: AVOps Data Analytics

## Overview

Welcome to our data pipeline hackathon! This hands-on challenge will guide you through building a complete data processing pipeline using the medallion architecture pattern. You'll work with a computer vision dataset containing 7,000 images with labeled annotations to extract weather patterns, object classifications, and scene categorizations.

## Dataset: DBB00K Image Collection



Our hackathon uses a subset of autonomous driving datasets containing:
- **the DBB00K dataset**: https://github.com/bdd100k/bdd100k
- **7,000 images** with corresponding annotation files
- **Structured labels** including weather conditions, object categories, and scene types
- **JSON format annotations** with metadata for each image

## Background: Medallion Architecture

The medallion architecture is a data design pattern that organizes data into three progressive quality layers:

### 🥉 Bronze Layer (Raw Data)
- Contains raw, unprocessed data in its original format
- Preserves data lineage and enables reprocessing
- Minimal validation performed

### 🥈 Silver Layer (Cleaned Data)  
- Data is cleaned, validated, and conformed
- Provides an "enterprise view" of business entities
- Enables self-service analytics

### 🥇 Gold Layer (Business-Ready Data)
- Aggregated, enriched data optimized for analytics
- Structured for reporting and business intelligence
- Ready for consumption by end users

## Reference Materials

### Core Concepts
- **ETL Overview**: [Extract, Transform, Load (ETL) - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/data-guide/relational-data/etl)
- **Medallion Architecture**: [Databricks Medallion Architecture Guide](https://www.databricks.com/glossary/medallion-architecture)

### Azure Technologies
- **Azure Databricks**: [Microsoft Azure Databricks Documentation](https://learn.microsoft.com/en-us/azure/databricks/)
- **Azure Data Lake Storage**: [ADLS Documentation](https://learn.microsoft.com/en-us/azure/storage/blobs/)
- **Azure Data Factory**: [ADF Documentation](https://learn.microsoft.com/en-us/azure/data-factory/)
- **Azure Fabric**: [Microsoft Fabric Documentation](https://learn.microsoft.com/en-us/fabric/)

---

## Task 1: Data Ingestion
**Goal**: Import the DBB00K dataset into the Bronze layer

**📝 Create a Databricks Notebook**: In your workspace, click New in the sidebar, and then click Notebook to create a new notebook for this challenge.

Build a notebook that:
1. Connects to the pre-configured Bronze layer storage
2. Loads and extracts the compressed dataset
3. Organizes images and annotation files appropriately


### Reference Materials
- **Creating Notebooks**: [Manage Notebooks - Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/notebooks/notebooks-manage)
- **File System Operations**: [Databricks Utilities (dbutils) Reference](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-utils)
- **Working with Files**: [Work with Files on Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/files/)
- **File System Examples**: [Microsoft Azure Databricks File Operations Workshop](https://github.com/microsoft/Azure-Databricks-NYC-Taxi-Workshop/blob/master/code/01-Primer/pyspark/00-azure-storage/3-filesystem-operations.py)

### Solution Reference
`solution/notebooks/0-ingestion.py`

---

## Task 2: Data Cleansing
**Goal**: Filter and validate JSON annotation files

**📝 Create a Databricks Notebook**: Create a new notebook in your workspace for data cleansing operations.

Create a process to:
1. Validate JSON file structure and format
2. Filter out files missing critical fields
3. Handle malformed or corrupted annotations
4. Prepare clean data for the Silver layer

### Reference Materials
- **Notebook Development**: [Develop Code in Databricks Notebooks](https://learn.microsoft.com/en-us/azure/databricks/notebooks/notebooks-code)
- **Python in Databricks**: [Azure Databricks for Python Developers](https://learn.microsoft.com/en-us/azure/databricks/languages/python)
- **File Operations**: [Work with Files on Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/files/)

### Solution Reference
`solution/notebooks/1-cleansing.py`

---

## Task 3: Data Transformation
**Goal**: Convert cleaned data into structured tables

**📝 Create a Databricks Notebook**: Create a new notebook specifically for data transformation tasks using SQL and Python.

Transform Bronze layer data to Silver layer by:
1. Converting annotations into structured table format
2. Implementing proper data types and schema
3. Creating relationships between images and metadata
4. Storing results in Delta Lake format

### Skills You'll Learn
- Data schema design
- Spark DataFrame operations
- Delta Lake table management

### Reference Materials
- **Delta Lake Tutorial**: [Tutorial: Delta Lake - Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/delta/tutorial)
- **What is Delta Lake**: [What is Delta Lake in Azure Databricks?](https://learn.microsoft.com/en-us/azure/databricks/delta/)
- **Delta Lake Training**: [Manage Data with Delta Lake - Microsoft Learn](https://learn.microsoft.com/en-us/training/modules/use-delta-lake-azure-databricks/)
- **Spark DataFrames**: [Tutorial: Load and Transform Data using Apache Spark DataFrames](https://learn.microsoft.com/en-us/azure/databricks/getting-started/dataframes)

### Solution Reference
`solution/notebooks/2-transformation.py`

---

## Task 4: Data Aggregation & Analytics
**Goal**: Create business insights and visualizations

**📝 Create a Databricks Notebook**: Create a new notebook for analytics and visualization, using both SQL and Python capabilities.

Analyze Silver layer data to:
1. **Weather Analytics**: Count weather conditions across images
2. **Object Classification**: Summarize object categories and frequencies  
3. **Scene Analysis**: Analyze scene types and distributions
4. **Data Visualization**: Create charts and graphs for insights
5. Store aggregated results in the Gold layer

### Skills You'll Learn
- Data aggregation techniques
- Statistical analysis with Spark
- Data visualization in Databricks
- Gold layer design patterns

### Reference Materials
- **Query and Visualize Data**: [Tutorial: Query and Visualize Data from a Notebook](https://learn.microsoft.com/en-us/azure/databricks/getting-started/quick-start)
- **Databricks Visualizations**: [Visualizations in Databricks Notebooks](https://learn.microsoft.com/en-us/azure/databricks/notebooks/visualizations/)
- **Databricks Notebooks Overview**: [Databricks Notebooks - Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/notebooks/)
- **SQL in Databricks**: [Databricks SQL Documentation](https://learn.microsoft.com/en-us/azure/databricks/sql/)

### Solution Reference
`solution/notebooks/3-aggregation.py`

---

## Task 5: End-to-End Pipeline
**Goal**: Orchestrate all steps into a complete data pipeline

Integrate all previous challenges into:
1. **Automated Workflow**: Chain all notebooks together
2. **Error Handling**: Implement robust error management
3. **Monitoring**: Add logging and status tracking
4. **Scheduling**: Set up automated pipeline execution

### Skills You'll Learn
- Pipeline orchestration
- Workflow automation
- Production data pipeline best practices

### Reference Materials
- **Azure Databricks Jobs**: [Jobs Documentation](https://learn.microsoft.com/en-us/azure/databricks/workflows/jobs/)
- **Azure Data Factory Pipelines**: [ADF Pipeline Guide](https://learn.microsoft.com/en-us/azure/data-factory/concepts-pipelines-activities)


---

Good luck with your DataOps journey! Remember, the goal is to learn and build something amazing together. 🚀


