# DevContainer Setup Guide

## Overview

This guide explains how to set up and use the Azure AI Foundry Workshop development container (devcontainer). The devcontainer provides a complete, consistent development environment with all necessary tools, libraries, and dependencies pre-installed.

## What is a DevContainer?

A development container (devcontainer) is a running container that provides a full-featured development environment. It includes:
- Runtime environment (Python, Node.js, etc.)
- Development tools (VS Code extensions, debuggers, etc.)
- Dependencies and libraries
- Configuration files

## Prerequisites

### Required Software

1. **Visual Studio Code**
   - Download from [code.visualstudio.com](https://code.visualstudio.com/)
   - Install the "Dev Containers" extension

2. **Docker Desktop**
   - Download from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
   - Ensure Docker is running before opening the devcontainer

3. **Git** (usually included with VS Code)
   - For cloning the repository

### System Requirements

- **Windows**: Windows 10/11 with WSL2
- **macOS**: macOS 10.14 or later
- **Linux**: Most modern distributions
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB free space for container and dependencies

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd azure-ai-foundry-workshop
```

### 2. Open in VS Code

```bash
code .
```

### 3. Open in DevContainer

When VS Code opens, you should see a popup asking if you want to "Reopen in Container". Click **"Reopen in Container"**.

Alternatively, you can:
1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type "Dev Containers: Reopen in Container"
3. Press Enter

### 4. Wait for Setup

The first time you open the devcontainer, it will:
- Download the base Docker image (~2-3 GB)
- Install all dependencies
- Configure the development environment
- Run post-creation scripts

This process takes 5-15 minutes depending on your internet connection.
