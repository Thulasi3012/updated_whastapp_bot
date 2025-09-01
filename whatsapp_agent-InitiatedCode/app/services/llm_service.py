# app/services/llm_service.py - Complete implementation with factory pattern

import datetime
import os
from typing import List, Dict, Any, Optional
import logging
import asyncio
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from app.config import settings
from app.services.llm.llm_service_factory import LLMServiceFactory
from app.services.llm.base_llm_service import BaseLLMService

logger = logging.getLogger(__name__)

class LLMService:
    """
    Main LLM Service that either delegates to provider-specific implementations
    or falls back to original implementation for backward compatibility
    """
    
    def __init__(self):
        try:
            # Try to use the new multi-provider system
            self._service: Optional[BaseLLMService] = LLMServiceFactory.get_llm_service()
            self._use_factory = True
            logger.info(f"LLMService initialized with {self._service.get_provider_name()} provider")
        except Exception as e:
            logger.warning(f"Failed to initialize provider-specific service: {e}")
            logger.info("Falling back to original OpenAI implementation")
            self._use_factory = False
            self._initialize_fallback()
    
    def _initialize_fallback(self):
        """Initialize fallback OpenAI implementation for backward compatibility"""
        api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        
        if not api_key or api_key.startswith("your-") or "***" in api_key:
            raise ValueError("Invalid OpenAI API key.")
            
        self.api_key = api_key
        self.model_name = settings.OPENAI_MODEL
        self.fast_model = settings.OPENAI_FAST_MODEL
        self.full_llm_model = settings.OPENAI_FULL_LLM_MODEL
        
        self.llm = self._initialize_llm()
        self.fast_llm = self._initialize_fast_llm()
        self.full_llm = self._initialize_full_llm()

    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize the main LLM model"""
        return ChatOpenAI(
            api_key=self.api_key, 
            model=self.model_name,
            temperature=settings.LLM_TEMPERATURE,
            streaming=False,
            request_timeout=settings.LLM_TIMEOUT,
            max_retries=settings.LLM_MAX_RETRIES
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
            max_tokens=150
        )
    
    def _initialize_full_llm(self) -> ChatOpenAI:
        """Initialize the full LLM for full_llm mode with better model and settings"""
        return ChatOpenAI(
            api_key=self.api_key, 
            model=self.full_llm_model,
            temperature=0.8,
            streaming=False,
            request_timeout=settings.LLM_TIMEOUT,
            max_retries=settings.LLM_MAX_RETRIES,
            max_tokens=settings.MAX_TOKENS
        )

    async def generate_chat_response(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: str, 
        rag_context: Optional[str] = None,
        use_fast_model: bool = True,
        use_full_llm_mode: bool = False
    ) -> str:
        """
        Generate a chat response - delegates to provider or uses fallback
        
        Args:
            messages: Conversation messages
            system_prompt: System prompt for the LLM
            rag_context: RAG context (ignored in full_llm mode)
            use_fast_model: Whether to use fast model
            use_full_llm_mode: Whether to use full LLM mode
        """
        if self._use_factory:
            return await self._service.generate_chat_response(
                messages=messages,
                system_prompt=system_prompt,
                use_fast_model=use_fast_model,
                use_full_llm_mode=use_full_llm_mode,
                use_cache=True
            )
        else:
            # Use original implementation
            return await self._generate_chat_response_fallback(
                messages, system_prompt, rag_context, use_fast_model, use_full_llm_mode
            )

    async def _generate_chat_response_fallback(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: str, 
        rag_context: Optional[str] = None,
        use_fast_model: bool = True,
        use_full_llm_mode: bool = False
    ) -> str:
        """Original OpenAI implementation for backward compatibility"""
        
        # Convert to LangChain message format
        langchain_messages = []
        
        # Add system prompt
        langchain_messages.append(SystemMessage(content=system_prompt))
        
        # Handle conversation history based on mode
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
            # Select appropriate LLM based on mode
            if use_full_llm_mode:
                llm_to_use = self.full_llm
                logger.debug(f"Using full LLM mode with model: {self.full_llm_model}")
            else:
                llm_to_use = self.fast_llm if use_fast_model else self.llm
                logger.debug(f"Using hybrid mode with model: {self.fast_model if use_fast_model else self.model_name}")
            
            # Generate response with appropriate timeout
            timeout = settings.LLM_TIMEOUT if not use_full_llm_mode else settings.LLM_TIMEOUT + 5
            
            response = await asyncio.wait_for(
                llm_to_use.ainvoke(langchain_messages),
                timeout=timeout
            )
            
            logger.debug(f"Generated response length: {len(response.content)} characters")
            return response.content
            
        except asyncio.TimeoutError:
            logger.error("LLM request timed out")
            if use_full_llm_mode:
                raise Exception("I'm having trouble processing your request right now. Please try again.")
            else:
                return "Sorry, I'm thinking too hard! 😅 Let me try again - what were you asking about?"
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            if use_full_llm_mode:
                raise Exception(f"I encountered an error: {str(e)}")
            else:
                return "Oops, my brain froze for a second there! Could you repeat that?"

    def create_full_llm_system_prompt(self, project_context: str, project_name: str, customer_name: str = None) -> str:
        """Create a comprehensive system prompt for full LLM mode"""
        if self._use_factory:
            return self._service.create_full_llm_system_prompt(project_context, project_name, customer_name)
        else:
            # Use original implementation
            return self._create_full_llm_system_prompt_fallback(project_context, project_name, customer_name)

    def _create_full_llm_system_prompt_fallback(self, project_context: str, project_name: str, customer_name: str = None) -> str:
        """Original system prompt creation for backward compatibility"""
        
        name_part = f" (Customer: {customer_name})" if customer_name else ""
        
        system_prompt = f"""You are Maaya, a friendly real estate consultant helping people find their dream homes{name_part}.

