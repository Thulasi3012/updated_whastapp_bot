# app/services/llm/llm_service_factory.py

import logging
from typing import Optional
from app.config import settings
from app.services.llm.base_llm_service import BaseLLMService
from app.services.llm.openai_llm_service import OpenAILLMService
from app.services.llm.claude_llm_service import ClaudeLLMService
from app.services.llm.gemini_llm_service import GeminiLLMService

logger = logging.getLogger(__name__)

class LLMServiceFactory:
    """Factory class to create appropriate LLM service based on configuration"""
    
    _instance: Optional[BaseLLMService] = None
    
    @classmethod
    def get_llm_service(cls) -> BaseLLMService:
        """Get the appropriate LLM service based on configuration"""
        
        # Return cached instance if available
        if cls._instance is not None:
            return cls._instance
        
        provider = settings.LLM_PROVIDER.lower()
        
        logger.info(f"Initializing LLM service for provider: {provider}")
        
        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key not configured")
                
            cls._instance = OpenAILLMService(
                api_key=settings.OPENAI_API_KEY,
                model_name=settings.OPENAI_MODEL,
                fast_model=settings.OPENAI_FAST_MODEL,
                full_llm_model=settings.OPENAI_FULL_LLM_MODEL
            )
            
        elif provider == "claude":
            if not settings.CLAUDE_API_KEY:
                raise ValueError("Claude API key not configured")
                
            cls._instance = ClaudeLLMService(
                api_key=settings.CLAUDE_API_KEY,
                model_name=settings.CLAUDE_MODEL,
                fast_model=settings.CLAUDE_FAST_MODEL,
                full_llm_model=settings.CLAUDE_FULL_LLM_MODEL
            )
            
        elif provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise ValueError("Gemini API key not configured")
                
            cls._instance = GeminiLLMService(
                api_key=settings.GEMINI_API_KEY,
                model_name=settings.GEMINI_MODEL,
                fast_model=settings.GEMINI_FAST_MODEL,
                full_llm_model=settings.GEMINI_FULL_LLM_MODEL
            )
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
        logger.info(f"Successfully initialized {cls._instance.get_provider_name()} LLM service")
        logger.info(f"Caching enabled: {settings.ENABLE_PROVIDER_CACHING}")
        
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the cached instance (useful for testing or provider switching)"""
        cls._instance = None