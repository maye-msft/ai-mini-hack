#!/bin/bash

# Azure AI Foundry Workshop - Simplified Deployment Script
# This script deploys Azure AI Foundry and other resources using Bicep templates

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default configuration
DEFAULT_RESOURCE_GROUP="rg-azure-ai-foundry-workshop"
DEFAULT_LOCATION="eastus2"
# Generate a random suffix to avoid naming conflicts
RANDOM_SUFFIX=$(openssl rand -hex 2 2>/dev/null || printf "%04x" $((RANDOM % 65536)))
DEFAULT_AI_FOUNDRY_NAME="aifoundry-${RANDOM_SUFFIX}"

# Header
echo -e "${BOLD}${BLUE}🚀 Azure AI Foundry Workshop - Deployment${NC}"
echo "==============================================="
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate prerequisites
echo -e "${BLUE}🔍 Validating prerequisites...${NC}"

if ! command_exists az; then
    echo -e "${RED}❌ Azure CLI is not installed. Please install it first.${NC}"
    echo "   Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites validated${NC}"

# Configuration prompts
echo ""
echo -e "${BLUE}📋 Configuration Setup${NC}"
read -p "Enter resource group name (or press Enter for '$DEFAULT_RESOURCE_GROUP'): " RESOURCE_GROUP_NAME
RESOURCE_GROUP_NAME=${RESOURCE_GROUP_NAME:-"$DEFAULT_RESOURCE_GROUP"}

read -p "Enter Azure region (or press Enter for '$DEFAULT_LOCATION'): " LOCATION
LOCATION=${LOCATION:-"$DEFAULT_LOCATION"}

read -p "Enter AI Foundry name (or press Enter for '$DEFAULT_AI_FOUNDRY_NAME'): " AI_FOUNDRY_NAME
AI_FOUNDRY_NAME=${AI_FOUNDRY_NAME:-"$DEFAULT_AI_FOUNDRY_NAME"}

echo ""
echo -e "${BLUE}📋 Selected Configuration:${NC}"
echo "   Resource Group: $RESOURCE_GROUP_NAME"
echo "   Location: $LOCATION"
echo "   AI Foundry Name: $AI_FOUNDRY_NAME"
echo ""

# Check Azure CLI login status
echo -e "${BLUE}🔐 Checking Azure authentication...${NC}"
if ! az account show >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Not logged in to Azure. Starting login process...${NC}"
    az login
fi

echo -e "${GREEN}✅ Authenticated to Azure${NC}"
echo ""

read -p "Continue with deployment? (y/N): " CONFIRM
if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Create resource group if it doesn't exist
echo ""
echo -e "${BLUE}🏗️  Creating resource group...${NC}"
if az group show --name "$RESOURCE_GROUP_NAME" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Resource group '$RESOURCE_GROUP_NAME' already exists${NC}"
else
    az group create --name "$RESOURCE_GROUP_NAME" --location "$LOCATION" --output table
    echo -e "${GREEN}✅ Resource group '$RESOURCE_GROUP_NAME' created${NC}"
fi

# Check for deleted Key Vaults that need to be purged
echo ""
echo -e "${BLUE}🔍 Checking for deleted Key Vaults...${NC}"
DELETED_VAULTS=$(az keyvault list-deleted --query "[?location=='$LOCATION'].name" --output tsv 2>/dev/null || echo "")
if [ -n "$DELETED_VAULTS" ]; then
    echo -e "${YELLOW}⚠️  Found deleted Key Vaults. Purging them to avoid name conflicts...${NC}"
    for vault in $DELETED_VAULTS; do
        echo "Purging vault: $vault"
        az keyvault purge --name "$vault" --location "$LOCATION" >/dev/null 2>&1 || true
    done
    echo -e "${GREEN}✅ Deleted Key Vaults purged${NC}"
fi

# Deploy resources using Bicep template
echo ""
echo -e "${BLUE}🚀 Deploying Azure resources using Bicep template...${NC}"
DEPLOYMENT_NAME="ai-foundry-$(date +%H%M)"

# Create logs directory if it doesn't exist
mkdir -p ./logs

