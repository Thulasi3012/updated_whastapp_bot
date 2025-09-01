import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import os
from app.config import settings
from app.api.endpoints import chat, project_whatsapp_credentials,positive_customer,send_template,summary,list_customer
from fastapi import APIRouter, Depends
from app.database.database import get_db
from app.services import project_whatsapp_credentials as service
import requests
from app.database import models
from sqlalchemy.orm import Session
from app.database.models import AppointmentRequests, Customer, ProjectWhatsAppCredentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=f"Real Estate Sales whatsappChatbot API - {settings.CHAT_MODE.upper()} Mode with {settings.LLM_PROVIDER.upper()}",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Chat-Mode"] = settings.CHAT_MODE
    response.headers["X-LLM-Provider"] = settings.LLM_PROVIDER
    
    # Log slow requests (different thresholds for different modes and providers)
    slow_threshold = 3.0 if settings.CHAT_MODE == "full_llm" else 2.0
    if settings.LLM_PROVIDER == "gemini":
        slow_threshold += 0.5  # Gemini might be slightly slower
    
    if process_time > slow_threshold:
        logger.warning(f"Slow request: {request.method} {request.url.path} took {process_time:.3f}s in {settings.CHAT_MODE} mode with {settings.LLM_PROVIDER}")
    
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."}
    )

# Include routers
app.include_router(chat.router)
app.include_router(project_whatsapp_credentials.router)
app.include_router(positive_customer.router)
app.include_router(send_template.router)
app.include_router(summary.router)
app.include_router(list_customer.router)

# Root endpoint with mode and provider information
@app.get("/")
async def root():
    # Get model info based on provider
    if settings.LLM_PROVIDER == "openai":
        model_info = {
            "provider": "OpenAI",
            "model": settings.OPENAI_FULL_LLM_MODEL if settings.CHAT_MODE == "full_llm" else settings.OPENAI_MODEL,
            "cache_type": "Cached Input (seed-based)" if settings.ENABLE_PROVIDER_CACHING else "Disabled"
        }
    elif settings.LLM_PROVIDER == "claude":
        model_info = {
            "provider": "Claude (Anthropic)",
            "model": settings.CLAUDE_FULL_LLM_MODEL if settings.CHAT_MODE == "full_llm" else settings.CLAUDE_MODEL,
            "cache_type": "Prompt Caching" if settings.ENABLE_PROVIDER_CACHING else "Disabled"
        }
    elif settings.LLM_PROVIDER == "gemini":
        model_info = {
            "provider": "Gemini (Google)",
            "model": settings.GEMINI_FULL_LLM_MODEL if settings.CHAT_MODE == "full_llm" else settings.GEMINI_MODEL,
            "cache_type": "Context Caching" if settings.ENABLE_PROVIDER_CACHING else "Disabled"
        }
    
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "chat_mode": settings.CHAT_MODE,
        "llm_provider": settings.LLM_PROVIDER,
        "description": f"Chat mode: {settings.CHAT_MODE.upper()} with {settings.LLM_PROVIDER.upper()}",
        "model_info": model_info,
        "features": {
            "hybrid_mode": settings.CHAT_MODE == "hybrid",
            "full_llm_mode": settings.CHAT_MODE == "full_llm",
            "quick_responses": settings.CHAT_MODE == "hybrid",
            "complete_project_context": settings.CHAT_MODE == "full_llm",
            "provider_caching": settings.ENABLE_PROVIDER_CACHING
        }
    }

# Health check endpoint with provider info
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "chat_mode": settings.CHAT_MODE,
        "llm_provider": settings.LLM_PROVIDER,
        "timestamp": time.time()
    }

