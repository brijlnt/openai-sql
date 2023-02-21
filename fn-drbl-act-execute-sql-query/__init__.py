import logging
import pandas as pd
import psycopg2

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
                return results_df.to_csv(index=False)
    
def main(params) -> str:
    try:
        return execute_sql_query(
            params['host'], 
            params['port'], 
            params['database'], 
            params['user'], 
            params['password'], 
            params['sql_query'])
    except Exception as e:
        logging.exception(e)
        return str(e)
