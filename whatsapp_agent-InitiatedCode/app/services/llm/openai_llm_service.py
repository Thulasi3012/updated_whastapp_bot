# app/services/llm/openai_llm_service.py

from typing import List, Dict, Any, Optional
import hashlib
import json
import asyncio
import logging
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from app.services.llm.base_llm_service import BaseLLMService
from app.config import settings

logger = logging.getLogger(__name__)

class OpenAILLMService(BaseLLMService):
    """OpenAI implementation of LLM service with cached input support"""
    
    def __init__(self, api_key: str, model_name: str, fast_model: str, full_llm_model: str):
        super().__init__(api_key, model_name, fast_model, full_llm_model)
        
        # Initialize models
        self.llm = self._initialize_llm()
        self.fast_llm = self._initialize_fast_llm()
        self.full_llm = self._initialize_full_llm()
        self.embeddings = OpenAIEmbeddings(
            api_key=api_key,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        
    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize the main LLM model"""
        return ChatOpenAI(
            api_key=self.api_key, 
            model=self.model_name,
            temperature=settings.LLM_TEMPERATURE,
            streaming=False,
            request_timeout=settings.LLM_TIMEOUT,
            max_retries=settings.LLM_MAX_RETRIES,
            # OpenAI specific: seed for cached input
            model_kwargs={"seed": settings.OPENAI_CACHE_SEED} if settings.ENABLE_PROVIDER_CACHING else {}
        )

    def _initialize_fast_llm(self) -> ChatOpenAI:
        """Initialize a faster LLM for hybrid mode"""
        return ChatOpenAI(
            api_key=self.api_key, 
            model=self.fast_model,
            temperature=settings.LLM_TEMPERATURE,
            streaming=False,
            request_timeout=settings.LLM_TIMEOUT,
            max_retries=1,
            max_tokens=150,
            model_kwargs={"seed": settings.OPENAI_CACHE_SEED} if settings.ENABLE_PROVIDER_CACHING else {}
        )
    
    def _initialize_full_llm(self) -> ChatOpenAI:
        """Initialize the full LLM for full_llm mode"""
        return ChatOpenAI(
            api_key=self.api_key, 
            model=self.full_llm_model,
            temperature=0.8,
            streaming=False,
            request_timeout=settings.LLM_TIMEOUT,
            max_retries=settings.LLM_MAX_RETRIES,
            max_tokens=settings.MAX_TOKENS,
            model_kwargs={"seed": settings.OPENAI_CACHE_SEED} if settings.ENABLE_PROVIDER_CACHING else {}
        )
    
    async def generate_chat_response(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: str, 
        use_fast_model: bool = True,
        use_full_llm_mode: bool = False,
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """Generate a chat response with OpenAI cached input support"""
        
        # Check cache first
        if use_cache and settings.ENABLE_PROVIDER_CACHING:
            cache_key = self.get_cache_key(messages, system_prompt)
            if cache_key in self._cache:
                logger.debug("Using cached response from OpenAI")
                return self._cache[cache_key]
        
        # Convert to LangChain message format
        langchain_messages = []
        
        # Add system prompt
        langchain_messages.append(SystemMessage(content=system_prompt))
        
        # Handle conversation history
        if use_full_llm_mode:
            recent_messages = messages[-settings.MAX_CONVERSATION_HISTORY:] if len(messages) > settings.MAX_CONVERSATION_HISTORY else messages
        else:
            recent_messages = messages[-5:] if len(messages) > 5 else messages
        
        for message in recent_messages:
            if message["role"] == "user":
                langchain_messages.append(HumanMessage(content=message["content"]))
            elif message["role"] == "assistant":
                langchain_messages.append(AIMessage(content=message["content"]))
        
        try:
            # Select appropriate LLM
            if use_full_llm_mode:
                llm_to_use = self.full_llm
                logger.debug(f"Using OpenAI full LLM mode with model: {self.full_llm_model}")
            else:
                llm_to_use = self.fast_llm if use_fast_model else self.llm
                logger.debug(f"Using OpenAI hybrid mode with model: {self.fast_model if use_fast_model else self.model_name}")
            
            # Generate response
            timeout = settings.LLM_TIMEOUT if not use_full_llm_mode else settings.LLM_TIMEOUT + 5
            
            response = await asyncio.wait_for(
                llm_to_use.ainvoke(langchain_messages),
                timeout=timeout
            )
            
            response_text = response.content
            
            # Cache the response
            if use_cache and settings.ENABLE_PROVIDER_CACHING:
                self._cache[cache_key] = response_text
            
            logger.debug(f"Generated response length: {len(response_text)} characters")
            return response_text
            
        except asyncio.TimeoutError:
            logger.error("OpenAI request timed out")
            if use_full_llm_mode:
                raise Exception("I'm having trouble processing your request right now. Please try again.")
            else:
                return "Sorry, I'm thinking too hard! 😅 Let me try again - what were you asking about?"
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            if use_full_llm_mode:
                raise Exception(f"I encountered an error: {str(e)}")
            else:
                return "Oops, my brain froze for a second there! Could you repeat that?"
    
    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI"""
        try:
            embeddings = await self.embeddings.aembed_query(text)
            return embeddings
        except Exception as e:
            logger.error(f"Error generating OpenAI embeddings: {e}")
            return []
    
    def get_cache_key(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """Generate cache key for OpenAI cached input"""
        # Create a deterministic key based on the conversation
        key_data = {
            "system": system_prompt[:200],  # First 200 chars of system prompt
            "messages": [(m["role"], m["content"][:100]) for m in messages[-3:]],  # Last 3 messages
            "provider": "openai",
            "seed": settings.OPENAI_CACHE_SEED
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_provider_name(self) -> str:
        """Get the provider name"""
        return "OpenAI"