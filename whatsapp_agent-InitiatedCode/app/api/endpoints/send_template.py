import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from enum import Enum
import requests

from app.database.database import get_db
from app.database.models import (
    Customer,
    Project,
    WhatsappTemplate,
    TemplateUsageLog,
    WhatsappConversation,
    WhatsappConversationMessage,
    ProjectWhatsAppCredentials
)

router = APIRouter(prefix="/api/start-chat", tags=["startchat"])
logger = logging.getLogger("whatsapp_templates")


class TemplateEnum(str, Enum):
    welcome_temp = "welcome_temp"
    appointment_1 = "appointment_1"
    post_visit = "post_visit"


def send_whatsapp_template(project_id, phone_number, template_name, db: Session, components=None):
    cred = db.query(ProjectWhatsAppCredentials).filter_by(project_id=project_id).first()
    if not cred:
        raise Exception("WhatsApp credentials not found for project")

    access_token = cred.long_lived_access_token or cred.temporary_access_token
    if not access_token:
        raise Exception("No valid access token found for project WhatsApp credentials")

    url = f"https://graph.facebook.com/v19.0/{cred.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": "welcome" if template_name =="welcome_temp" else "appointment_3" if template_name=="appointment_1"else "post_visit",
            "language": {"code": "en_GB"}
        }
    }

    if components:
        payload["template"]["components"] = components

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to send WhatsApp template: {response.text}")

    return response.json()


@router.post("/send-template")
def send_template_message(
    project_id: int,
    customer_id: str,
    template_name: TemplateEnum,
    appointment_date: datetime = None,  # Optional, only for appointment_1
    db: Session = Depends(get_db)
):
    # 1. Fetch customer
    customer = db.query(Customer).filter_by(customer_id=customer_id).first()
    if not customer or not customer.phone_number:
        raise HTTPException(status_code=404, detail="Customer not found or missing phone number")

    # 2. Fetch project
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 3. Prepare components explicitly per template
    components = []

    if template_name == TemplateEnum.welcome_temp:
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "parameter_name": "customer_name", "text": customer.full_name or "Customer"},
                    {"type": "text", "parameter_name": "project_name", "text": project.name or "Project"}
                ]
            }
        ]

    elif template_name == TemplateEnum.appointment_1:
        # Appointment date is required
        if appointment_date is None:
            raise HTTPException(status_code=400, detail="Missing required variable: appointment_date")
        
        components = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "parameter_name": "1", "text": customer.full_name or "Customer"},
                        {"type": "text", "parameter_name": "2", "text": project.name or "Project"},
                        {"type": "text", "parameter_name": "3", "text": appointment_date.strftime("%d-%m-%Y")}
                    ]
                }
            ]


    elif template_name == TemplateEnum.post_visit:
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "parameter_name": "customer_name", "text": customer.full_name or "Customer"},
                    {"type": "text", "parameter_name": "project_name", "text": project.name or "Project"}
                ]
            }
        ]

    else:
        raise HTTPException(status_code=400, detail="Invalid template selected")

    # 4. Send WhatsApp message
    try:
        response = send_whatsapp_template(
            project_id=project_id,
            phone_number=customer.phone_number,
            template_name=template_name.value,
            db=db,
            components=components
        )
    except Exception as e:
        logger.error(f"WhatsApp send error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    # 5. Log template usage
    usage_log = TemplateUsageLog(
        template_name=template_name.value,
        recipient_number=customer.phone_number,
        message_sid=response.get("messages", [{}])[0].get("id"),
        conversation_id=None,
        created_at=datetime.utcnow()
    )
    db.add(usage_log)

    # 6. Manage conversation
    conversation = (
        db.query(WhatsappConversation)
        .filter_by(customer_id=customer_id, project_id=project_id, end_time=None)
        .first()
    )
    if not conversation:
        conversation = WhatsappConversation(
            customer_id=customer_id,
            project_id=project_id,
            whatsapp_number=customer.phone_number,
            start_time=datetime.utcnow(),
        )
        db.add(conversation)
        db.flush()

    # 7. Log conversation message
    message_log = WhatsappConversationMessage(
        conversation_id=conversation.conversation_id,
        sender_type="system",
        message_text=f"Template: {template_name.value}",
        message_type="template",
        twilio_message_sid=response.get("messages", [{}])[0].get("id"),
    )
    db.add(message_log)
    db.commit()

    return {
        "status": "success",
        "message": f"Template '{template_name.value}' sent to {customer.phone_number}",
        "response": response
    }