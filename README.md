# An app for querying a PostgresQL database using OpenAI's natural language-to-SQL translation and Azure Functions

## Design

### API app
Design of the App shown in Figure 1. At the core, there is an Azure durable orchestrator function which runs as set of activity functions using [function chaining pattern](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-overview?tabs-csharp-inproc#chaining) to translate the natural language query to SQL using OpenAI Codex model and execute it on Postgres SQL database tables and upload the results to Azure Blob Storage. It then returns the generated SQL and a SAS URL of the output file to the caller. 

![Figure 1](https://github.com/bablulawrence/openai-sql/raw/main/docs/openai_sql.svg)

### Database

The application uses a sample database consisting of following tables. Data in products, customer and sales_orders tables are based on the Databricks retail_org datasets. 

| Table          | Details                                                                                            |
|----------------|--------------------------------------------------------------------------------------------------------------------------|
| `Products`     | Product details - product_id, product_name, product_category, sales_price etc.                                           |     
| `Customers`    | Customer details - customer_id, customer_name, street, state, city, postcode  etc.                                       |     
| `Sales_orders` | Sales order details - order_line_item_no, order_number, order_datetime, customer_id, product_id, unit_price, quantity    |
| `Prompt`       | Prompt - A table which contains details such as table schema, data descriptions etc. used for creating OpenAI API prompt |

## Deployment

### Deploy azure resources
Deploy the Azure resources by running the bicep template `template.bicep` in the folder `/deployment`

```sh
    az deployment group create --name deployopenaisql --resource-group rg-openai-sql --template-file template.bicep
```

Following resources will be deployed.  

1. Azure Function app - `az-func-app-<suffix> *` which contains following functions : 

| Function                     | Description                                                                                                       |
|------------------------------|-------------------------------------------------                                                                  |
| `fn-drbl-starter`            | Azure durable starter function with http trigger                                                                  |     
| `fn-drbl-orch-openai-sql`    | Azure durable orchastrator function                                                                               |     
| `fn-drbl-act-generate-sql-query` | Azure durable activity function which generate SQL equivalent for the natural language query using OpenAI API |
| `fn-drbl-act-execute-sql-query`  | Azure durable activity function which executes SQL query on PostgreSQL database                               |
| `fn-drbl-act-upload-results-to-blob`     | Azure durable activity function which uploads the results of the query to an Azure storage blob       |
| `fn-openai-sql`     | A regular(non-durable) Azure Function with http trigger which does everthing - prompt generation through result file upload, good fit for interactive use cases       |

2. Application insights - `az-app-ins-<suffix>`
3. Storage account used by the function app for internal purposes- `azfnstrg<suffix>`
4. App service plan for the function app - `az-func-app-plan-<suffix>`
5. Postgres SQL flexiserver - `az-postgres-server-<suffix>` and database - `retail_org`
6. Storage account used for storing query output - `azdatastrg<suffix>` with container `data`

_* Suffix is random unique string generated automatically during deployment_

### Update the OpenAI API Key

1. Sign up for OpenAI if you haven't done so already and generate an API key. 

2. Go to azure portal, locate the function app and update the applicaton settings - `OPEN_AI_API_KEY` with the value of the key.

### Modify PostgreSQL Server network settings
Go to azure portal, locate PostgreSQL server resource and make following changes to network settings.
    
1. Turn on _Allow public access from any Azure service within Azure to this server_

2. Add your client ip addres(optional, if you running following commands from your machine instead of Azure Shell).

### Create and configure database

1. Dowload the database backup from the repo

```sh
    wget https://github.com/bablulawrence/openai-sql/raw/main/data/retail_org.dump    
```

2. Connect to the PostgreSQL server and create `retail_org` database.

```sh
     az postgres flexible-server connect -n az-postgres-server-<suffix> -u pgadmin123 -d postgres --interactive
```
```SQL
    CREATE DATABASE retail_org;
```
3. Restore the backup file to the database
```sh
    pg_restore -v --no-owner --host-az-postgres-server-<suffix>.postgres.database.azure.com --port-5432 --username-pgadmin123 --dbname-retail_org retail_org.dump
```

### Deploy azure function code
Github action is used for deploying the function code to Azure Function app. 

1. Fork this repo. 

2. Create environment variables and secrets required for Github action in the copy. 

Go to 'Actions' tab and enable workflows. In the 'Settings -> Secrets and variables-> Actions' of the repo, create an environment variable called `AZURE_FUNCTIONAPP_NAME` and populate the name of the Azure function app. Create new secret `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` under the 'Secrets' section and copy past the contents of the publish profile of the function app from the Azure portal(overview -> 'Get publish profile').

3. Execute the Github action to deploy the code. 

Go to the 'Actions' tab of the repo and exectue the Git hub action `Deploy code to Azure Function App` to deploy the code. 

## Executing the natural language(English) queries

1. Directly through Function API calls. 

You can query the database by directly invoking the orchastrator function `fn-drbl-orch-openai-sql` through azure function runtime interface.

```sh
curl https://az-func-app-<suffix>.azurewebsites.net/runtime/webhooks/durabletask/orchestrators/fn-drbl-orch-openai-sql?code-<azure function master key>\
--header "Content-Type: application/json" \
--data '{ "query": "list top selling products by state" }'
```

This will trigger the orchastrator function execution and return a response like this :  

```json
{
   "id":"f5d1849aae2442d8ad2ed7287ed9f282",
   "statusQueryGetUri":"https://az-func-app-<suffix>.azurewebsites.net/runtime/webhooks/durabletask/instances/f5d1849aae2442d8ad2ed7287ed9f282?taskHub-azfuncapp<suffix>&connection-Storage&code-QBcKy6A2i2QlmtVsJ2KNAFHg70uZ9_nmKag8kP1ZTkr8AeFuJrUHLg--",
   "sendEventPostUri":"https://az-func-app-<suffix>.azurewebsites.net/runtime/webhooks/durabletask/instances/f5d1849aae2442d8ad2ed7287ed9f282/raiseEvent/{eventName}?taskHub-azfuncapp<suffix>&connection-Storage&code-QBcKy6A2i2QlmtVsJ2KNAFHg70uZ9_nmKag8kP1ZTkr8AeFuJrUHLg--",
   "terminatePostUri":"https://az-func-app-<suffix>.azurewebsites.net/runtime/webhooks/durabletask/instances/f5d1849aae2442d8ad2ed7287ed9f282/terminate?reason-{text}&taskHub-azfuncapp<suffix>&connection-Storage&code-QBcKy6A2i2QlmtVsJ2KNAFHg70uZ9_nmKag8kP1ZTkr8AeFuJrUHLg--",
   "purgeHistoryDeleteUri":"https://az-func-app-<suffix>.azurewebsites.net/runtime/webhooks/durabletask/instances/f5d1849aae2442d8ad2ed7287ed9f282?taskHub-azfuncapp<suffix>&connection-Storage&code-QBcKy6A2i2QlmtVsJ2KNAFHg70uZ9_nmKag8kP1ZTkr8AeFuJrUHLg--",
   "restartPostUri":"https://az-func-app-<suffix>.azurewebsites.net/runtime/webhooks/durabletask/instances/f5d1849aae2442d8ad2ed7287ed9f282/restart?taskHub-azfuncapp<suffix>&connection-Storage&code-QBcKy6A2i2QlmtVsJ2KNAFHg70uZ9_nmKag8kP1ZTkr8AeFuJrUHLg--",
   "suspendPostUri":"https://az-func-app-<suffix>.azurewebsites.net/runtime/webhooks/durabletask/instances/f5d1849aae2442d8ad2ed7287ed9f282/suspend?reason-{text}&taskHub-azfuncapp<suffix>&connection-Storage&code-QBcKy6A2i2QlmtVsJ2KNAFHg70uZ9_nmKag8kP1ZTkr8AeFuJrUHLg--",
   "resumePostUri":"https://az-func-app-<suffix>.azurewebsites.net/runtime/webhooks/durabletask/instances/f5d1849aae2442d8ad2ed7287ed9f282/resume?reason-{text}&taskHub-azfuncapp<suffix>&connection-Storage&code-QBcKy6A2i2QlmtVsJ2KNAFHg70uZ9_nmKag8kP1ZTkr8AeFuJrUHLg--"
}
```
You can use the URL provided in the property `statusQueryGetUri` to track the status of the execution. 

```sh
curl 'https://az-func-app-<suffix>.azurewebsites.net/runtime/webhooks/durabletask/instances/f5d1849aae2442d8ad2ed7287ed9f282?taskHub-azfuncapp7yq7uiiw4bhwi&connection-Storage&code-QBcKy6A2i2QlmtVsJ2WNAFHg70uZ9_nmKag7kP1ZTkw8AzFuJrUHLg--'
```
response will be similar to: 

```
{
  "name": "fn-drbl-orch-openai-sql",
  "instanceId": "f5d1849aae2442d8ad2ed7287ed9f282",
  "runtimeStatus": "Completed",
  "input": {
    "query": "list top selling products by state"
  },
  "customStatus": null,
  "output": {
    "sqlQuery": "select    state,   product_name,   SUM(quantity) AS total_quantity FROM   sales_orders   INNER JOIN customers ON sales_orders.customer_id - customers.customer_id   INNER JOIN products ON sales_orders.product_id - products.product_id GROUP BY   state,   product_name ORDER BY   state,   total_quantity DESC LIMIT   10;",
    "resultsFileUrl": "https://azdatastrg<suffix>.blob.core.windows.net/data/file_c5013082-e328-453e-8259-b13ad0ce96cd.csv?st-2023-02-20T08%3A44%3A30Z&se-2023-02-20T09%3A29%3A30Z&sp-r&sv-2021-08-06&sr-b&skoid-d95e5438-908f-47ee-b8f7-70a1a3c93b00&sktid-0b55e01a-573a-4060-b656-d1a3d5815791&skt-2023-02-20T07%3A59%3A30Z&ske-2023-02-20T09%3A59%3A30Z&sks-b&skv-2021-08-06&sig-g/D6cfkd18JDoTBgRtsMgrdhZwCpQ4HNm%2B7aFggLOYY%3D"
  },
  "createdTime": "2023-02-20T08:59:15Z",
  "lastUpdatedTime": "2023-02-20T08:59:31Z"
}
```

`runtimeStatus` property will be initially show `Pending`. Once the orchastrator starts running its value will change to `Running` and finally to `Completed`. You can see the SQL corresponding to input text query and the URL of the blob storage file where there results are uploaded. By default the SAS token will be valid for 30 mins. 

2. Using Streamlit app.

You can also use the Streamlit app script `app.py` in the `/tests` folder to execute the queries. To do this create two environemnt variables `AZURE_FUNCTION_APP_URL` and `AZURE_FUNCTION_APP_KEY` and populate the values of the function app URL and key. Alternatively you can update thise values directly in the script.

Start the script by running the command :

```sh
    streamlit run app.py
```

This will lanch app screen. Type in the query text in the text area and press `Ctrl + Enter` to run the query. Generated SQL query and results will be displayed below after query execution is complete (Figure 2). 

![Figure 2](https://github.com/bablulawrence/openai-sql/raw/main/docs/streamlit_run.png)

## Sample query results

### Query for most valuable customers
![High value customers](https://github.com/bablulawrence/openai-sql/raw/main/docs/sample_high_value_customers.png)
----------------------

### Query for state code using full state names
Note that in the database state codes use USPS code. To query these correctly using NL, insert a line in the prompt table. 

```SQL
INSERT INTO config.prompt (line, include) VALUES ('state column uses USPS code', true);
```
![State code](https://github.com/bablulawrence/openai-sql/raw/main/docs/sample_state_code.png)
----------------------

### Query for customer names
`customer_name` column of `customers` table contains names of the form  "last name, first name middle name" in capital letters. It also contains a mixture of people(individual) names and company names and only people names follow the above format. To query correctly, insert the following line in the prompt table

```SQL
INSERT INTO config.prompt (line, include) VALUES
('sample customer names are  "STEPHENS,  GERALDINE M",  "OUTTEN,  MIA G", "STUBBS SR,  LAWRENCE D",  "status ditigal", "m2 digital post", "genesis electronics recycling"', true)

```
![Customer name - person](https://github.com/bablulawrence/openai-sql/raw/main/docs/sample_customer_names_person.png)
----------------------

![Customer name - company](https://github.com/bablulawrence/openai-sql/raw/main/docs/sample_customer_names_company.png)
----------------------

### Query for date and time
![Date and time](https://github.com/bablulawrence/openai-sql/raw/main/docs/sample_data_and_time.png)