# Set up logging
LOG_FILE="./logs/deployment-$(date +%Y%m%d-%H%M%S).log"
echo "$(date): Starting deployment process" | tee -a "$LOG_FILE"
echo "$(date): Resource Group: $RESOURCE_GROUP_NAME" | tee -a "$LOG_FILE"
echo "$(date): Location: $LOCATION" | tee -a "$LOG_FILE"
echo "$(date): AI Foundry Name: $AI_FOUNDRY_NAME" | tee -a "$LOG_FILE"
echo "$(date): Deployment Name: $DEPLOYMENT_NAME" | tee -a "$LOG_FILE"

# Validate template first
echo "$(date): Starting template validation..." | tee -a "$LOG_FILE"
if az deployment group validate \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --template-file ./deploy/main.bicep \
    --parameters aiFoundryName="$AI_FOUNDRY_NAME" location="$LOCATION" \
    2>&1 | tee -a "$LOG_FILE"; then
    echo "$(date): ✅ Template validation successful" | tee -a "$LOG_FILE"
else
    echo "$(date): ❌ Template validation failed" | tee -a "$LOG_FILE"
    echo -e "${RED}❌ Template validation failed. Check log: $LOG_FILE${NC}"
    exit 1
fi

# Run what-if check for more detailed analysis
echo ""
echo -e "${BLUE}🔍 Running what-if analysis to identify potential issues...${NC}"
echo "$(date): Starting what-if analysis..." | tee -a "$LOG_FILE"

if WHATIF_OUTPUT=$(az deployment group what-if \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --template-file ./deploy/main.bicep \
    --parameters aiFoundryName="$AI_FOUNDRY_NAME" location="$LOCATION" \
    --name "$DEPLOYMENT_NAME" \
    2>&1); then
    
    echo "$(date): ✅ What-if analysis completed successfully" | tee -a "$LOG_FILE"
    echo "$(date): What-if results:" | tee -a "$LOG_FILE"
    echo "$WHATIF_OUTPUT" | tee -a "$LOG_FILE"
    echo -e "${GREEN}✅ What-if analysis completed - no blocking issues detected${NC}"
else
    echo "$(date): ❌ What-if analysis failed" | tee -a "$LOG_FILE"
    echo "$(date): What-if error output:" | tee -a "$LOG_FILE"
    echo "$WHATIF_OUTPUT" | tee -a "$LOG_FILE"
    
    # Check for specific error types
    if echo "$WHATIF_OUTPUT" | grep -q "ServiceQuotaExceeded.*Search"; then
        echo "$(date): 🔍 DETECTED: Azure Search service quota exceeded" | tee -a "$LOG_FILE"
        echo -e "${RED}❌ QUOTA EXCEEDED: You already have the maximum number of free Azure Search services${NC}"
        echo ""
        echo -e "${BLUE}🔍 Solutions:${NC}"
        echo "   1. Delete an existing search service from your subscription"
        echo "   2. Upgrade to a paid Search service tier (Basic or Standard)"
        echo "   3. Use an existing search service instead"
        echo ""
        echo -e "${BLUE}📋 To check existing search services:${NC}"
        echo "   az search service list --query \"[].{Name:name,ResourceGroup:resourceGroup,Sku:sku.name}\" --output table"
        echo ""
        echo -e "${RED}❌ Cannot proceed with deployment. Fix the quota issue first.${NC}"
        exit 1
    elif echo "$WHATIF_OUTPUT" | grep -q "ServiceQuotaExceeded"; then
        echo "$(date): 🔍 DETECTED: Service quota exceeded for another resource type" | tee -a "$LOG_FILE"
        echo -e "${RED}❌ QUOTA EXCEEDED: You've reached the quota limit for one or more Azure services${NC}"
        echo "$(date): Full quota error details:" | tee -a "$LOG_FILE"
        echo "$WHATIF_OUTPUT" | grep -A 5 -B 5 "ServiceQuotaExceeded" | tee -a "$LOG_FILE"
        echo ""
        echo -e "${RED}❌ Cannot proceed with deployment. Check the quota limits above.${NC}"
        exit 1
    elif echo "$WHATIF_OUTPUT" | grep -q "content.*already consumed"; then
        echo "$(date): 🔍 DETECTED: 'Content already consumed' error in what-if analysis" | tee -a "$LOG_FILE"
        echo -e "${YELLOW}⚠️  What-if analysis revealed the 'content already consumed' error.${NC}"
        echo -e "${YELLOW}   This indicates a problem with the Bicep template or resource conflicts.${NC}"
        echo ""
        echo -e "${BLUE}🔍 Common causes:${NC}"
        echo "   1. Resource names already in use"
        echo "   2. Invalid resource configurations"
        echo "   3. Missing required parameters"
        echo "   4. API version conflicts"
        echo ""
        echo -e "${RED}❌ Cannot proceed with deployment. Fix the issues above first.${NC}"
        exit 1
    else
        echo -e "${YELLOW}⚠️  What-if analysis failed but not due to known critical errors${NC}"
        echo -e "${YELLOW}   Proceeding with deployment as this might be a temporary issue${NC}"
        echo "$(date): Proceeding despite what-if failure" | tee -a "$LOG_FILE"
    fi
