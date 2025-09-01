from fastapi import APIRouter, HTTPException, Query,Depends
from typing import List
from app.database.database import get_db
from app.schemas.projectWhatsAPPCredentials import  ProjectWhatsAppCredentialsResponse
from sqlalchemy.orm import Session
from app.services import project_whatsapp_credentials as service
from app.schemas.projectWhatsAPPCredentials import ProjectWhatsAppCredentialsCreate, ProjectWhatsAppCredentialsUpdate
import uuid

router=APIRouter(prefix="/whatsapp/creds", tags=["whatsapp_credentials"])

@router.get("/")
def get_whatsapp_credentials(project_id:int = None,db:Session=Depends(get_db)):
    try:
        creds=service.get_credentials_service(db, project_id)
        return creds
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
def create_whatsapp_credentials(payload: ProjectWhatsAppCredentialsCreate, db: Session = Depends(get_db)):
    try:
        created_cred = service.create_credentials_service(db, payload)
        return created_cred
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.put("/{cred_id}")
def update_whatsapp_credentials(cred_id: uuid.UUID, payload: ProjectWhatsAppCredentialsUpdate, db: Session = Depends(get_db)):
    try:
        updated_cred = service.update_credentials_service(db, cred_id, payload)
        if not updated_cred:
            raise HTTPException(status_code=404, detail="Credential not found")
        return {"message": "Credential updated successfully", "credential": updated_cred}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