# Configuration endpoint for debugging
@app.get("/config")
async def get_config():
    # Get provider-specific config
    provider_config = {}
    
    if settings.LLM_PROVIDER == "openai":
        provider_config = {
            "model": settings.OPENAI_FULL_LLM_MODEL if settings.CHAT_MODE == "full_llm" else settings.OPENAI_MODEL,
            "cache_seed": settings.OPENAI_CACHE_SEED if settings.ENABLE_PROVIDER_CACHING else None
        }
    elif settings.LLM_PROVIDER == "claude":
        provider_config = {
            "model": settings.CLAUDE_FULL_LLM_MODEL if settings.CHAT_MODE == "full_llm" else settings.CLAUDE_MODEL,
            "cache_ttl_minutes": settings.CLAUDE_CACHE_TTL_MINUTES if settings.ENABLE_PROVIDER_CACHING else None,
            "max_tokens": settings.CLAUDE_MAX_TOKENS
        }
    elif settings.LLM_PROVIDER == "gemini":
        provider_config = {
            "model": settings.GEMINI_FULL_LLM_MODEL if settings.CHAT_MODE == "full_llm" else settings.GEMINI_MODEL,
            "cache_ttl_minutes": settings.GEMINI_CACHE_TTL_MINUTES if settings.ENABLE_PROVIDER_CACHING else None,
            "max_output_tokens": settings.GEMINI_MAX_OUTPUT_TOKENS
        }
    
    return {
        "chat_mode": settings.CHAT_MODE,
        "llm_provider": settings.LLM_PROVIDER,
        "provider_config": provider_config,
        "max_tokens": settings.MAX_TOKENS,
        "max_conversation_history": settings.MAX_CONVERSATION_HISTORY,
        "timeout": settings.LLM_TIMEOUT,
        "quick_responses_enabled": settings.CHAT_MODE == "hybrid",
        "provider_caching_enabled": settings.ENABLE_PROVIDER_CACHING,
        "version": settings.APP_VERSION
    }

@app.on_event("startup")
async def startup_event():
    """Log startup information with provider details"""
    logger.info("="*60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"💬 Chat Mode: {settings.CHAT_MODE.upper()}")
    logger.info(f"🤖 LLM Provider: {settings.LLM_PROVIDER.upper()}")
    
    # Provider-specific startup info
    if settings.LLM_PROVIDER == "openai":
        logger.info("🟢 OpenAI Configuration:")
        logger.info(f"   - Model: {settings.OPENAI_FULL_LLM_MODEL if settings.CHAT_MODE == 'full_llm' else settings.OPENAI_MODEL}")
        logger.info(f"   - Embeddings: {settings.OPENAI_EMBEDDING_MODEL}")
        if settings.ENABLE_PROVIDER_CACHING:
            logger.info(f"   - Cache Type: Cached Input (seed: {settings.OPENAI_CACHE_SEED})")
    
    elif settings.LLM_PROVIDER == "claude":
        logger.info("🟣 Claude (Anthropic) Configuration:")
        logger.info(f"   - Model: {settings.CLAUDE_FULL_LLM_MODEL if settings.CHAT_MODE == 'full_llm' else settings.CLAUDE_MODEL}")
        if settings.ENABLE_PROVIDER_CACHING:
            logger.info(f"   - Cache Type: Prompt Caching (TTL: {settings.CLAUDE_CACHE_TTL_MINUTES} min)")
        logger.info("   - Note: Embeddings will fall back to OpenAI or be disabled")
    
    elif settings.LLM_PROVIDER == "gemini":
        logger.info("🔵 Gemini (Google) Configuration:")
        logger.info(f"   - Model: {settings.GEMINI_FULL_LLM_MODEL if settings.CHAT_MODE == 'full_llm' else settings.GEMINI_MODEL}")
        if settings.ENABLE_PROVIDER_CACHING:
            logger.info(f"   - Cache Type: Context Caching (TTL: {settings.GEMINI_CACHE_TTL_MINUTES} min)")
    
    # General settings
    logger.info(f"⚙️  General Settings:")
    logger.info(f"   - Max Tokens: {settings.MAX_TOKENS}")
    logger.info(f"   - Temperature: {settings.LLM_TEMPERATURE}")
    logger.info(f"   - Timeout: {settings.LLM_TIMEOUT}s")
    logger.info(f"   - Max Conversation History: {settings.MAX_CONVERSATION_HISTORY}")
    logger.info(f"   - Provider Caching: {'Enabled' if settings.ENABLE_PROVIDER_CACHING else 'Disabled'}")
    
    logger.info("="*60)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=settings.DEBUG)