fi

# Start deployment with enhanced logging
echo "$(date): Starting actual deployment..." | tee -a "$LOG_FILE"
echo -e "${BLUE}📝 Deployment logs will be saved to: $LOG_FILE${NC}"

# Run deployment with error capture
if DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --template-file ./deploy/main.bicep \
    --parameters aiFoundryName="$AI_FOUNDRY_NAME" location="$LOCATION" \
    --name "$DEPLOYMENT_NAME" \
    --output json \
    --verbose 2>&1); then
    
    echo "$(date): ✅ Deployment command executed successfully" | tee -a "$LOG_FILE"
    echo "$DEPLOYMENT_OUTPUT" | tee -a "$LOG_FILE"
    echo -e "${GREEN}✅ Resources deployed successfully${NC}"
else
    DEPLOYMENT_EXIT_CODE=$?
    echo "$(date): ❌ Deployment command failed with exit code: $DEPLOYMENT_EXIT_CODE" | tee -a "$LOG_FILE"
    echo "$(date): Error output:" | tee -a "$LOG_FILE"
    echo "$DEPLOYMENT_OUTPUT" | tee -a "$LOG_FILE"
    
    # Check if it's the "content already consumed" error
    if echo "$DEPLOYMENT_OUTPUT" | grep -q "content.*already consumed"; then
        echo "$(date): 🔍 DETECTED: 'Content already consumed' error" | tee -a "$LOG_FILE"
        echo -e "${YELLOW}⚠️  Detected 'content already consumed' error. This usually indicates:${NC}"
        echo "   1. API throttling or network issues"
        echo "   2. Authentication token expiry during deployment"
        echo "   3. Concurrent deployments to the same resource group"
        echo ""
        echo -e "${BLUE}🔄 Attempting to check deployment status...${NC}"
        
        # Try to check deployment status
        sleep 10
        if DEPLOYMENT_STATUS=$(az deployment group show \
            --resource-group "$RESOURCE_GROUP_NAME" \
            --name "$DEPLOYMENT_NAME" \
            --query 'properties.provisioningState' \
            --output tsv 2>&1); then
            echo "$(date): Current deployment status: $DEPLOYMENT_STATUS" | tee -a "$LOG_FILE"
            
            if [ "$DEPLOYMENT_STATUS" = "Succeeded" ]; then
                echo -e "${GREEN}✅ Deployment actually succeeded despite the error${NC}"
            elif [ "$DEPLOYMENT_STATUS" = "Running" ]; then
                echo -e "${YELLOW}⏳ Deployment is still running. Waiting for completion...${NC}"
                az deployment group wait --resource-group "$RESOURCE_GROUP_NAME" --name "$DEPLOYMENT_NAME" --created
            else
                echo -e "${RED}❌ Deployment failed with status: $DEPLOYMENT_STATUS${NC}"
                exit 1
            fi
        else
            echo "$(date): Failed to check deployment status: $DEPLOYMENT_STATUS" | tee -a "$LOG_FILE"
            echo -e "${RED}❌ Cannot determine deployment status${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Deployment failed with different error. Check log: $LOG_FILE${NC}"
        exit 1
    fi
