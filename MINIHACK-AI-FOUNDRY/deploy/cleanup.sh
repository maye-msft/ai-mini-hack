#!/bin/bash

# Azure AI Foundry Workshop Cleanup Script
# This script removes all Azure resources created for the workshop

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}🗑️  Azure AI Foundry Workshop Cleanup${NC}"
echo "============================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate prerequisites
echo -e "${BLUE}🔍 Validating prerequisites...${NC}"

if ! command_exists az; then
    echo -e "${RED}❌ Azure CLI is not installed.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites validated${NC}"

# Check Azure CLI login status
echo -e "${BLUE}🔐 Checking Azure authentication...${NC}"
if ! az account show >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Not logged in to Azure. Please login first.${NC}"
    az login
fi

# Get current subscription info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
echo -e "${GREEN}✅ Authenticated to Azure${NC}"
echo "   Subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)"

# List resource groups that might contain workshop resources
echo ""
echo -e "${BLUE}📋 Finding workshop resource groups...${NC}"

# Look for resource groups that might be related to the workshop
RESOURCE_GROUPS=$(az group list --query "[?contains(name, 'azure-ai-foundry') || contains(name, 'aiworkshop') || contains(name, 'rg-azure-ai-foundry-workshop') || contains(name, 'aifoundry')].name" -o tsv)

if [ -z "$RESOURCE_GROUPS" ]; then
    echo -e "${YELLOW}⚠️  No workshop resource groups found with common naming patterns.${NC}"
    echo "   Please specify the resource group name manually."
    read -p "Enter the resource group name to delete: " RESOURCE_GROUP_NAME
    
    if [ -z "$RESOURCE_GROUP_NAME" ]; then
        echo "No resource group specified. Exiting."
        exit 0
    fi
    
    RESOURCE_GROUPS="$RESOURCE_GROUP_NAME"
fi

echo -e "${BLUE}📋 Found the following resource groups:${NC}"
echo "$RESOURCE_GROUPS" | while read -r rg; do
    echo "   • $rg"
done

echo ""
echo -e "${RED}⚠️  WARNING: This will permanently delete all resources in the selected resource group(s)!${NC}"
echo -e "${RED}   This action cannot be undone.${NC}"
echo ""

# If multiple resource groups found, let user choose
RESOURCE_GROUP_ARRAY=($RESOURCE_GROUPS)
if [ ${#RESOURCE_GROUP_ARRAY[@]} -gt 1 ]; then
    echo "Multiple resource groups found. Please select:"
    for i in "${!RESOURCE_GROUP_ARRAY[@]}"; do
        echo "   $((i+1)). ${RESOURCE_GROUP_ARRAY[$i]}"
    done
    echo "   0. Delete all workshop resource groups"
    echo "   q. Quit without deleting anything"
    echo ""
    
    read -p "Enter your choice: " CHOICE
    
    if [[ "$CHOICE" == "q" || "$CHOICE" == "Q" ]]; then
        echo "Cleanup cancelled."
        exit 0
    elif [[ "$CHOICE" == "0" ]]; then
        # Delete all
        SELECTED_GROUPS="$RESOURCE_GROUPS"
    elif [[ "$CHOICE" =~ ^[0-9]+$ ]] && [ "$CHOICE" -ge 1 ] && [ "$CHOICE" -le ${#RESOURCE_GROUP_ARRAY[@]} ]; then
        # Delete selected
        SELECTED_GROUPS="${RESOURCE_GROUP_ARRAY[$((CHOICE-1))]}"
    else
        echo "Invalid choice. Exiting."
        exit 1
    fi
else
    SELECTED_GROUPS="$RESOURCE_GROUPS"
fi

# Show what will be deleted
echo ""
echo -e "${RED}📋 The following resource groups will be PERMANENTLY DELETED:${NC}"
echo "$SELECTED_GROUPS" | while read -r rg; do
    echo "   • $rg"
    
    # Show resources in the group
    echo "     Resources:"
    az resource list --resource-group "$rg" --query "[].{Name:name, Type:type}" -o table | sed 's/^/       /'
    echo ""
done

# Final confirmation
echo -e "${RED}⚠️  FINAL CONFIRMATION${NC}"
echo "Type 'DELETE' to confirm permanent deletion of all selected resources:"
read -p "> " FINAL_CONFIRM

if [ "$FINAL_CONFIRM" != "DELETE" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

# Perform cleanup
echo ""
echo -e "${BLUE}🗑️  Starting cleanup process...${NC}"

echo "$SELECTED_GROUPS" | while read -r rg; do
    if [ -n "$rg" ]; then
        echo -e "${BLUE}   Deleting resource group: $rg${NC}"
        
        # Delete the resource group
        az group delete --name "$rg" --yes --no-wait
        
        echo -e "${GREEN}   ✅ Deletion initiated for: $rg${NC}"
    fi
done

echo ""
echo -e "${GREEN}🎉 Cleanup process initiated!${NC}"
echo "============================================="
echo ""
echo -e "${YELLOW}📋 Important Notes:${NC}"
echo "   • Resource deletion is running in the background"
echo "   • It may take 10-15 minutes to complete"
echo "   • You can monitor progress in the Azure Portal"
echo "   • Check: https://portal.azure.com/#blade/HubsExtension/BrowseResourceGroups"
echo ""
echo -e "${BLUE}🧹 Local Cleanup:${NC}"
echo "   • Consider removing the .env file if you're done with the workshop"
echo "   • Your local workshop files and notebooks are preserved"
echo ""
echo -e "${GREEN}Thank you for using the Azure AI Foundry Workshop! 👋${NC}"