FROM mcr.microsoft.com/devcontainers/python:3.10

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Azure CLI and application insights and azure devops extension
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Set working directory
WORKDIR /workspace