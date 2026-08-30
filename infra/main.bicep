// ============================================================================
// Intelligent Knowledge Hub - Infrastructure as Code (IaC)
// Declarative Azure Bicep Template
// Provisions: Linux App Service (B1), Azure AI Search, Azure OpenAI, Storage, and Zero-Trust RBAC
// ============================================================================

targetScope = 'resourceGroup'

@description('Azure Region for resource deployment')
param location string = resourceGroup().location

@description('Base prefix for all provisioned resource names')
@minLength(3)
@maxLength(50)
param appName string = 'intelligent-knowledge-hub'

@description('Unique suffix for globally unique resources (Storage, Search, OpenAI)')
@minLength(3)
@maxLength(13)
param uniqueSuffix string = uniqueString(resourceGroup().id)

@description('App Service Plan Linux SKU')
@allowed([
  'B1'
  'B2'
  'S1'
  'P1v3'
])
param appServicePlanSku string = 'B1'

@description('Azure AI Search Service SKU')
@allowed([
  'free'
  'basic'
  'standard'
])
param searchSku string = 'basic'

@description('Azure OpenAI embedding model deployment name')
param embeddingDeploymentName string = 'text-embedding-3-small'

@description('Azure OpenAI chat model deployment name')
param chatDeploymentName string = 'gpt-5.4-mini'

// ----------------------------------------------------------------------------
// Resource Names
// ----------------------------------------------------------------------------
var storageAccountName = take(toLower('sa${replace(appName, '-', '')}${uniqueSuffix}'), 24)
var appServicePlanName = 'asp-${appName}'
var webAppName = appName
var searchServiceName = take('search-${appName}-${uniqueSuffix}', 60)
var openAiServiceName = take('openai-${appName}-${uniqueSuffix}', 64)
var storageContainerName = 'kb-documents'

// ----------------------------------------------------------------------------
// 1. Storage Account & Blob Container for Document Ingestion
// ----------------------------------------------------------------------------
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
    encryption: {
      services: {
        blob: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: storageContainerName
  properties: {
    publicAccess: 'None'
  }
}

// ----------------------------------------------------------------------------
// 2. Azure AI Search Service (Hybrid BM25 + Vector Search with HNSW / RRF)
// ----------------------------------------------------------------------------
resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: location
  sku: {
    name: searchSku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    semanticSearch: 'free'
  }
}

// ----------------------------------------------------------------------------
// 3. Azure OpenAI Service (Embeddings + Chat Completion Models)
// ----------------------------------------------------------------------------
resource openAiService 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: openAiServiceName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAiServiceName
    publicNetworkAccess: 'Enabled'
    apiProperties: {}
  }
}

// Embedding Model Deployment: text-embedding-3-small
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAiService
  name: embeddingDeploymentName
  sku: {
    name: 'Standard'
    capacity: 20
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
  }
}

// Chat Model Deployment: gpt-5.4-mini (or gpt-4o-mini fallback)
resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAiService
  name: chatDeploymentName
  dependsOn: [
    embeddingDeployment
  ]
  sku: {
    name: 'Standard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
  }
}

// ----------------------------------------------------------------------------
// 4. Linux App Service Plan (Cost-Efficient B1 Tier)
// ----------------------------------------------------------------------------
resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: appServicePlanSku
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true // Required for Linux
  }
}

// ----------------------------------------------------------------------------
// 5. Azure Linux App Service Web Application with System-Assigned Identity
// ----------------------------------------------------------------------------
resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appCommandLine: 'gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app'
      alwaysOn: true
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'AZURE_SEARCH_ENDPOINT'
          value: 'https://${searchService.name}.search.windows.net'
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: openAiService.properties.endpoint
        }
        {
          name: 'STORAGE_ACCOUNT_NAME'
          value: storageAccount.name
        }
        {
          name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
          value: embeddingDeploymentName
        }
        {
          name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
          value: chatDeploymentName
        }
        {
          name: 'AZURE_SEARCH_INDEX_NAME'
          value: 'kb-index'
        }
      ]
    }
  }
}

// ----------------------------------------------------------------------------
// 6. Zero-Trust RBAC Role Assignments (Managed Identity Principal)
// ----------------------------------------------------------------------------

// Cognitive Services OpenAI User (5e070341-92c5-408a-b8cb-472ef07cf275)
resource openAiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAiService.id, webApp.id, 'Cognitive Services OpenAI User')
  scope: openAiService
  properties: {
    principalId: webApp.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e070341-92c5-408a-b8cb-472ef07cf275')
    principalType: 'ServicePrincipal'
  }
}

// Search Index Data Reader (1407120a-a4aa-4278-889e-ab203207142b)
resource searchDataReaderAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, webApp.id, 'Search Index Data Reader')
  scope: searchService
  properties: {
    principalId: webApp.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '1407120a-a4aa-4278-889e-ab203207142b')
    principalType: 'ServicePrincipal'
  }
}

// Storage Blob Data Reader (2a2b9908-6ea1-4ae2-8e65-a410df84e7d1)
resource storageBlobDataReaderAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, webApp.id, 'Storage Blob Data Reader')
  scope: storageAccount
  properties: {
    principalId: webApp.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1')
    principalType: 'ServicePrincipal'
  }
}

// ----------------------------------------------------------------------------
// Outputs
// ----------------------------------------------------------------------------
output webAppUrl string = 'https://${webApp.properties.defaultHostName}'
output webAppPrincipalId string = webApp.identity.principalId
output openAiEndpoint string = openAiService.properties.endpoint
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output storageAccountNameOutput string = storageAccount.name
