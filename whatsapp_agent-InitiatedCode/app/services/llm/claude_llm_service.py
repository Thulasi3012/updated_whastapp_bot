# app/services/llm/claude_llm_service.py

from typing import List, Dict, Any, Optional
import hashlib
import json
import asyncio
import logging
from anthropic import AsyncAnthropic
from datetime import datetime, timedelta
from app.services.llm.base_llm_service import BaseLLMService
from app.config import settings

logger = logging.getLogger(__name__)

class ClaudeLLMService(BaseLLMService):
    """Claude implementation of LLM service with prompt caching support"""
    
    def __init__(self, api_key: str, model_name: str, fast_model: str, full_llm_model: str):
        super().__init__(api_key, model_name, fast_model, full_llm_model)
        
        # Initialize Claude client
        self.client = AsyncAnthropic(api_key=api_key)
        
        # Cache for prompt caching (stores cache control metadata)
        self._prompt_cache = {}
        self._cache_expiry = {}
        
    async def generate_chat_response(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: str, 
        use_fast_model: bool = True,
        use_full_llm_mode: bool = False,
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """Generate a chat response with Claude prompt caching support"""
        
        # Check if we have a cached prompt
        cache_key = None
        if use_cache and settings.ENABLE_PROVIDER_CACHING:
            cache_key = self.get_cache_key(messages, system_prompt)
            
            # Check if cache is still valid
            if cache_key in self._cache_expiry:
                if datetime.now() < self._cache_expiry[cache_key]:
                    logger.debug("Using Claude prompt cache")
                else:
                    # Cache expired, remove it
                    del self._prompt_cache[cache_key]
                    del self._cache_expiry[cache_key]
        
        # Convert messages to Claude format
        claude_messages = []
        
        # Handle conversation history
        if use_full_llm_mode:
            recent_messages = messages[-settings.MAX_CONVERSATION_HISTORY:] if len(messages) > settings.MAX_CONVERSATION_HISTORY else messages
        else:
            recent_messages = messages[-5:] if len(messages) > 5 else messages
        
        for message in recent_messages:
            claude_messages.append({
                "role": message["role"],
                "content": message["content"]
            })
        
        # Select model
        if use_full_llm_mode:
            model = self.full_llm_model
            logger.debug(f"Using Claude full LLM mode with model: {model}")
        else:
            model = self.fast_model if use_fast_model else self.model_name
            logger.debug(f"Using Claude hybrid mode with model: {model}")
        
        try:
            # Prepare the request
            request_params = {
                "model": model,
                "max_tokens": settings.CLAUDE_MAX_TOKENS if use_full_llm_mode else 300,
                "temperature": settings.LLM_TEMPERATURE,
                "messages": claude_messages,
                "system": system_prompt
            }
            
            # Add cache control if enabled and we have a cache key
            if use_cache and settings.ENABLE_PROVIDER_CACHING and cache_key:
                # Claude's prompt caching works by marking the system message
                request_params["system"] = [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
                
                # Store cache metadata
                self._prompt_cache[cache_key] = True
                self._cache_expiry[cache_key] = datetime.now() + timedelta(minutes=settings.CLAUDE_CACHE_TTL_MINUTES)
            
            # Generate response
            timeout = settings.LLM_TIMEOUT if not use_full_llm_mode else settings.LLM_TIMEOUT + 5
            
            response = await asyncio.wait_for(
                self.client.messages.create(**request_params),
                timeout=timeout
            )
            
            response_text = response.content[0].text
            
            logger.debug(f"Generated response length: {len(response_text)} characters")
            return response_text
            
        except asyncio.TimeoutError:
            logger.error("Claude request timed out")
            if use_full_llm_mode:
                raise Exception("I'm having trouble processing your request right now. Please try again.")
            else:
                return "Sorry, I'm thinking too hard! 😅 Let me try again - what were you asking about?"
        except Exception as e:
            logger.error(f"Error generating Claude response: {e}")
            if use_full_llm_mode:
                raise Exception(f"I encountered an error: {str(e)}")
            else:
                return "Oops, my brain froze for a second there! Could you repeat that?"
    
    async def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings - Claude doesn't have native embeddings,
        so we'll need to use OpenAI for this or return empty
        """
        logger.warning("Claude doesn't support embeddings natively. Consider using OpenAI for embeddings.")
        return []
    
    def get_cache_key(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """Generate cache key for Claude prompt caching"""
        # Create a deterministic key based on the conversation
        key_data = {
            "system": system_prompt[:500],  # More of system prompt for Claude
            "messages": [(m["role"], m["content"][:100]) for m in messages[-3:]],
            "provider": "claude"
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_provider_name(self) -> str:
        """Get the provider name"""
        return "Claude"