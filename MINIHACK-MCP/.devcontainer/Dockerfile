FROM mcr.microsoft.com/devcontainers/python:3.10

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Azure CLI and extensions
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Switch to vscode user to install UV where they can run it
USER vscode
RUN curl -Ls https://astral.sh/uv/install.sh | sh

# Switch back to root for default devcontainer behavior
USER root

# Add UV (vscode-installed) to PATH
ENV PATH="/home/vscode/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /workspace
