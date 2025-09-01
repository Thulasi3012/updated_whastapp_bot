from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, DateTime,
    JSON, Boolean, UniqueConstraint, Index, Numeric
)
import uuid
from sqlalchemy.dialects.postgresql import JSONB,UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ChatAnalysis(Base):
    __tablename__ = "chat_analysis"

    conversation_id = Column(String, ForeignKey("bot_conversations.conversation_id", ondelete="CASCADE"), primary_key=True)
    customer_id = Column(String, ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    channel = Column(String(50), nullable=True)
    sentimental_score = Column(Float(precision=2), nullable=True)
    buyer_intent_score = Column(Float(precision=2), nullable=True)
    interest_level_score = Column(Float(precision=2), nullable=True)
    chat_length = Column(Integer, nullable=True)
    chat_tag = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversation = relationship("BotConversations", back_populates="analysis")
    customer = relationship("Customer")
    project = relationship("Project")

    _table_args_ = (
        Index("idx_chat_analysis_customer_id", "customer_id"),
        Index("idx_chat_analysis_project_id", "project_id"),
    )


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    builder_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    external_id = Column(String(255), nullable=True)
    external_source = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    _table_args_ = (
        UniqueConstraint('external_source', 'external_id', name='idx_projects_external_unique'),
        Index('idx_projects_external_id', 'external_id'),
        Index('idx_projects_external_source_id', 'external_source', 'external_id'),
    )
    
    agents = relationship("Agent", back_populates="project")
    conversations = relationship("Conversation", back_populates="project")
    calls = relationship("CallAnalysis", back_populates="project")
    documents = relationship("ProjectDocuments", back_populates="project")
    appointment_requests = relationship("AppointmentRequests", back_populates="project")
    bot_conversations = relationship("BotConversations", back_populates="project")
    keywords_association = relationship("Keyword", back_populates="project")
    whatsapp_credentials= relationship("ProjectWhatsAppCredentials",back_populates="project")
    post_visits = relationship("PostVisit", back_populates="project")


class ProjectWhatsAppCredentials(Base):
    __tablename__="project_whatsapp_credentials"
    cred_id =Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id=Column(Integer, ForeignKey("projects.id",ondelete='CASCADE'),nullable=False)
    api_key=Column(String(255),nullable=False)
    verify_token=Column(String(255),nullable=False)
    phone_number_id=Column(String(50),nullable=False)
    app_id=Column(String(255),nullable=False)
    app_secret=Column(String(255),nullable=False)
    temporary_access_token=Column(Text,nullable=True)
    long_lived_access_token=Column(Text,nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)   
    modified_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    project= relationship("Project",back_populates="whatsapp_credentials")


class Customer(Base):
    __tablename__ = "customers"
    customer_id = Column(String(100), primary_key=True, index=True)
    external_id = Column(String(100), nullable=True)
    external_source = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    preferred_language = Column(String(50), nullable=True)
    customer_type = Column(String(50), nullable=True)
    account_number = Column(String(100), nullable=True)
    customer_since = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    _table_args_ = (
        UniqueConstraint('external_source', 'external_id', name='idx_customers_external_unique'),
        Index('idx_customers_external_id', 'external_id'),
        Index('idx_customers_external_source_id', 'external_source', 'external_id'),
        Index('idx_customers_phone_number', 'phone_number'),
    )

    calls = relationship("CallAnalysis")
    conversations = relationship("Conversation", back_populates="customer")
    appointment_requests = relationship("AppointmentRequests", back_populates="customer")
    bot_conversations = relationship("BotConversations", back_populates="customer")
    whatsapp_conversations = relationship("WhatsappConversation", back_populates="customer")
    post_visits = relationship("PostVisit", back_populates="customer")

class Agent(Base):
    __tablename__ = "agents"
    agent_id = Column(String(100), primary_key=True, index=True)
    agent_name = Column(String(255), nullable=False)
    agent_email = Column(String(255), nullable=True)
    department = Column(String(100), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    external_id = Column(String(255), nullable=True)
    external_source = Column(String(100), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    _table_args_ = (
        UniqueConstraint('external_source', 'external_id', name='idx_agents_external_unique'),
        Index('idx_agents_external_id', 'external_id'),
        Index('idx_agents_external_project', 'external_source', 'project_id'),
    )
    
    project = relationship("Project", back_populates="agents")
    calls = relationship("CallAnalysis", back_populates="agent")
    conversations = relationship("Conversation", back_populates="agent")

class Conversation(Base):
    __tablename__ = "conversations"
    
    conversation_id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"))
    customer_id = Column(String, ForeignKey("customers.customer_id"))
    project_id = Column(Integer, ForeignKey("projects.id")) 
    call_start_time = Column(DateTime)
    call_end_time = Column(DateTime)
    call_duration_seconds = Column(Integer)
    call_status = Column(String)
    call_direction = Column(String)
    call_purpose = Column(String)
    call_reference = Column(String, nullable=True)
    source_language = Column(String)
    language_detected = Column(String, nullable=True)
    call_sentiment = Column(String, nullable=True)
    call_tags = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    agent = relationship("Agent", back_populates="conversations")
    customer = relationship("Customer", back_populates="conversations")
    project = relationship("Project", back_populates="conversations")
    recordings = relationship("Recording", back_populates="conversation")
    transcriptions = relationship("Transcription", back_populates="conversation")
    analysis = relationship("CallAnalysis", uselist=False, back_populates="conversation")
    webhook_audits = relationship("WebhookAudit", back_populates="conversation")

class Recording(Base):
    __tablename__ = "recordings"
    
    recording_id = Column(String, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"))
    file_name = Column(String)
    storage_bucket = Column(String)
    storage_path = Column(String)
    file_format = Column(String)
    file_size_bytes = Column(Integer)
    recording_duration_seconds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="recordings")
    transcription = relationship("Transcription", uselist=False, back_populates="recording")

class Transcription(Base):
    __tablename__ = "transcriptions"
    
    transcription_id = Column(String, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"))
    recording_id = Column(String, ForeignKey("recordings.recording_id"))
    job_id = Column(String)
    transcript_text = Column(Text)
    transcript_file_path = Column(String, nullable=True)
    transcript_storage_bucket = Column(String, nullable=True)
    status = Column(String)
    error_message = Column(String, nullable=True)
    diarization_enabled = Column(Boolean, default=False)
    diarized_segments = Column(JSONB, nullable=True)
    progress = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    _table_args_ = (
        Index('idx_transcriptions_job_id', 'job_id'),
    )

    conversation = relationship("Conversation", back_populates="transcriptions")
    recording = relationship("Recording", back_populates="transcription")
    segments = relationship("TranscriptSegment", back_populates="transcription")
    webhook_audits = relationship("WebhookAudit", back_populates="transcription")

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    
    segment_id = Column(String, primary_key=True, index=True)
    transcription_id = Column(String, ForeignKey("transcriptions.transcription_id"))
    speaker_label = Column(String)
    segment_text = Column(Text)
    start_time = Column(Float)
    end_time = Column(Float)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to transcription
    transcription = relationship("Transcription", back_populates="segments")

class CallAnalysis(Base):
    __tablename__ = "call_analyses"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), unique=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    agent_id = Column(String, ForeignKey("agents.agent_id"))
    customer_id = Column(String, ForeignKey("customers.customer_id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    direction = Column(String)
    purpose = Column(String)
    language = Column(String)
    buyer_intent_score = Column(Float)
    interest_level = Column(Float)
    objection_level = Column(Float)
    sentiment_score = Column(Float)
    call_rating = Column(Float)
    key_insights = Column(JSONB)
    transcript_text = Column(Text)
    diarized_transcript = Column(JSONB)
    analysis_result = Column(JSONB)

    _table_args_ = (
        Index('ix_call_analyses_conversation_id', 'conversation_id'),
    )
    
    project = relationship("Project", back_populates="calls")
    agent = relationship("Agent", back_populates="calls")
    customer = relationship("Customer", back_populates="calls")
    improvement_suggestions = relationship("ImprovementSuggestion", back_populates="call")
    conversation = relationship("Conversation", back_populates="analysis")
    topics = relationship("ConversationTopic", back_populates="call")

class ImprovementSuggestion(Base):
    __tablename__ = "improvement_suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("call_analyses.id"))
    suggestion = Column(Text)
    category = Column(String)
    priority = Column(Integer)

    call = relationship("CallAnalysis", back_populates="improvement_suggestions")

class ConversationTopic(Base):
    __tablename__ = "conversation_topics"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("call_analyses.id"))
    topic = Column(String)
    importance_score = Column(Float)
    segment_ids = Column(JSONB)

    call = relationship("CallAnalysis", back_populates="topics")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    key_id = Column(String, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    owner_name = Column(String, nullable=False)
    owner_email = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    
    def _repr_(self):
        return f"<APIKey(key_id='{self.key_id}', owner='{self.owner_name}', active={self.is_active})>"

class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    builder_name = Column(String, nullable=False)
    keywords = Column(JSONB, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String)

    _table_args_ = (
        UniqueConstraint('project_id', 'builder_name', name='keywords_project_id_builder_name_key'),
    )

    project = relationship("Project", back_populates="keywords_association")

class ProjectDocuments(Base):
    __tablename__ = "project_documents"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    document_type = Column(String(50))
    filename = Column(String(255))
    gcs_path = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    project = relationship("Project", back_populates="documents")

class AppointmentRequests(Base):
    __tablename__ = "appointment_requests"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(100), ForeignKey("bot_conversations.conversation_id"))
    customer_id = Column(String(100), ForeignKey("customers.customer_id"), index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    requested_date = Column(DateTime(timezone=True))
    requested_time = Column(String(20))
    status = Column(String(50))
    assigned_agent_id = Column(String(100))
    pickup_required = Column(Boolean, default=False)
    pickup_address = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    _table_args_ = (
        Index('idx_appointments_customer_id', 'customer_id'),
        Index('idx_appointments_project_id', 'project_id')
    )

    conversation = relationship("BotConversations", back_populates="appointments")
    customer = relationship("Customer", back_populates="appointment_requests")
    project = relationship("Project", back_populates="appointment_requests")

class BotConversations(Base):
    __tablename__ = "bot_conversations"
    conversation_id = Column(String(100), primary_key=True)
    customer_id = Column(String(100), ForeignKey("customers.customer_id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    start_time = Column(DateTime(timezone=True), default=datetime.utcnow)
    end_time = Column(DateTime(timezone=True))
    channel = Column(String(50))
    sentiment_score = Column(Numeric(3, 1))
    summary = Column(Text)
    buyer_intent_score = Column(Numeric(3, 1))
    interest_level_score = Column(Numeric(3, 1))

    customer = relationship("Customer", back_populates="bot_conversations")
    project = relationship("Project", back_populates="bot_conversations")
    messages = relationship("BotConversationMessages", back_populates="conversation")
    appointments = relationship("AppointmentRequests", back_populates="conversation")
    topics = relationship("BotConversationTopics", back_populates="conversation")
    analysis = relationship("ChatAnalysis", uselist=False, back_populates="conversation")

class BotConversationMessages(Base):
    __tablename__ = "bot_conversation_messages"
    message_id = Column(String(100), primary_key=True)
    conversation_id = Column(String(100), ForeignKey("bot_conversations.conversation_id"), index=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    sender_type = Column(String(20))
    message_text = Column(Text)
    message_type = Column(String(50))
    sentiment_label = Column(String(20))
    intent_detected = Column(String(100))

    conversation = relationship("BotConversations", back_populates="messages")

class BotConversationTopics(Base):
    __tablename__ = "bot_conversation_topics"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(100), ForeignKey("bot_conversations.conversation_id"), index=True)
    topic = Column(String(100))
    topic_category = Column(String(50))
    mention_count = Column(Integer, default=1)
    sentiment_score = Column(Numeric(3, 1))

    conversation = relationship("BotConversations", back_populates="topics")

class WebhookAudit(Base):
    __tablename__ = "webhook_audit"
    webhook_id = Column(String(100), primary_key=True)
    conversation_id = Column(String(100), ForeignKey("conversations.conversation_id"), nullable=False)
    transcription_id = Column(String(100), ForeignKey("transcriptions.transcription_id"), nullable=True)
    webhook_url = Column(String(500), nullable=False)
    webhook_secret_hash = Column(String(255), nullable=True)
    event_type = Column(String(50), default='transcription.completed')
    payload_size_bytes = Column(Integer, nullable=True)
    attempt_number = Column(Integer, default=1)
    status = Column(String(50), default='pending')
    http_status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    conversation = relationship("Conversation", back_populates="webhook_audits")
    transcription = relationship("Transcription", back_populates="webhook_audits")

class WhatsappConversation(Base):
    __tablename__ = "whatsapp_conversations"

    conversation_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    channel = Column(String(50), default="whatsapp")
    sentiment = Column(Float, nullable=True)
    buyer_intent_score = Column(Float, nullable=True)
    interest_level_score = Column(Float, nullable=True)
    whatsapp_number = Column(String(20), index=True, nullable=True)
    conversation_sid = Column(String(100), nullable=True)
    summary = Column(Text, nullable=True)   # ✅ new column

    customer = relationship("Customer", back_populates="whatsapp_conversations")
    messages = relationship("WhatsappConversationMessage", back_populates="conversation")

class WhatsappConversationMessage(Base):
    __tablename__ = "whatsapp_conversation_messages"

    message_id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("whatsapp_conversations.conversation_id"), index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender_type = Column(String(20), nullable=True)
    message_text = Column(Text, nullable=True)
    message_type = Column(String(50), nullable=True)
    sentiment = Column(String(20), nullable=True)
    intent_detected = Column(String(100), nullable=True)
    twilio_message_sid = Column(String(100), nullable=True)

    conversation = relationship("WhatsappConversation", back_populates="messages")

class WhatsappTemplate(Base):
    __tablename__ = "whatsapp_templates"
    template_id = Column(Integer, primary_key=True)
    template_name = Column(String(100), unique=True, nullable=True)
    template_text = Column(Text, nullable=True)
    variables = Column(JSONB, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TemplateUsageLog(Base):
    __tablename__ = "template_usage_log"
    log_id = Column(Integer, primary_key=True)
    template_name = Column(String(100), index=True, nullable=True)
    recipient_number = Column(String(20), nullable=True)
    message_sid = Column(String(100), nullable=True)
    conversation_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PostVisit(Base):
    __tablename__ = "post_visits"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True) # FK to Project
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="post_visits")
    project = relationship("Project", back_populates="post_visits")
