# Azure Function App for querying PostgresQL database using Open AI natural language to code translation

## Deployment

### Deploy azure resources
Clone this repo. Deploy the Azure resources by executing the bicep template `template.bicep` in the folder `/deployment`

```sh
    az deployment group create --name deployopenaisql --resource-group rg-openai-sql --template-file template.bicep
```

Below resources will be deployed.  

1. Azure Function app - `az-func-app-<suffix> *` which contains following functions : 

| Function                     | Description                                                                                                   |
|------------------------------|-------------------------------------------------                                                              |
| `fn-drbl-orch-openai-sql`    | Azure durable orchastrator function                                                                           |     
| `fn-drbl-generate-sql-query` | Azure durable activity function which generate SQL equivalent for the natural language query using OpenAI API |
| `fn-drbl-execute-sql-query`  | Azure durable activity function which executes SQL query on PostgresSQL database                              |
| `fn-drbl-act-upload-results-to-blob`     | Azure durable activity function which uploads the results of the query to an Azure storage blob   |
2. Application insights - `az-app-ins-<suffix>`
3. Storage account used by the function app for internal purposes- `azfnstrg<suffix>`
4. App service plan for the function app - `az-func-app-plan-<suffix>`
5. Postgres SQL flexiserver - `az-postgres-server-<suffix>` and database - `retail_org`
6. Storage account used for storing query output - `azdatastrg<suffix>` with container `data`

_* Suffix is random unique string generated automatically during deployment_

### Update the OpenAI API Key

1. Sign up for OpenAI if you haven't done so already and generate an API key. 

2. Go to azure portal, locate the function app and update the applicaton settings `OPEN_AI_API_KEY` with the value of the key.

### Modify PostgresSQL Server network settings
Go to azure portal, locate postgresSQL server resource and make following changes to network settings.
    
1. Turn on _Allow public access from any Azure service within Azure to this server_

2. Add your client ip addres(optional, if you running following commands from your machine instead of Azure Shell).

### Create and configure database

1. Dowload the database backup from the repo

```sh
    wget https://github.com/bablulawrence/openai-sql/raw/main/data/retail_org.dump    
```

2. Connect to the PostgreSQL server and create `retail_org` database.

```sh
     az postgres flexible-server connect -n az-postgres-server-<suffix> -u pgadmin123 -p <password> -d postgres --interactive
```
```SQL
    CREATE DATABASE retail_org;
```
3. Restore the backup file to the database
```sh
    pg_restore -v --no-owner --host=az-postgres-server-<suffix>.postgres.database.azure.com --port=5432 --username=pgadmin123 --dbname=retail_org retail_org.dump
```