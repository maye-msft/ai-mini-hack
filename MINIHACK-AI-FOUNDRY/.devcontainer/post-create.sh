#!/bin/bash

# Azure AI Foundry Workshop - DevContainer Post-Create Script
echo "🚀 Setting up Azure AI Foundry Workshop environment..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# Install additional system dependencies
echo "🔧 Installing system dependencies..."
sudo apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    vim \
    nano \
    jq \
    tree \
    htop \
    unzip \
    software-properties-common

# Upgrade pip and install wheel
echo "🐍 Upgrading pip and setuptools..."
python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "📚 Installing Python packages for Azure AI Foundry Workshop..."
pip install -r requirements.txt
echo "✅ Installed packages from requirements.txt"

# Install Azure CLI extensions
echo "☁️  Installing Azure CLI extensions..."
az extension add --name ml --yes 2>/dev/null || echo "Azure ML extension already installed"
az extension add --name ai-examples --yes 2>/dev/null || echo "AI Examples extension installation skipped"


# Print completion message
echo ""
echo "✅ Azure AI Foundry Workshop DevContainer setup completed!"
echo ""
echo "🎯 Next Steps:"
echo "  Run 'bash deploy/deploy.sh' to deploy the workshop resources."
echo ""
echo "📚 Workshop Materials:"
echo "  - Documentation: docs/"
echo "  - Sample Notebooks: notebooks/" 
echo ""
echo "🚀 Happy learning with Azure AI Foundry!"
echo ""