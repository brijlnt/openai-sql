import streamlit as st
import sqlparse
import os
import requests
from requests.exceptions import HTTPError
import pandas as pd
from time import sleep


FUNC_URL = os.environ["AZURE_FUNCTION_APP_URL"] 
FUNC_KEY = os.environ["AZURE_FUNCTION_APP_KEY"] 


def call_az_func_api(text_query, exec_state):
    url = f'{FUNC_URL}/api/orchestrators/fn-drbl-orch-openai-sql?code={FUNC_KEY}'
    try:
        response = requests.post(url, json={ "query" : text_query})
        response.raise_for_status()
        func_start = response.json()        
    except HTTPError as http_e:
        print(f'HTTP error: {http_e}')
    except Exception as e:
        print(f'Error: {e}') 

    statusUri = func_start['statusQueryGetUri']
    try: 
        response = requests.get(statusUri)
        response.raise_for_status()        
        func_run = response.json()
        exec_state.text(f'Status: {func_run["runtimeStatus"]}') 
        while(func_run['runtimeStatus'] != 'Completed'):
            sleep(3)
            response= requests.get(statusUri)
            response.raise_for_status()
            func_run = response.json()
            exec_state.text(f'Status: {func_run["runtimeStatus"]}') 
            if (func_run['runtimeStatus'] == 'Failed'):
                exec_state.text(f'Status: {func_run["runtimeStatus"]}, Error:{func_run["output"]}') 
                Exception(f'Error : {func_run["output"]}')
        return { 'sqlQuery': func_run['output']['sqlQuery'], 'resultsFileUrl' : func_run['output']['resultsFileUrl'] }
    except HTTPError as http_e:
        print(f'HTTP error occurred: {http_e}')
    except Exception as e: 
        print(f'Error: {e}') 

@st.cache_data
def load_data(nrows, resultsFileUrl):
    data = pd.read_csv(resultsFileUrl, nrows=nrows, dtype=str)
    lowercase = lambda x: str(x).lower()
    data.rename(lowercase, axis='columns', inplace=True)
    return data

text_query = st.text_area('Please enter query text', '')
if (text_query): 
    exec_state = st.text(f'Triggering execution ...')
    response = call_az_func_api(text_query, exec_state)
    st.code(sqlparse.format(response['sqlQuery'], reindent=True, keyword_case='upper'), language='sql')
    data = load_data(1000, response['resultsFileUrl'])
    st.write(data)
    exec_state.text(f'Done, results:')