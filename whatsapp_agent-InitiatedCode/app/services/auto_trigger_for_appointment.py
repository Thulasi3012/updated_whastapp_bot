import requests
from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from app.database.models import AppointmentRequests, Customer, Project, ProjectWhatsAppCredentials
from app.database.database import get_db

router = APIRouter()

def send_whatsapp_auto_template(project_id, phone_number, template_name, db: Session, components=None):
    """
    Sends an approved WhatsApp template message with optional components
    (placeholders like name, project, date).
    """
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
            "name": template_name,
            "language": {"code": "en_US"}
        }
    }

    # add dynamic variables if provided
    if components:
        payload["template"]["components"] = components

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to send WhatsApp template: {response.text}")

    return response.json()


@router.post("/auto_trigger-appointment/{appointment_id}")
def trigger_appointment(appointment_id: int, db: Session = Depends(get_db)):
    """
    When an appointment is created, automatically sends an approved WhatsApp 
    template message (with dynamic placeholders).
    """
    appointment = db.query(AppointmentRequests).filter(AppointmentRequests.id == appointment_id).first()
    if not appointment:
        return {"status": "error", "message": "Appointment not found."}

    customer = db.query(Customer).filter(Customer.customer_id == appointment.customer_id).first()
    if not customer or not customer.phone_number:
        return {"status": "error", "message": "Customer phone number not found."}

    project = db.query(Project).filter(Project.id == appointment.project_id).first()

    # Example: Approved template "hello_world" expects 3 body placeholders
    components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": customer.name if customer.name else "Customer"},
                {"type": "text", "text": project.name if project else "Project"},
                {"type": "text", "text": appointment.requested_date.strftime("%d-%m-%Y") if appointment.requested_date else "Soon"}
            ]
        }
    ]

    res = send_whatsapp_auto_template(
        project_id=appointment.project_id,
        phone_number=customer.phone_number,
        template_name="appointment",   # ✅ must exactly match Meta approved template
        db=db,
        components=components
    )

    return {
        "status": "success",
        "appointment_id": appointment_id,
        "whatsapp_response": res
    }
