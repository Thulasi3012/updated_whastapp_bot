import requests
from sqlalchemy.orm import Session
from app.database.crud import ProjectWhatsAppCredentialsCreate,ProjectWhatsAppCredentialsUpdate
import uuid
from app.database import crud

def exchange_tokens(app_id:str, app_secret:str, short_lived_token:str)->str:
    url="https://graph.facebook.com/v17.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token
    }
    response=requests.get(url,params=params)
    data=response.json()
    return data.get("access_token")

def create_credentials_service(db:Session, cred:ProjectWhatsAppCredentialsCreate):
    if cred.temporary_access_token:
        long_token=exchange_tokens(cred.app_id, cred.app_secret, cred.temporary_access_token)
        cred.long_lived_access_token = long_token
        return crud.create_credentials(db, cred)
    
def update_credentials_service(db:Session,cred_id:uuid.UUID,cred:ProjectWhatsAppCredentialsUpdate):
    if cred.temporary_access_token:
        long_token=exchange_tokens(cred.app_id, cred.app_secret, cred.temporary_access_token)
        cred.long_lived_access_token = long_token
    return crud.update_credentials(db, cred_id, cred)

def get_credentials_service(db:Session, project_id:int=None):
    return crud.get_credentials(db,project_id)

