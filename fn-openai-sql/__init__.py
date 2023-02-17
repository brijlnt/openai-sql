from azure.identity import DefaultAzureCredential
import azure.functions as func
import os
import io
import csv
import openai
import logging
import json
import pandas as pd
import uuid
# import pyodbc
import psycopg2
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

def execute_sql_query(host, port, database, user, password, sql_query): 
    with psycopg2.connect(host=host, 
                        port=port, 
                        database=database, 
                        user=user, 
                        password=password) as conn:
        with conn.cursor() as cursor:
                cursor.execute(sql_query)
                results_df = pd.DataFrame(cursor.fetchall(), 
                            columns=[desc[0] for desc in cursor.description])
                return results_df

def get_prompt_text(prompt_lines, text_query):
    schema_text=''
    for pl in prompt_lines:
        schema_text+= f'# {pl}\\n'
    return ( '### Postgres SQL tables, with their properties:\\n#\\n' + schema_text + 
            '#\\n### A query to' + text_query +'\\nSELECT' )

def generate_openai_prompt(host, port, database, user, password, text_query):
    sql_query = "Select line from config.prompt where include is true;"
    df = execute_sql_query(host, port, database, user, password, sql_query)
    prompt_lines = df['line'].values.tolist()
    return get_prompt_text(prompt_lines, text_query)
    
def prompt_openai(prompt):
    return openai.Completion.create(
        model="code-davinci-002",
        prompt=prompt,
        temperature=0,
        max_tokens=150,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=["#", ";"]
    )

def generate_sql_query(prompt_text):
    response = prompt_openai(prompt_text)
    s = response["choices"][0]["text"]
    s = s.replace('\\n', ' ').replace('\n', ' ')
    # print(response)
    return f'select {s};'        

def upload_results_to_blob(results_df, storage_account_name, container_name, file_name ):        
    
    #Create BlobServiceClient, ContainerClient and BlobClient    
    blob_service_client = BlobServiceClient(
        account_url=f"https://{storage_account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential()
    )

    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(file_name)

    # Convert Dataframe to CSV and upload it to a blob
    blob_client.upload_blob(results_df.to_csv(index=False), overwrite=True)

    udk = blob_service_client.get_user_delegation_key(
        key_start_time=datetime.utcnow() - timedelta(hours=1),
        key_expiry_time=datetime.utcnow() + timedelta(hours=1))

    # Create and return a SAS URI for the blob
    sas_token = generate_blob_sas(
        account_name=storage_account_name,
        container_name=container_name,
        blob_name=file_name,        
        user_delegation_key=udk,
        permission=BlobSasPermissions(read=True),
        start=datetime.utcnow() - timedelta(minutes=15),
        expiry=datetime.utcnow() + timedelta(minutes=30),
        default_credential=True
    )
    
    blob_url = blob_client.url
    sas_uri = f"{blob_url}?{sas_token}"
    return sas_uri
       
    
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Starting execution')
    host = os.environ["POSTGRES_SQL_SERVER"]
    port = os.environ["POSTGRES_SQL_PORT"]
    database = os.environ["POSTGRES_SQL_DB_NAME"]
    user = os.environ['POSTGRES_SQL_USER']
    password = os.environ['POSTGRES_SQL_PWD']
    storage_account_name = os.environ["STORAGE_ACCOUNT_NAME"]
    container_name = os.environ["STORAGE_CONTAINER_NAME"]
    openai.api_key = os.environ["OPENAI_API_KEY"]

    try:
        req_body = req.get_json()
        logging.error(req_body)
    except ValueError:
        pass
    else:
        text_query = req_body.get('query')
    
    if not text_query:
        func.HttpResponse("Please provide query text", status_code = 400)

    try:
        prompt_text = generate_openai_prompt(host, port, database, user, password, text_query)    
        sql_query = generate_sql_query(prompt_text)    
        results_df = execute_sql_query(host, port, database, user, password, sql_query)
        results_blob_uri = upload_results_to_blob(results_df, storage_account_name, container_name, f"file_{uuid.uuid4()}.csv")
        return func.HttpResponse(json.dumps({ "sqlQuery": sql_query, "resultsFileUrl": results_blob_uri}), status_code=200)
    except Exception as e: 
        logging.exception(e)
        return func.HttpResponse(str(e), status_code=500)        