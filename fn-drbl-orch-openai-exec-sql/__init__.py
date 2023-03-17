import logging
import os
import openai
import azure.durable_functions as df

def orchestrator_function(context: df.DurableOrchestrationContext):
    """
    Orchastrates the execution by executing the activity functions : 

    1. Execute the query and get the result in CSV format
    2. Upload the CSV file to a azure storage blob and return a SAS URL
    """
    logging.info("Starting execution of orchastrator function")

    #Get environment variables
    host = os.environ["POSTGRE_SQL_SERVER"]
    port = os.environ["POSTGRE_SQL_PORT"]
    database = os.environ["POSTGRE_SQL_DB_NAME"]
    user = os.environ['POSTGRE_SQL_USER']
    password = os.environ['POSTGRE_SQL_PWD']
    storage_account_name = os.environ["STORAGE_ACCOUNT_NAME"]
    container_name = os.environ["STORAGE_CONTAINER_NAME"]

    # Get query text from input
    params = context.get_input()    
    if 'query' in params:
        sql_query = params['query']
    else: 
        return ['Please provide query text.']
    
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