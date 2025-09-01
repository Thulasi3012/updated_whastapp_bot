import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database.database import get_db
from app.database.models import (
    CallAnalysis,
    BotConversations,
    WhatsappConversation,
    Conversation,
    WhatsappConversationMessage,
    Transcription,
)

# --- Setup Logger ---
logger = logging.getLogger("list_customer_logger")
logger.setLevel(logging.DEBUG)  # Detailed logs for debugging
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
)
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

router = APIRouter(prefix="/api/List_Customer", tags=["List_Customer"])


# --- Response Schemas ---
class ConversationResponse(BaseModel):
    project_id: int
    conversation_id: str
    customer_id: str
    timestamp: str
    source: str  # added explicitly


class ConversationTextResponse(BaseModel):
    conversation_id: str
    mode: str
    messages: List[str]


# --- API Endpoint to get conversations ---
@router.get("/", response_model=List[ConversationResponse])
def get_conversations(
    project_id: int,
    mode: str = Query(..., description="Select mode", enum=["calls", "bot", "whatsapp"]),
    db: Session = Depends(get_db),
):
    logger.info(f"Fetching conversations | project_id={project_id}, mode={mode}")

    try:
        if mode == "calls":
            logger.debug("Querying CallAnalysis table...")
            conversations = (
                db.query(
                    Conversation.conversation_id,
                    Conversation.customer_id,
                    Conversation.created_at.label("timestamp"),
                )
                .filter(Conversation.project_id == project_id)
                .all()
            )

        elif mode == "bot":
            logger.debug("Querying BotConversations table...")
            conversations = (
                db.query(
                    BotConversations.conversation_id,
                    BotConversations.customer_id,
                    BotConversations.start_time.label("timestamp"),
                )
                .filter(BotConversations.project_id == project_id)
                .all()
            )

        elif mode == "whatsapp":
            logger.debug("Querying WhatsappConversation table...")
            conversations = (
                db.query(
                    WhatsappConversation.conversation_id,
                    WhatsappConversation.customer_id,
                    WhatsappConversation.start_time.label("timestamp"),
                )
                .filter(WhatsappConversation.project_id == project_id)
                .all()
            )

        else:
            logger.error(f"Invalid mode received: {mode}")
            raise HTTPException(status_code=400, detail="Invalid mode selected")

        if not conversations:
            logger.warning(f"No {mode} conversations found for project_id={project_id}")
            raise HTTPException(
                status_code=404,
                detail=f"No {mode} conversations found for project_id={project_id}",
            )

        result = [
            ConversationResponse(
                project_id=project_id,
                conversation_id=str(c.conversation_id),
                customer_id=str(c.customer_id),
                timestamp=str(c.timestamp) if c.timestamp else "N/A",
                source=mode,
            )
            for c in conversations
        ]

        logger.info(
            f"Successfully fetched {len(result)} {mode} conversations for project_id={project_id}"
        )
        return result

    except ValueError as ve:
        logger.exception("Invalid format error")
        raise HTTPException(status_code=422, detail=f"Invalid format: {str(ve)}")

    except Exception as e:
        logger.exception("Unexpected error while fetching conversations")
        raise HTTPException(status_code=500, detail="Internal server error")


# --- API Endpoint to get conversation text/messages ---
@router.get("/conversation-text/", response_model=ConversationTextResponse)
def get_conversation_text(
    conversation_id: str,
    mode: str = Query(..., description="Select mode", enum=["calls", "bot", "whatsapp"]),
    db: Session = Depends(get_db),
):
    logger.info(f"Fetching conversation text | conversation_id={conversation_id}, mode={mode}")
    messages = []

    try:
        if mode == "calls":
            logger.debug("Querying Transcription table...")
            transcription = (
                db.query(Transcription.transcript_text)
                .filter(Transcription.conversation_id == conversation_id)
                .scalar()
            )
            messages = [transcription] if transcription else []
            if not messages:
                logger.warning(f"No call transcription found for conversation_id={conversation_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"No call transcription found for conversation_id={conversation_id}",
                )

        elif mode == "bot":
            logger.debug("Querying BotConversations table...")
            bot_msgs = (
                db.query(BotConversations.summary)
                .filter(BotConversations.conversation_id == conversation_id)
                .all()
            )
            messages = [m.summary for m in bot_msgs if m.summary] if bot_msgs else []
            if not messages:
                logger.warning(f"No bot conversation found for conversation_id={conversation_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"No bot conversation found for conversation_id={conversation_id}",
                )

        elif mode == "whatsapp":
            logger.debug("Querying WhatsappConversationMessage table...")
            whatsapp_msgs = (
                db.query(WhatsappConversationMessage.message_text)
                .filter(WhatsappConversationMessage.conversation_id == conversation_id)
                .all()
            )
            messages = [m.message_text for m in whatsapp_msgs if m.message_text] if whatsapp_msgs else []
            if not messages:
                logger.warning(f"No WhatsApp messages found for conversation_id={conversation_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"No WhatsApp messages found for conversation_id={conversation_id}",
                )

        else:
            logger.error(f"Invalid mode received: {mode}")
            raise HTTPException(status_code=400, detail="Invalid mode selected")

        logger.info(f"Successfully fetched {len(messages)} messages for conversation_id={conversation_id}")
        return ConversationTextResponse(
            conversation_id=conversation_id,
            mode=mode,
            messages=messages,
        )

    except ValueError as ve:
        logger.exception("Invalid format error")
        raise HTTPException(status_code=422, detail=f"Invalid format: {str(ve)}")

    except Exception as e:
        logger.exception("Unexpected error while fetching conversation text")
        raise HTTPException(status_code=500, detail="Internal server error")
