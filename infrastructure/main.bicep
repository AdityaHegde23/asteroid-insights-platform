@description('Environment name (dev, staging, prod)')
param environment string = 'dev'

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Storage account name')
param storageAccountName string = 'asteroiddata${uniqueString(resourceGroup().id)}'

@description('SQL Server name')
param sqlServerName string = 'asteroid-sql-${environment}'

@description('SQL Database name')
param databaseName string = 'asteroid_insight'

@description('Function App name')
param functionAppName string = 'asteroid-processor-${environment}'

@description('App Service Plan name')
param appServicePlanName string = 'asteroid-plan-${environment}'

@description('Application Insights name')
param appInsightsName string = 'asteroid-insights-${environment}'

@description('Key Vault name')
param keyVaultName string = 'asteroid-kv-${environment}'

@description('SQL Server admin password')
@secure()
param sqlAdminPassword string = newGuid()

// Variables
var storageAccountSku = 'Standard_LRS'
var sqlServerAdminLogin = 'asteroidadmin'
var functionAppRuntime = 'python'

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: storageAccountSku
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
  }
}

// Blob Service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  name: 'default'
  parent: storageAccount
  properties: {
    cors: {
      corsRules: [
        {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE']
          allowedHeaders: ['*']
          exposedHeaders: ['*']
          maxAgeInSeconds: 86400
        }
      ]
    }
  }
}

// Blob Containers for raw data
resource rawDataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: 'asteroid-raw'
  parent: blobService
  properties: {
    publicAccess: 'None'
  }
}

resource processedDataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: 'asteroid-processed'
  parent: blobService
  properties: {
    publicAccess: 'None'
  }
}

resource insightsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: 'asteroid-insights'
  parent: blobService
  properties: {
    publicAccess: 'None'
  }
}

// SQL Server
resource sqlServer 'Microsoft.Sql/servers@2023-02-01-preview' = {
  name: sqlServerName
  location: location
  properties: {
    administratorLogin: sqlServerAdminLogin
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
  }
}

// SQL Database
resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-02-01-preview' = {
  name: databaseName
  parent: sqlServer
  location: location
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 2147483648 // 2GB for Basic tier
  }
}

// SQL Server Firewall Rule (allow Azure services)
resource sqlFirewallRule 'Microsoft.Sql/servers/firewallRules@2023-02-01-preview' = {
  name: 'AllowAzureServices'
  parent: sqlServer
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: ''
  }
}

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'Y1' // Consumption plan for serverless
    tier: 'Dynamic'
  }
  kind: 'functionapp'
  properties: {
    reserved: false
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(functionAppName)
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: functionAppRuntime
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'AZURE_STORAGE_CONNECTION_STRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'AZURE_SQL_CONNECTION_STRING'
          value: 'Driver={ODBC Driver 17 for SQL Server};Server=${sqlServer.properties.fullyQualifiedDomainName};Database=${databaseName};Uid=${sqlServerAdminLogin};Pwd=${sqlAdminPassword};'
        }
      ]
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
    httpsOnly: true
  }
}

// Key Vault (for storing secrets)
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// Assign Function App identity to Key Vault
resource keyVaultAccessPolicy 'Microsoft.KeyVault/vaults/accessPolicies@2023-07-01' = {
  name: 'add'
  parent: keyVault
  properties: {
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: functionApp.identity.principalId
        permissions: {
          secrets: ['get', 'list']
          keys: ['get', 'list']
          certificates: ['get', 'list']
        }
      }
    ]
  }
}

// Outputs (without sensitive information)
output storageAccountName string = storageAccount.name
output storageConnectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=[HIDDEN];EndpointSuffix=core.windows.net'
output sqlServerName string = sqlServer.properties.fullyQualifiedDomainName
output sqlDatabaseName string = databaseName
output sqlConnectionString string = 'Driver={ODBC Driver 17 for SQL Server};Server=${sqlServer.properties.fullyQualifiedDomainName};Database=${databaseName};Uid=${sqlServerAdminLogin};Pwd=[HIDDEN];'
output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
output appInsightsKey string = appInsights.properties.InstrumentationKey
output keyVaultName string = keyVault.name
