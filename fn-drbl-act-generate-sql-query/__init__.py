import openai
import logging
import pandas as pd
import psycopg2
#added below nltk imports 
from stop_words import get_stop_words
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


def get_prompt_text(prompt_lines, text_query):
    schema_text=''
    for pl in prompt_lines:
        schema_text+= f'# {pl}\\n'
    return ( '### Postgres SQL tables, with their properties:\\n#\\n' + schema_text + 
            '#\\n### A query to ' + text_query +'\\nSELECT' )

#def get_probabale_tablelist(text_query):
#    stop_words = list(get_stop_words('en'))         #About 900 stopwords
#    nltk_words = list(stopwords.words('english')) #About 150 stopwords
#    stop_words.extend(nltk_words)
    #  word_list =  "show all sales_orders of customers"
#    tokens = word_tokenize(text_query)
#    req_table_list = [w for w in tokens if not w in stop_words]
#    return req_table_list

def get_probabale_tablelist(text_query):
    req_table_list = [w for w in tokens if not w in stop_words]
    prompt = (f"Please correct spelling and list only keywords from below text:\n"
              f"{text_query}\n")
    logging.info(prompt)
    return openai.Completion.create(
        engine='LTIM_Keyword',        
        prompt=prompt,
        temperature=0,
        max_tokens=150,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=["#", ";"]
    )

def generate_prompt_list(data, probabale_tablelist):
    table_list = data["table_name"]
    join_table_list = data["join_table"]
    final_list = []
    for table_name,join_table in zip(table_list,join_table_list):
        for j in range(len(req_table_list)):
            if table_name == req_table_list[j]:   #This logic can be changed to cater to spelling mistakes
                final_list.append(table_name)       
                if join_table ==join_table:
                    for kv in join_table.split(","):
                        final_list.append(kv)
    list_for_prompt = set(final_list)
    filterd_data = data[data['table_name'].isin(list_for_prompt)]
    return(filterd_data['line'].values.tolist())
    
def generate_openai_prompt(host, port, database, user, password, text_query):
    #added code to creare optimized prompt
    probabale_tablelist = get_probabale_tablelist(text_query)
    sql_query = "Select * from config.prompt;"
    with psycopg2.connect(host=host, 
                    port=port, 
                    database=database, 
                    user=user, 
                    password=password) as conn:
        with conn.cursor() as cursor:
                cursor.execute(sql_query)
                df = pd.DataFrame(cursor.fetchall(), 
                            columns=[desc[0] for desc in cursor.description])
                prompt_lines = generate_prompt_list(df, probabale_tablelist)
      #          df['line'].values.tolist()
    return get_prompt_text(prompt_lines, text_query)

def prompt_openai(prompt):
    logging.info(prompt)
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
      
    
def main(params) -> str:
    try:
        prompt_text = generate_openai_prompt(
                params['host'], 
                params['port'], 
                params['database'], 
                params['user'], 
                params['password'], 
                params['text_query'])

        return generate_sql_query(prompt_text)    
    except Exception as e:
        logging.exception(e)
        return str(e)
