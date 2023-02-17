from azure.identity import DefaultAzureCredential
import logging
import pandas as pd
import uuid
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

def upload_results_to_blob(storage_account_name, container_name, results, file_name ):        
    
    #Create BlobServiceClient, ContainerClient and BlobClient    
    blob_service_client = BlobServiceClient(
        account_url=f"https://{storage_account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential()
    )

    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(file_name)

    # Upload results to a blob
    blob_client.upload_blob(results, overwrite=True)

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
    sas_url = f"{blob_url}?{sas_token}"
    return sas_url
   
def main(params) -> str:
    try:
        return upload_results_to_blob(
            params['storage_account_name'], 
            params['container_name'], 
            params['results'], 
            f"file_{uuid.uuid4()}.csv")
    except Exception as e:
        logging.exception(e)
        return str(e)