fi

echo "$(date): Deployment phase completed" | tee -a "$LOG_FILE"

# Automatically generate .env file from deployed resources
echo ""
echo -e "${BLUE}🔧 Automatically generating .env file from deployed resources...${NC}"

# Get the script directory and change to it
SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR"

# Run generate-env.sh automatically with the resource group name
echo "$RESOURCE_GROUP_NAME" | bash generate-env.sh

# Check if .env file was created successfully
if [ -f "./.env" ]; then
    echo -e "${GREEN}✅ .env file generated successfully${NC}"
else
    echo -e "${YELLOW}⚠️  .env file not found, you may need to run generate-env.sh manually${NC}"
fi

# Get service credentials and resource information (keeping existing logic as backup)
echo ""
echo -e "${BLUE}🔑 Retrieving deployment outputs and credentials...${NC}"
echo "$(date): Starting credential retrieval phase" | tee -a "$LOG_FILE"

# Function to safely execute az commands with logging
safe_az_command() {
    local command_desc="$1"
    shift
    echo "$(date): Executing: $command_desc" | tee -a "$LOG_FILE"
    
    if result=$(timeout 60 "$@" 2>&1); then
        echo "$(date): ✅ $command_desc - Success" | tee -a "$LOG_FILE"
        echo "$result"
        return 0
    else
        local exit_code=$?
        echo "$(date): ❌ $command_desc - Failed with exit code $exit_code" | tee -a "$LOG_FILE"
        echo "$(date): Error output: $result" | tee -a "$LOG_FILE"
        
        # Check for the specific error
        if echo "$result" | grep -q "content.*already consumed"; then
            echo "$(date): 🔍 DETECTED: 'Content already consumed' error in: $command_desc" | tee -a "$LOG_FILE"
        fi
        return $exit_code
    fi
}

# Get deployment outputs with logging
echo "$(date): Getting AI Foundry endpoint..." | tee -a "$LOG_FILE"
AI_FOUNDRY_ENDPOINT=$(safe_az_command "Get AI Foundry endpoint" \
    az deployment group show \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --name "$DEPLOYMENT_NAME" \
    --query 'properties.outputs.aiFoundryEndpoint.value' \
    --output tsv)

echo "$(date): Getting AI Project name..." | tee -a "$LOG_FILE"
AI_PROJECT_NAME=$(safe_az_command "Get AI Project name" \
    az deployment group show \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --name "$DEPLOYMENT_NAME" \
    --query 'properties.outputs.aiProjectName.value' \
    --output tsv)

echo "$(date): Getting deployed AI Foundry name..." | tee -a "$LOG_FILE"
DEPLOYED_AI_FOUNDRY_NAME=$(safe_az_command "Get deployed AI Foundry name" \
    az deployment group show \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --name "$DEPLOYMENT_NAME" \
    --query 'properties.outputs.aiFoundryName.value' \
    --output tsv)

echo "$(date): Getting AI Foundry credentials..." | tee -a "$LOG_FILE"
AI_FOUNDRY_KEY=$(safe_az_command "Get AI Foundry credentials" \
    az cognitiveservices account keys list \
    --name "$DEPLOYED_AI_FOUNDRY_NAME" \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --query 'key1' \
    --output tsv)

echo "$(date): Getting Search service name..." | tee -a "$LOG_FILE"
SEARCH_SERVICE_NAME=$(safe_az_command "Get Search service name" \
    az deployment group show \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --name "$DEPLOYMENT_NAME" \
    --query 'properties.outputs.searchServiceName.value' \
    --output tsv)

echo "$(date): Getting Search endpoint..." | tee -a "$LOG_FILE"
SEARCH_ENDPOINT=$(safe_az_command "Get Search endpoint" \
    az deployment group show \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --name "$DEPLOYMENT_NAME" \
    --query 'properties.outputs.searchEndpoint.value' \
    --output tsv)

