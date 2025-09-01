from fastapi import FastAPI, Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
import os
from app.database.database import get_db
from openai import OpenAI
from app.database.database import SessionLocal
from app.database.models import (
    Transcription, BotConversations, WhatsappConversation, WhatsappConversationMessage
)

router = APIRouter(prefix="/api/Summarize", tags=["summarization"])

# ✅ OpenAI Client (make sure OPENAI_API_KEY is in your .env)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SummaryRequest(BaseModel):
    conversation_id: str
    customer_id: str
    project_id: int


@router.post("/generate-summary/")
def generate_summary(request: SummaryRequest, db: Session = Depends(get_db)):
    """
    Generate a combined summary from transcription, bot conversation, and WhatsApp messages.
    """

    # 1️⃣ Get transcription text
    transcription = db.execute(
        select(Transcription.transcript_text).where(
            Transcription.conversation_id == request.conversation_id
        )
    ).scalar()

    if not transcription:
        transcription = "no transcription_Found"

    # 2️⃣ Get bot conversation summary
    bot_summary = db.execute(
        select(BotConversations.summary).where(
            BotConversations.customer_id == request.customer_id,
            BotConversations.project_id == request.project_id
        )
    ).scalar()

    if not bot_summary:
        bot_summary = "bot_summary not found"

    # 3️⃣ Get WhatsApp customer messages
    # First select conversation_ids for the given customer_id + project_id
    # 3️⃣ Get WhatsApp customer messages
    whatsapp_messages = []

    # Get the whatsapp conversation row for given customer + project
    conversation = (
        db.query(WhatsappConversation)
        .filter_by(customer_id=request.customer_id, project_id=request.project_id)
        .first()
    )

    if conversation:
        # ✅ use conversation.conversation_id (integer) instead of request.conversation_id (string)
        messages = (
            db.query(WhatsappConversationMessage)
            .filter_by(conversation_id=conversation.conversation_id)
            .all()
        )
        whatsapp_messages = [msg.message_text for msg in messages] if messages else []
    else:
        whatsapp_messages = []

    if not whatsapp_messages:
        whatsapp_messages = ["no whatsapp messages found"]

    whatsapp_text = "\n".join([msg for msg in whatsapp_messages if msg]) if whatsapp_messages else "no whatsapp messages found"

    # 4️⃣ Combine all text
    combined_text = f"""
You are an AI assistant that summarizes customer interactions across three channels:
1. **Call Transcription**
2. **Bot Conversation**
3. **WhatsApp Messages**

Here are the raw texts:

--- Call Transcription ---
{transcription if transcription else "No transcription available."}

--- Bot Conversation ---
{bot_summary if bot_summary else "No bot conversation available."}

--- WhatsApp Messages ---
{whatsapp_messages if whatsapp_messages else "No WhatsApp messages available."}

### Task:
- Carefully read all three sections.  
- First, summarize what the **customer said/did** across call, bot, and WhatsApp.  
- Then summarize what the **bot replied or did**.  
- Finally, give a **clear, coherent overall summary** combining all interactions, as if explaining the story of the customer’s journey.

### Output format:
Return in JSON with these keys:
- "transcription_text": short summary of the call transcription
- "bot_conversation_summary": short summary of bot conversation
- "whatsapp_messages": short summary of WhatsApp chat
- "overall_summary": detailed combined summary (customer said X in call, bot replied Y, customer followed up in WhatsApp with Z, etc.)
"""
    # 5️⃣ Call OpenAI API
    response = client.chat.completions.create(
        model="gpt-4o-mini",  #  use gpt-4o-mini or gpt-4o
        messages=[
            {"role": "system", "content": "You are a summarization assistant. Summarize the given text clearly."},
            {"role": "user", "content": combined_text}
        ],
        max_tokens=500
    )

    final_summary = response.choices[0].message.content.strip()

    # 6️ Save summary in WhatsappConversation
    whatsapp_conv = db.execute(
        select(WhatsappConversation).where(
            WhatsappConversation.customer_id == request.customer_id,
            WhatsappConversation.project_id == request.project_id
        )
    ).scalar_one_or_none()

    if whatsapp_conv:
        whatsapp_conv.summary = final_summary
        db.commit()
    else:
        raise HTTPException(status_code=404, detail="WhatsappConversation not found for given customer & project.")

    #  Return all parts in response
    return {
        "transcription_text": transcription,
        "bot_conversation_summary": bot_summary,
        "whatsapp_messages": whatsapp_text,
        "overall_summary": final_summary
    }