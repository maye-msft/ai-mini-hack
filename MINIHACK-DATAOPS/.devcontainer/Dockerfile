# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/devcontainers/python:latest

# Install Java 17, Node.js, and wget
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    nodejs \
    npm \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME for the available Java version
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64

# Install Spark
ENV SPARK_VERSION=3.5.0
ENV HADOOP_VERSION=3
ENV SPARK_HOME=/opt/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin

RUN wget -q "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" && \
    tar xzf "spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" && \
    mv "spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}" /opt/spark && \
    rm "spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz"

# Set PySpark environment variables
ENV PYSPARK_PYTHON=/usr/local/bin/python
ENV PYSPARK_DRIVER_PYTHON=/usr/local/bin/python

# Ensure JAVA_HOME is set in the environment
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64

# Install Jupyter
RUN pip install --upgrade pip 

# Install Azure CLI
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Set up a working directory
WORKDIR /workspace
