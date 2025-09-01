# app/services/llm/gemini_llm_service.py

from typing import List, Dict, Any, Optional
import hashlib
import json
import asyncio
import logging
import google.generativeai as genai
from datetime import datetime, timedelta
from app.services.llm.base_llm_service import BaseLLMService
from app.config import settings

logger = logging.getLogger(__name__)

class GeminiLLMService(BaseLLMService):
    """Gemini implementation of LLM service with context caching support"""
    
    def __init__(self, api_key: str, model_name: str, fast_model: str, full_llm_model: str):
        super().__init__(api_key, model_name, fast_model, full_llm_model)
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Initialize models
        self.models = {
            "main": genai.GenerativeModel(model_name),
            "fast": genai.GenerativeModel(fast_model),
            "full": genai.GenerativeModel(full_llm_model)
        }
        
        # Context cache for Gemini
        self._context_cache = {}
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
        """Generate a chat response with Gemini context caching support"""
        
        # Check context cache
        cache_key = None
        cached_chat = None
        
        if use_cache and settings.ENABLE_PROVIDER_CACHING:
            cache_key = self.get_cache_key(messages, system_prompt)
            
            # Check if we have a cached context
            if cache_key in self._context_cache:
                if datetime.now() < self._cache_expiry[cache_key]:
                    cached_chat = self._context_cache[cache_key]
                    logger.debug("Using Gemini context cache")
                else:
                    # Cache expired
                    del self._context_cache[cache_key]
                    del self._cache_expiry[cache_key]
        
        # Select model
        if use_full_llm_mode:
            model = self.models["full"]
            model_name = self.full_llm_model
        else:
            model = self.models["fast"] if use_fast_model else self.models["main"]
            model_name = self.fast_model if use_fast_model else self.model_name
        
        logger.debug(f"Using Gemini model: {model_name}")
        
        try:
            # Convert messages to Gemini format
            gemini_messages = []
            
            # Add system prompt as the first message
            gemini_messages.append({
                "role": "user",
                "parts": [f"System: {system_prompt}\n\nLet's start our conversation."]
            })
            gemini_messages.append({
                "role": "model",
                "parts": ["Understood. I'm ready to help you with your real estate inquiries."]
            })
            
            # Handle conversation history
            if use_full_llm_mode:
                recent_messages = messages[-settings.MAX_CONVERSATION_HISTORY:] if len(messages) > settings.MAX_CONVERSATION_HISTORY else messages
            else:
                recent_messages = messages[-5:] if len(messages) > 5 else messages
            
            for message in recent_messages:
                role = "user" if message["role"] == "user" else "model"
                gemini_messages.append({
                    "role": role,
                    "parts": [message["content"]]
                })
            
            # Create or use cached chat session
            if cached_chat:
                chat = cached_chat
                # Only send the last user message
                last_user_message = [m for m in gemini_messages if m["role"] == "user"][-1]
                response = await asyncio.to_thread(
                    chat.send_message,
                    last_user_message["parts"][0]
                )
            else:
                # Start new chat with history
                chat = model.start_chat(history=gemini_messages[:-1])
                
                # Cache the chat session if caching is enabled
                if use_cache and settings.ENABLE_PROVIDER_CACHING and cache_key:
                    self._context_cache[cache_key] = chat
                    self._cache_expiry[cache_key] = datetime.now() + timedelta(minutes=settings.GEMINI_CACHE_TTL_MINUTES)
                
                # Send the last message
                last_message = gemini_messages[-1]["parts"][0]
                
                # Configure generation
                generation_config = genai.GenerationConfig(
                    temperature=settings.LLM_TEMPERATURE,
                    max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS if use_full_llm_mode else 500,
                )
                
                response = await asyncio.to_thread(
                    chat.send_message,
                    last_message,
                    generation_config=generation_config
                )
            
            response_text = response.text
            
            logger.debug(f"Generated response length: {len(response_text)} characters")
            return response_text
            
        except asyncio.TimeoutError:
            logger.error("Gemini request timed out")
            if use_full_llm_mode:
                raise Exception("I'm having trouble processing your request right now. Please try again.")
            else:
                return "Sorry, I'm thinking too hard! 😅 Let me try again - what were you asking about?"
        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            if use_full_llm_mode:
                raise Exception(f"I encountered an error: {str(e)}")
            else:
                return "Oops, my brain froze for a second there! Could you repeat that?"
    
    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings using Gemini"""
        try:
            # Use the embedding model
            model = genai.GenerativeModel('models/text-embedding-004')
            result = await asyncio.to_thread(
                model.embed_content,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error generating Gemini embeddings: {e}")
            return []
    
    def get_cache_key(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """Generate cache key for Gemini context caching"""
        # Create a deterministic key based on the conversation
        key_data = {
            "system": system_prompt[:300],  # Moderate amount of system prompt
            "messages": [(m["role"], m["content"][:100]) for m in messages[-3:]],
            "provider": "gemini"
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_provider_name(self) -> str:
        """Get the provider name"""
        return "Gemini"