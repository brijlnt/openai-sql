param suffix string = uniqueString(resourceGroup().id)
param location string = resourceGroup().location

@secure()
param openaiApiKey string = ''

param postgresServerName string = 'az-postgres-server-${suffix}'
param postgresPort string = '5432'

param postgresDbName string = 'retail_org'

param postgresAdminUser string = 'pgadmin123'

@secure()
param postgresAdminUserPassword string = 'postgrespw@123'

param appInsightsName string = 'az-app-ins-${suffix}'
param functionAppName string = 'az-func-app-${suffix}'
param funcAppAppServicePlanName string = 'az-func-app-service-${suffix}'
param funcAppStorageAccountName string = 'azfnstrg${suffix}'
param dataStorageAccountName string = 'azdatastrg${suffix}'
param dataStorageAccountContainerName string = 'data'


// 'Storage blob data contributor' role id
var storageRoleDefintionId = '/providers/Microsoft.Authorization/roleDefinitions/ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2021-06-01' = {
  name: postgresServerName
  location: location  
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '14'
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminUserPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }    
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'   
  properties: {
    Application_Type: 'web'
  }
}

resource funcAppStorageAccount 'Microsoft.Storage/storageAccounts@2021-04-01' = {
  name: funcAppStorageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }  
}

resource appServicePlan 'Microsoft.Web/serverfarms@2021-02-01' = {
  name: funcAppAppServicePlanName
  location: location
  kind: 'linux'
  properties: {
    reserved: true
  }
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
}

resource functionApp 'Microsoft.Web/sites@2021-02-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.8'
      appSettings: [
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${funcAppStorageAccountName};AccountKey=${funcAppStorageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net;'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'PYTHON_VERSION'
          value: '3.8'
        }
        {
          name: 'OPENAI_API_KEY'
          value: openaiApiKey
        }
        {
          name: 'POSTGRES_SQL_DB_NAME'
          value: postgresDbName
        }
        {
          name: 'POSTGRES_SQL_PORT'
          value: postgresPort
        }
        {
          name: 'POSTGRES_SQL_USER'
          value: postgresAdminUser
        }
        {
          name: 'POSTGRES_SQL_PWD'
          value: postgresAdminUserPassword
        }
        {
          name: 'POSTGRES_SQL_SERVER'
          value: postgresServer.properties.fullyQualifiedDomainName
        }        
        {
          name: 'STORAGE_ACCOUNT_NAME'
          value: dataStorageAccountName
        }
        {
          name: 'STORAGE_CONTAINER_NAME'
          value: dataStorageAccountContainerName
        }
      ]
    }    
  }  
}


resource dataStorageAccount 'Microsoft.Storage/storageAccounts@2021-04-01' = {
  name: dataStorageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  identity: {
    type: 'SystemAssigned'
    }
}

resource dataStorageContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-04-01' = {
  name: '${dataStorageAccountName}/default/${dataStorageAccountContainerName}'
  properties: {
    publicAccess: 'None'
  }
  dependsOn: [
    dataStorageAccount
  ]
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid('storage-role', 
          dataStorageAccount.id, 
          resourceGroup().id, 
          functionApp.id, 
          storageRoleDefintionId)
  scope: dataStorageAccount
  properties: {
    principalId: functionApp.identity.principalId
    roleDefinitionId: storageRoleDefintionId
    principalType: 'ServicePrincipal'
  }
}
