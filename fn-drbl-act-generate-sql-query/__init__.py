import openai
import logging
import pandas as pd
import psycopg2

def get_prompt_text(prompt_lines, text_query):
    schema_text=''
    for pl in prompt_lines:
        schema_text+= f'# {pl}\\n'
    return ( '### Postgres SQL tables, with their properties:\\n#\\n' + schema_text + 
            '#\\n### A query to ' + text_query +'\\nSELECT' )

def generate_openai_prompt(host, port, database, user, password, text_query):
    sql_query = "Select line from config.prompt where include is true;"
    with psycopg2.connect(host=host, 
                    port=port, 
                    database=database, 
                    user=user, 
                    password=password) as conn:
        with conn.cursor() as cursor:
                cursor.execute(sql_query)
                df = pd.DataFrame(cursor.fetchall(), 
                            columns=[desc[0] for desc in cursor.description])
                prompt_lines = df['line'].values.tolist()
    return get_prompt_text(prompt_lines, text_query)

def prompt_openai(prompt):
    logging.info(prompt)
    return openai.Completion.create(
        engine="LTIM",
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
