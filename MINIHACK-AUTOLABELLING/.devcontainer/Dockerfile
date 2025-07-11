# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/devcontainers/python:latest

RUN apt-get update && apt-get install -y libgl1

# Install Jupyter
RUN pip install --upgrade pip


# Install Azure CLI
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Set up a working directory
WORKDIR /workspace