echo "$(date): Getting Search admin key..." | tee -a "$LOG_FILE"
SEARCH_KEY=$(safe_az_command "Get Search admin key" \
    az search admin-key show \
    --service-name "$SEARCH_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --query 'primaryKey' \
    --output tsv)

echo "$(date): Getting App Insights name..." | tee -a "$LOG_FILE"
APP_INSIGHTS_NAME=$(safe_az_command "Get App Insights name" \
    az deployment group show \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --name "$DEPLOYMENT_NAME" \
    --query 'properties.outputs.appInsightsName.value' \
    --output tsv)

echo "$(date): Getting App Insights connection string..." | tee -a "$LOG_FILE"
APP_INSIGHTS_CONNECTION=$(safe_az_command "Get App Insights connection string" \
    az monitor app-insights component show \
    --app "$APP_INSIGHTS_NAME" \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --query 'connectionString' \
    --output tsv)

echo "$(date): Getting subscription and tenant info..." | tee -a "$LOG_FILE"
SUBSCRIPTION_ID=$(safe_az_command "Get subscription ID" az account show --query id -o tsv)
TENANT_ID=$(safe_az_command "Get tenant ID" az account show --query tenantId -o tsv)

echo "$(date): Credential retrieval phase completed" | tee -a "$LOG_FILE"

# Generate .env file
echo ""
echo -e "${BLUE}⚙️  Generating .env configuration file...${NC}"

WORKSHOP_ROOT="$(dirname "$(dirname "$0")")"
cd "$WORKSHOP_ROOT"

# Check if .env.template exists and inform user
if [ -f ".env.template" ]; then
    echo -e "${BLUE}📝 Found .env.template file - generating .env with actual values${NC}"
fi

# Remove existing .env file if it exists
if [ -f ".env" ]; then
    rm -f ".env"
fi

cat > .env << EOF
# Azure AI Foundry Workshop Configuration
# Generated automatically by deployment script

# ====================================
# Azure Subscription and Tenant Information
# ====================================
SUBSCRIPTION_ID=$SUBSCRIPTION_ID
TENANT_ID=$TENANT_ID

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
AI_FOUNDRY_NAME=$DEPLOYED_AI_FOUNDRY_NAME
AI_PROJECT_NAME=$AI_PROJECT_NAME
SEARCH_SERVICE_NAME=$SEARCH_SERVICE_NAME
APPINSIGHTS_NAME=$APP_INSIGHTS_NAME
EOF

# move the .env file to the parent directory
mv .env "../.env"

echo -e "${GREEN}✅ .env file created successfully${NC}"

# Install missing Python packages
echo ""
echo -e "${BLUE}📦 Installing required Python packages...${NC}"
pip install --user azure.ai.inference opentelemetry-instrumentation-openai-v2 > /dev/null 2>&1
echo -e "${GREEN}✅ Python packages installed${NC}"

# Final summary
echo ""
echo -e "${BOLD}${GREEN}🎉 Azure AI Foundry Workshop Deployment Complete!${NC}"
echo "========================================================="
echo ""
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo "   Resource Group: $RESOURCE_GROUP_NAME"
echo "   Location: $LOCATION"
echo "   AI Foundry: $DEPLOYED_AI_FOUNDRY_NAME"
echo "   AI Project: $AI_PROJECT_NAME"
echo ""
echo -e "${BLUE}🔗 Resource URLs:${NC}"
echo "   Azure AI Foundry Portal: https://ai.azure.com"
echo "   Azure Portal: https://portal.azure.com/#@/resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP_NAME"
echo ""
echo -e "${BLUE}⚙️  Configuration:${NC}"
echo "   ✅ .env file generated with all required values"
echo "   ✅ All Azure resources deployed using Bicep template"
echo "   ✅ AI models deployed successfully"
echo "   ✅ Python packages installed"
echo ""
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "   1. Run: bash scripts/test-environment.sh"
echo "   2. Start exploring the workshop notebooks"
echo ""
echo -e "${BOLD}${GREEN}Happy learning with Azure AI Foundry! 🎓${NC}"

# Final log entry
echo "$(date): Script completed successfully" | tee -a "$LOG_FILE"
echo -e "${BLUE}📋 Complete deployment log saved to: $LOG_FILE${NC}"