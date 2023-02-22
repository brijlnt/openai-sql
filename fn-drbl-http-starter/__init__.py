import logging
import azure.functions as func
import azure.durable_functions as df

async def main(req: func.HttpRequest, starter: str) -> func.HttpResponse:
    client = df.DurableOrchestrationClient(starter)

    #Get orchastration function name and data
    function_name = req.route_params["functionName"]
    data = req.get_json()
    
    #Call orchastrator function
    instance_id = await client.start_new(function_name, client_input=data)
    logging.info(f"Started orchestration with ID = '{instance_id}'.")
    return client.create_check_status_response(req, instance_id)