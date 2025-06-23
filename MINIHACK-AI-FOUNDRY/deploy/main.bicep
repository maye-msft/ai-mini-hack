@description('The name of the Azure AI Foundry service')
param aiFoundryName string = 'aifoundry'

@description('The location for all resources')
param location string = resourceGroup().location

@description('The SKU for the Azure AI Search service')
@allowed(['free', 'basic', 'standard', 'standard2', 'standard3', 'storage_optimized_l1', 'storage_optimized_l2'])
param searchSku string = 'basic'

@description('The chat model deployment name')
param chatModelName string = 'gpt-4o'

@description('The embedding model deployment name')
param embeddingModelName string = 'text-embedding-ada-002'

@description('The chat model version')
param chatModelVersion string = '2024-08-06'

@description('The embedding model version')
param embeddingModelVersion string = '2'

// Generate unique suffix from timestamp for better randomness
@secure()
param deploymentTimestamp string = utcNow()

var timestampSuffix = take(uniqueString(deploymentTimestamp), 8)
// Generate a different suffix for Key Vault to avoid naming conflicts
var kvUniqueSuffix = take(uniqueString(deploymentTimestamp, deployment().name), 8)

// Use consistent naming pattern - aiFoundryName already includes random suffix from deploy script
var actualAiFoundryName = '${aiFoundryName}-${timestampSuffix}'
var aiProjectName = '${actualAiFoundryName}-proj'
// Make search service use the same pattern as AI Foundry for consistency
var searchServiceName = 'search-${timestampSuffix}'
var appInsightsName = 'insights-${timestampSuffix}'
var keyVaultName = 'kv-${kvUniqueSuffix}'
var storageAccountName = 'storage${timestampSuffix}'

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Flow_Type: 'Bluefield'
    Request_Source: 'rest'
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: []
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    defaultToOAuthAuthentication: false
    allowCrossTenantReplication: false
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    networkAcls: {
      bypass: 'AzureServices'
      virtualNetworkRules: []
      ipRules: []
      defaultAction: 'Allow'
    }
    supportsHttpsTrafficOnly: true
    encryption: {
      services: {
        file: {
          keyType: 'Account'
          enabled: true
        }
        blob: {
          keyType: 'Account'
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
    accessTier: 'Hot'
  }
}

// Azure AI Foundry (replaces separate OpenAI service and AI Hub)
resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: actualAiFoundryName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    allowProjectManagement: true
    customSubDomainName: actualAiFoundryName
    disableLocalAuth: false
  }
}

// Azure AI Project
resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  name: aiProjectName
  parent: aiFoundry
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

// Chat Model Deployment
resource chatModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aiFoundry
  name: chatModelName
  sku: {
    capacity: 10
    name: 'GlobalStandard'
  }
  properties: {
    model: {
      name: chatModelName
      format: 'OpenAI'
      version: chatModelVersion
    }
  }
}

// Embedding Model Deployment
resource embeddingModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aiFoundry
  name: embeddingModelName
  sku: {
    capacity: 10
    name: 'GlobalStandard'
  }
  properties: {
    model: {
      name: embeddingModelName
      format: 'OpenAI'
      version: embeddingModelVersion
    }
  }
  dependsOn: [
    chatModelDeployment
  ]
}

// Azure AI Search Service
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  sku: {
    name: searchSku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    disableLocalAuth: false
    authOptions: {
      apiKeyOnly: {}
    }
  }
}

// Role assignments for AI Project to access resources
resource aiProjectSearchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: searchService
  name: guid(aiProject.id, searchService.id, 'Search Index Data Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7') // Search Index Data Contributor
    principalId: aiProject.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs for environment configuration (non-sensitive only)
output aiFoundryEndpoint string = aiFoundry.properties.endpoint
output aiFoundryName string = actualAiFoundryName
output aiProjectName string = aiProjectName
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output resourceGroupName string = resourceGroup().name
output searchServiceName string = searchServiceName
output appInsightsName string = appInsightsName
output keyVaultName string = keyVaultName
output storageAccountName string = storageAccountName
