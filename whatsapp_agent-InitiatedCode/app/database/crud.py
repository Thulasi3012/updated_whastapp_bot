from sqlalchemy.orm import Session
from app.database.models import ProjectWhatsAppCredentials
from app.schemas.projectWhatsAPPCredentials import ProjectWhatsAppCredentialsCreate, ProjectWhatsAppCredentialsUpdate
from typing import Optional
import uuid

def create_credentials(db:Session, credentials: ProjectWhatsAppCredentialsCreate)->ProjectWhatsAppCredentials:
    try:
        db_creds=ProjectWhatsAppCredentials(**credentials.dict())
        db.add(db_creds)
        db.commit()
        db.refresh(db_creds)
        return db_creds
    except Exception as e:
        db.rollback()
        raise e

def update_credentials(db:Session, cred_id:uuid.UUID, credentials:ProjectWhatsAppCredentialsUpdate)->Optional[ProjectWhatsAppCredentials]:
    try:
        db_creds = db.query(ProjectWhatsAppCredentials).filter(ProjectWhatsAppCredentials.cred_id == cred_id).first()
        if not db_creds:
            return None
        for key, value in credentials.dict(exclude_unset=True).items():
            setattr(db_creds, key, value)
        db.commit()
        db.refresh(db_creds)
        return db_creds
    except Exception as e:
        db.rollback()
        raise e


def get_credentials(db: Session, project_id:int)->Optional[ProjectWhatsAppCredentials]:
    try:
        query=db.query(ProjectWhatsAppCredentials)
        if project_id:
            query=query.filter(ProjectWhatsAppCredentials.project_id == project_id)
        return query.all() or []
    except Exception as e:
        db.rollback()
        raise e
