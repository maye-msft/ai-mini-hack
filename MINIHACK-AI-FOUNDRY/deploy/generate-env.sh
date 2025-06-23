#!/bin/bash

# Azure AI Foundry Workshop - Generate .env file from deployed resources
# This script retrieves information from deployed resources and generates a .env file

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}🔧 Generating .env file from deployed resources${NC}"
echo "================================================"
echo ""

# Prompt for resource group
read -p "Enter your resource group name: " RESOURCE_GROUP_NAME

if [ -z "$RESOURCE_GROUP_NAME" ]; then
    echo -e "${RED}❌ Resource group name is required${NC}"
    exit 1
fi

echo -e "${BLUE}🔍 Searching for resources in resource group: $RESOURCE_GROUP_NAME${NC}"

# Check if resource group exists
if ! az group show --name "$RESOURCE_GROUP_NAME" >/dev/null 2>&1; then
    echo -e "${RED}❌ Resource group '$RESOURCE_GROUP_NAME' not found${NC}"
    exit 1
fi

# Find AI Foundry (AI Services) resource
echo -e "${BLUE}🔍 Finding AI Foundry resource...${NC}"
AI_FOUNDRY_NAME=$(az cognitiveservices account list \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --query "[?kind=='AIServices'].name" \
    --output tsv | head -1)

if [ -z "$AI_FOUNDRY_NAME" ]; then
    echo -e "${RED}❌ No AI Foundry (AIServices) resource found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found AI Foundry: $AI_FOUNDRY_NAME${NC}"

# Get AI Foundry endpoint and key
AI_FOUNDRY_ENDPOINT=$(az cognitiveservices account show \
    --name "$AI_FOUNDRY_NAME" \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --query 'properties.endpoint' \
    --output tsv)

AI_FOUNDRY_KEY=$(az cognitiveservices account keys list \
    --name "$AI_FOUNDRY_NAME" \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --query 'key1' \
    --output tsv)

# Find AI Project name (should be {ai-foundry-name}-proj)
echo -e "${BLUE}🔍 Finding AI Project...${NC}"
AI_PROJECT_NAME="${AI_FOUNDRY_NAME}-proj"

# Generate AI Project endpoint using proper API format
# Format: https://{ai-foundry-name}.services.ai.azure.com/api/projects/{project-name}
AIPROJECT_ENDPOINT="https://${AI_FOUNDRY_NAME}.services.ai.azure.com/api/projects/${AI_PROJECT_NAME}"
echo -e "${GREEN}✅ Generated AI Project endpoint${NC}"

# Find Search service
echo -e "${BLUE}🔍 Finding Search service...${NC}"
SEARCH_SERVICE_NAME=$(az search service list \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --query "[].name" \
    --output tsv | head -1)

