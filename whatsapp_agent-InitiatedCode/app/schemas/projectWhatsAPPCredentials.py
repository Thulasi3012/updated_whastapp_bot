from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

class ProjectWhatsAppCredentialsBase(BaseModel):
    project_id:int
    api_key: str
    verify_token: str
    phone_number_id: str
    app_id: str
    app_secret: str
    temporary_access_token: Optional[str] = None
    long_lived_access_token: Optional[str] = None

class ProjectWhatsAppCredentialsCreate(ProjectWhatsAppCredentialsBase):
    pass

class ProjectWhatsAppCredentialsUpdate(BaseModel):
    api_key: Optional[str] = None
    verify_token: Optional[str] = None
    phone_number_id: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    temporary_access_token: Optional[str] = None
    long_lived_access_token: Optional[str] = None

class ProjectWhatsAppCredentialsResponse(ProjectWhatsAppCredentialsBase):
    cred_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True