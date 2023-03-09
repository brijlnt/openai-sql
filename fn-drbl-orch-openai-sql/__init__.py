import logging
import os
import openai
import azure.durable_functions as df

def orchestrator_function(context: df.DurableOrchestrationContext):
    logging.info("Starting execution of orchastrator function")

    #Get environment variables
    
    host = os.environ["POSTGRE_SQL_SERVER"]
    port = os.environ["POSTGRE_SQL_PORT"]
    database = os.environ["POSTGRE_SQL_DB_NAME"]
    user = os.environ['POSTGRE_SQL_USER']
    password = os.environ['POSTGRE_SQL_PWD']
    storage_account_name = os.environ["STORAGE_ACCOUNT_NAME"]
    container_name = os.environ["STORAGE_CONTAINER_NAME"]
    openai.api_key = os.environ["OPENAI_API_KEY"]
    openai.api_base = os.environ["AZURE_OPENAI_ENDPOINT"]
    openai.api_type = os.environ['API_TYPE']
    openai.api_version = os.environ['API_VERSION']
    deployment_name = os.environ['DEPLOYMENT_NAME']
    deployment_name_keyword = os.environ['DEPLOYMENT_NAME_KEYWORD']
    

    # Get query text from input
    params = context.get_input()    
    if 'query' in params:
        text_query = params['query']
    else: 
        return ['Please provide query text.']
    
    # Generate convert the text query to SQL using OpenAI api
    sql_query = yield context.call_activity('fn-drbl-act-generate-sql-query', 
                                { 
                                    'host' : host, 
                                    'port' : port,
                                    'database' : database,
                                    'user' : user,
                                    'password': password,
                                    'text_query': text_query
                                }
                            )
    # Exectute the SQL query and get results in CSV format
    results = yield context.call_activity('fn-drbl-act-execute-sql-query', 
                                { 
                                    'host' : host, 
                                    'port' : port,
                                    'database' : database,
                                    'user' : user,
                                    'password': password,
                                    'sql_query': sql_query
                                }
                            )
    # Upload the CSV to a azure storage blob and return a SAS URL
    results_blob_sas_url = yield context.call_activity('fn-drbl-act-upload-results-to-blob', 
                                { 
                                    'storage_account_name': storage_account_name, 
                                    'container_name': container_name,                                     
                                    'results': results
                                }
                            )
    
    # Return the query and the SAS URL
    return { 'sqlQuery': sql_query, 'resultsFileUrl': results_blob_sas_url }

main = df.Orchestrator.create(orchestrator_function)