BE HUMAN & NATURAL:
- Keep responses SHORT and conversational (2-3 sentences max usually)
- Talk like you're chatting with a friend, not giving a presentation
- Use simple, everyday language - no corporate jargon
- React naturally: "Oh, that's interesting!" or "Hmm, good question!"
- One emoji per message max, only when it feels natural 😊

HANDLING ANY TOPIC:
- You're a real person with general knowledge - answer ANY question naturally
- If someone asks about weather, sports, movies, food, or anything else - answer briefly using your knowledge, then smoothly connect it back to their home search
- Examples:
  * "Yeah, it's been pretty hot lately! Speaking of weather, our apartments have great cross-ventilation..."
  * "Oh, you follow cricket? Nice! There's actually a sports complex nearby..."
  * "Haha, I haven't seen that movie yet! But hey, we have a mini theater in the clubhouse..."

YOUR PERSONALITY:
- Genuinely helpful and warm, not salesy
- Share personal touches: "I personally love..." or "Other clients tell me..."
- Ask natural follow-ups based on what they say
- If you don't know something specific, be honest: "Let me check that for you"

PROJECT KNOWLEDGE:
You know everything about {project_name}:
- Exact prices, sizes, availability
- All amenities and features
- Location benefits
- Payment plans

CONVERSATION STYLE:
- First-time visitors: Warm welcome, understand their needs
- Focus on what THEY care about
- When discussing prices/features, be specific but brief
- Natural transitions to booking visits: "Want to see it in person?"

GOLDEN RULE: You're a helpful friend who happens to sell real estate. Be real, be brief, be helpful.

PROJECT DETAILS:
{project_context}

CURRENT DATE & TIME:
{datetime}

Remember: Short, natural responses. Answer anything they ask, then gently guide back to helping them find their perfect home."""

        return system_prompt

    async def detect_intent(self, message: str) -> Dict[str, Any]:
        """Detect intent from message"""
        if self._use_factory:
            return await self._service.detect_intent(message)
        else:
            # Use simplified intent detection
            return await self._detect_intent_fallback(message)

    async def _detect_intent_fallback(self, message: str) -> Dict[str, Any]:
        """Simplified intent detection for backward compatibility"""
        message_lower = message.lower()
        
        # Quick intent detection
        if any(word in message_lower for word in ["price", "cost", "how much", "rate", "payment", "expensive", "afford"]):
            return {"intent": "price_inquiry", "entities": [], "sentiment": 0, "is_off_topic": False}
        elif any(word in message_lower for word in ["appointment", "visit", "schedule", "book", "tour", "see", "viewing"]):
            return {"intent": "appointment_request", "entities": [], "sentiment": 0, "is_off_topic": False}
        elif any(word in message_lower for word in ["photo", "picture", "image", "brochure", "video", "floor", "plan"]):
            return {"intent": "media_request", "entities": [], "sentiment": 0, "is_off_topic": False}
        elif any(word in message_lower for word in ["location", "where", "address", "near", "close", "distance"]):
            return {"intent": "location_inquiry", "entities": [], "sentiment": 0, "is_off_topic": False}
        elif any(word in message_lower for word in ["amenity", "amenities", "facility", "facilities", "gym", "pool", "parking"]):
            return {"intent": "amenity_inquiry", "entities": [], "sentiment": 0, "is_off_topic": False}
        elif any(word in message_lower for word in ["available", "availability", "units", "flat", "apartment", "bhk"]):
            return {"intent": "availability_inquiry", "entities": [], "sentiment": 0, "is_off_topic": False}
        elif any(word in message_lower for word in ["possession", "ready", "completion", "handover", "move"]):
            return {"intent": "possession_inquiry", "entities": [], "sentiment": 0, "is_off_topic": False}
        else:
            return {"intent": "general_inquiry", "entities": [], "sentiment": 0, "is_off_topic": False}

    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        if self._use_factory:
            return await self._service.generate_embeddings(text)
        else:
            # Use OpenAI embeddings as fallback
            try:
                from langchain_openai import OpenAIEmbeddings
                embeddings = OpenAIEmbeddings(
                    api_key=self.api_key,
                    model=settings.OPENAI_EMBEDDING_MODEL
                )
                return await embeddings.aembed_query(text)
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
                return []

    def get_provider_name(self) -> str:
        """Get the current provider name"""
        if self._use_factory:
            return self._service.get_provider_name()
        else:
            return "OpenAI (Fallback)"