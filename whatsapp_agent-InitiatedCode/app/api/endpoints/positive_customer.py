from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, String, literal
from typing import Optional, Literal, Dict, Any, List
from app.database.database import get_db
from app.database import models
import logging
import time

router = APIRouter()

# ---------- Logging setup ----------
logger = logging.getLogger("sentiments")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

def _normalize_sentiment(label: Optional[str]) -> Optional[str]:
    """Normalize common sentiment variants (string labels)."""
    if not label:
        return None
    s = str(label).strip().lower()
    mapping = {
        # very positive
        "very_positive": "very positive", "very-positive": "very positive",
        "vpositive": "very positive", "v pos": "very positive",
        # very negative (add these to match chat_analysis style)
        "very_negative": "very negative", "very-negative": "very negative", "vneg": "very negative", "v neg": "very negative",
        # positive / negative / neutral
        "pos": "positive", "positive": "positive", "good": "positive",
        "neg": "negative", "negative": "negative", "bad": "negative",
        "neu": "neutral", "neutral": "neutral"
    }
    return mapping.get(s, s)

def _score_to_sentiment(score: Optional[float]) -> Optional[str]:
    """Map conversation-level float score to label."""
    if score is None:
        return None
    try:
        v = float(score)
    except (TypeError, ValueError):
        return None
    if v >= 0.6:
        return "very positive"
    elif v >= 0.2:
        return "positive"
    elif v <= -0.6:
        return "very negative"
    elif v <= -0.2:
        return "negative"
    else:
        return "neutral"

def get_customer_label(db: Session, customer_id: int) -> Optional[str]:
    """
    Priority based label check:
      1. PostVisit → post_visit_template
      2. AppointmentRequests → appointment_template
      3. Default → welcome_template
    """
    if db.query(models.PostVisit).filter_by(customer_id=customer_id).first():
        return "post_visit_template"
    elif db.query(models.AppointmentRequests).filter_by(customer_id=customer_id).first():
        return "appointment_template"
    else:
        return "welcome_template"