if [ -n "$SEARCH_SERVICE_NAME" ]; then
    echo -e "${GREEN}✅ Found Search service: $SEARCH_SERVICE_NAME${NC}"
    
    SEARCH_ENDPOINT="https://${SEARCH_SERVICE_NAME}.search.windows.net"
    SEARCH_KEY=$(az search admin-key show \
        --service-name "$SEARCH_SERVICE_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --query 'primaryKey' \
        --output tsv)
else
    echo -e "${YELLOW}⚠️  No Search service found${NC}"
    SEARCH_ENDPOINT="your_search_endpoint"
    SEARCH_KEY="your_search_key"
fi

# Find Application Insights
echo -e "${BLUE}🔍 Finding Application Insights...${NC}"
APP_INSIGHTS_NAME=$(az resource list \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --resource-type "Microsoft.Insights/components" \
    --query "[].name" \
    --output tsv | head -1)

if [ -n "$APP_INSIGHTS_NAME" ]; then
    echo -e "${GREEN}✅ Found Application Insights: $APP_INSIGHTS_NAME${NC}"
    
    APP_INSIGHTS_CONNECTION=$(az resource show \
        --name "$APP_INSIGHTS_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --resource-type "Microsoft.Insights/components" \
        --query "properties.ConnectionString" \
        --output tsv)
else
    echo -e "${YELLOW}⚠️  No Application Insights found${NC}"
    APP_INSIGHTS_CONNECTION="your_monitor_connection_string"
fi

# Get subscription and tenant info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

# Generate .env file
echo ""
echo -e "${BLUE}⚙️  Generating .env file...${NC}"

# Navigate to workshop root
WORKSHOP_ROOT="$(dirname "$(dirname "$0")")"
cd "$WORKSHOP_ROOT"
echo -e "${BLUE}📂 Working in directory: $(pwd)${NC}"

# Remove existing .env file if it exists
if [ -f ".env" ]; then
    rm -f ".env"
    echo -e "${BLUE}🗑️  Removed existing .env file${NC}"
fi

cat > .env << EOF
# Azure AI Foundry Workshop Configuration
# Generated automatically from deployed resources

# ====================================
# Azure Subscription and Tenant Information
# ====================================
SUBSCRIPTION_ID=$SUBSCRIPTION_ID
TENANT_ID=$TENANT_ID

# ====================================
# Azure AI Foundry Project Configuration
# ====================================
AIPROJECT_ENDPOINT=$AIPROJECT_ENDPOINT

# ====================================
# Azure AI Foundry Configuration
# ====================================
AZURE_OPENAI_ENDPOINT=$AI_FOUNDRY_ENDPOINT
AZURE_OPENAI_KEY=$AI_FOUNDRY_KEY

# Model deployment names
MODEL_DEPLOYMENT_NAME=gpt-4o
EMBEDDING_MODEL_DEPLOYMENT_NAME=text-embedding-ada-002
CHAT_MODEL=gpt-4o
EVALUATION_MODEL=gpt-4o

# ====================================
# Azure AI Search Configuration
# ====================================
AZURE_SEARCH_ENDPOINT=$SEARCH_ENDPOINT
AZURE_SEARCH_KEY=$SEARCH_KEY
AZURE_SEARCH_INDEX_NAME=rag-mini-wikipedia

# ====================================
# Monitoring and Observability
# ====================================
AZURE_MONITOR_CONNECTION_STRING=$APP_INSIGHTS_CONNECTION

# Logging configuration
LOG_LEVEL=INFO
ENABLE_TRACING=true

# ====================================
# Evaluation Configuration
# ====================================
ENABLE_DETAILED_EVALUATION=true
EVALUATION_BATCH_SIZE=10

# ====================================
# Workshop Settings
# ====================================
WORKSHOP_NAME=Azure AI Foundry Workshop
WORKSHOP_VERSION=1.0.0

# ====================================
# Resource Names (for reference)
# ====================================
AI_FOUNDRY_NAME=$AI_FOUNDRY_NAME
SEARCH_SERVICE_NAME=$SEARCH_SERVICE_NAME
APPINSIGHTS_NAME=$APP_INSIGHTS_NAME
EOF

# Verify .env file was created
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env file created successfully at $(pwd)/.env${NC}"
    echo -e "${BLUE}📄 File size: $(du -h .env | cut -f1)${NC}"
else
    echo -e "${RED}❌ Failed to create .env file${NC}"
    exit 1
fi

# Display summary
echo ""
echo -e "${BOLD}${GREEN}🎉 Environment Configuration Complete!${NC}"
echo "=================================="
echo ""
echo -e "${BLUE}📋 Configuration Summary:${NC}"
echo "   AI Foundry: $AI_FOUNDRY_NAME"
echo "   AI Project: $AI_PROJECT_NAME"
echo "   Project Endpoint: $AIPROJECT_ENDPOINT"
echo "   OpenAI Endpoint: $AI_FOUNDRY_ENDPOINT"
echo "   Search Service: ${SEARCH_SERVICE_NAME:-'Not found'}"
echo "   Application Insights: ${APP_INSIGHTS_NAME:-'Not found'}"
echo ""
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "   1. Run: bash scripts/test-environment.sh"
echo "   2. Start exploring the workshop notebooks"
echo ""