@router.get("/sentiments_by_project", tags=["Customer Sentiments"])
def get_all_sentiments(
    project_id: int,
    sentiment: Optional[Literal["very positive", "positive", "negative", "neutral"]] = Query(
        None, description="Filter sentiments"
    ),
    db: Session = Depends(get_db)
):
    """
    Fetch sentiments from:
      - Conversation.call_sentiment (calls) [BASE]
      - BotConversations (direct base, no sentiment column → None)
      - ChatAnalysis.chat_tag (joined with BotConversations)
      - WhatsappConversations.sentiment (FLOAT conversation-level)
    Add label depending on whether customer exists in PostVisit / AppointmentRequests / fallback Welcome.
    """
    t0 = time.time()
    logger.info(f"[START] sentiments_by_project project_id={project_id}, sentiment={sentiment}")

    results: List[Dict[str, Any]] = []
    per_source_counts = {"conversation": 0, "bot_conversation": 0, "chat_analysis": 0, "whatsapp_conversation": 0}

    try:
        # ---- 1) Conversation (base) ----
        conv_q = (
            db.query(
                models.Conversation.project_id,
                models.Conversation.customer_id,
                models.Conversation.call_sentiment
            )
            .filter(models.Conversation.project_id == project_id)
        )
        if sentiment:
            conv_q = conv_q.filter(func.lower(models.Conversation.call_sentiment) == sentiment.lower())

        conv_rows = conv_q.all()
        logger.info(f"[conversation] rows: {len(conv_rows)}")

        for row in conv_rows:
            sent = _normalize_sentiment(row.call_sentiment)
            if sentiment and sent != sentiment:
                continue
            if sent:
                label = get_customer_label(db, row.customer_id)
                results.append({
                    "project_id": row.project_id,
                    "customer_id": row.customer_id,
                    "sentiment": sent,
                    "source": "conversation",
                    "label": label
                })
        per_source_counts["conversation"] = sum(1 for r in results if r["source"] == "conversation")

        # ---- 2) BotConversations (direct base) ----
        bot_q = (
            db.query(
                models.BotConversations.project_id,
                models.BotConversations.customer_id,
                literal(None).label("sentiment"),
                models.BotConversations.conversation_id,
                models.BotConversations.start_time,
                models.BotConversations.end_time,
                models.BotConversations.channel
            )
            .filter(models.BotConversations.project_id == project_id)
        )
        bot_rows = bot_q.all()
        logger.info(f"[bot_conversation] rows: {len(bot_rows)}")

        for row in bot_rows:
            label = get_customer_label(db, row.customer_id)
            results.append({
                "project_id": row.project_id,
                "customer_id": row.customer_id,
                "sentiment": None,  # BotConversations has no sentiment
                "conversation_id": row.conversation_id,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "channel": row.channel,
                "source": "bot_conversation",
                "label": label
            })
        per_source_counts["bot_conversation"] = sum(1 for r in results if r["source"] == "bot_conversation")

        # ---- 3) ChatAnalysis + BotConversations (joined) ----
        chat_q = (
            db.query(
                models.ChatAnalysis.project_id,
                models.ChatAnalysis.customer_id,
                models.ChatAnalysis.chat_tag,
                models.BotConversations.conversation_id,
                models.BotConversations.start_time,
                models.BotConversations.end_time,
                models.BotConversations.channel
            )
            .join(
                models.BotConversations,
                models.ChatAnalysis.conversation_id == models.BotConversations.conversation_id
            )
            .filter(models.ChatAnalysis.project_id == project_id)
        )
        if sentiment:
            chat_q = chat_q.filter(
                func.lower(cast(models.ChatAnalysis.chat_tag["sentiment"].astext, String)) == sentiment.lower()
            )
        chat_rows = chat_q.all()
        logger.info(f"[chat_analysis] rows: {len(chat_rows)}")

        for row in chat_rows:
            tag = row.chat_tag.get("sentiment").strip().lower() if row.chat_tag and "sentiment" in row.chat_tag else None
            if sentiment and tag != sentiment.lower():
                continue
            if tag:
                label = get_customer_label(db, row.customer_id)
                results.append({
                    "project_id": row.project_id,
                    "customer_id": row.customer_id,
                    "sentiment": _normalize_sentiment(tag),
                    "conversation_id": row.conversation_id,
                    "start_time": row.start_time,
                    "end_time": row.end_time,
                    "channel": row.channel,
                    "source": "chat_analysis",
                    "label": label
                })
        per_source_counts["chat_analysis"] = sum(1 for r in results if r["source"] == "chat_analysis")

        # ---- 4) WhatsappConversations (conversation-level FLOAT) ----
        whats_q = (
            db.query(
                models.WhatsappConversation.project_id,
                models.WhatsappConversation.customer_id,
                models.WhatsappConversation.sentiment  # FLOAT score
            )
            .filter(models.WhatsappConversation.project_id == project_id)
        )
        # NOTE: do NOT DB-filter by label here; we map float->label in Python.

        whats_rows = whats_q.all()
        logger.info(f"[whatsapp_conversation] rows: {len(whats_rows)}")

        for w_row in whats_rows:
            score = w_row.sentiment  # float or None
            sent = _score_to_sentiment(score)  # map to label
            if sentiment and sent != sentiment:
                continue
            if sent:
                label = get_customer_label(db, w_row.customer_id)
                results.append({
                    "project_id": w_row.project_id,
                    "customer_id": w_row.customer_id,
                    "sentiment": sent,
                    "source": "whatsapp_conversation",
                    "label": label
                })
        per_source_counts["whatsapp_conversation"] = sum(
            1 for r in results if r["source"] == "whatsapp_conversation"
        )

        # ---- Summary ----
        summary: Dict[str, int] = {}
        for r in results:
            if r["sentiment"]:
                summary[r["sentiment"]] = summary.get(r["sentiment"], 0) + 1

        overall_count = len(results)
        if overall_count == 0:
            logger.warning(f"[EMPTY] No results for project_id={project_id} sentiment={sentiment}")

        dt = round((time.time() - t0) * 1000)
        logger.info(f"[DONE] total={overall_count} per_source={per_source_counts} time_ms={dt}")

        return {
            "count": overall_count,
            "per_source_counts": per_source_counts,
            "summary": summary,
            "data": results
        }

    except Exception as e:
        logger.exception(f"[ERROR] sentiments_by_project failed for project_id={project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch sentiments")
