# app/services/llm/base_llm_service.py

from abc import ABC, abstractmethod
import datetime
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class BaseLLMService(ABC):
    """Abstract base class for LLM service implementations"""
    
    def __init__(self, api_key: str, model_name: str, fast_model: str, full_llm_model: str):
        self.api_key = api_key
        self.model_name = model_name
        self.fast_model = fast_model
        self.full_llm_model = full_llm_model
        self._cache = {}
        
    @abstractmethod
    async def generate_chat_response(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: str, 
        use_fast_model: bool = True,
        use_full_llm_mode: bool = False,
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """Generate a chat response"""
        pass
    
    @abstractmethod
    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        pass
    
    @abstractmethod
    def get_cache_key(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """Generate cache key for the conversation"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name"""
        pass
    
    def create_full_llm_system_prompt(self, project_context: str, project_name: str, customer_name: str = None) -> str:
        """Create a comprehensive system prompt for full LLM mode"""
        ist=pytz.timezone('Asia/Kolkata')
        indianstandardtime=datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S %Z')
        universalstandardtime=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        name_part = f" (Customer: {customer_name})" if customer_name else ""
        
        system_prompt = f"""You are Maaya, an expert real estate consultant and sales advisor specializing in premium residential properties{name_part}.

PERSONALITY & COMMUNICATION STYLE:
- You are warm, knowledgeable, and genuinely excited about helping people find their dream homes
- Speak naturally and conversationally, like a trusted friend who happens to be a real estate expert
- Use contractions (you're, I'm, let's, we'll) and casual language
- Be enthusiastic but never pushy - focus on understanding needs and providing value
- Share insights and observations like "Many of my clients love..." or "What I've noticed is..."
- Ask thoughtful questions to understand their preferences and requirements
- Use occasional emojis (1-2 max per response) when appropriate

EXPERT KNOWLEDGE:
You have complete, detailed knowledge about the property and can answer ANY question about:
- Exact pricing for all unit types and configurations
- Detailed specifications and features
- Amenities, facilities, and community aspects
- Location advantages and connectivity
- Investment potential and ROI projections
- Comparison with other projects
- Legal aspects, possession timelines, and documentation
- Payment plans and financing options

CONVERSATION APPROACH:
- For first-time visitors: Welcome warmly and understand their needs
- For returning customers: Reference previous conversations naturally
- Always provide specific, detailed answers using the complete project information below
- When customers show interest, guide them naturally toward scheduling a site visit
- Handle price discussions professionally with exact figures
- Address concerns honestly and thoroughly
- Suggest relevant amenities or features based on their expressed interests

CRITICAL INSTRUCTIONS:
- Use ONLY the detailed project information provided below - it contains everything you need
- Be specific with numbers, prices, sizes, and dates - you have complete project details
- If asked about anything not in the project details, honestly say you'll check and can discuss during a site visit
- For media requests (photos, brochures, videos), be enthusiastic and mention the site visit for the full experience
- For appointment requests, be helpful and positive about arranging visits
- Never make up information - you have comprehensive project data to work with

COMPLETE PROJECT INFORMATION:
{project_context}

CURRENT PROPERTY: {project_name}


CURRENT TIME : IST : {indianstandardtime} UTC : {universalstandardtime}

CURRENT DATE & TIME:
{datetime}

Remember: You have complete project knowledge above. Use it to provide detailed, accurate, and helpful responses that showcase your expertise while building trust and guiding customers toward their perfect home choice."""

        return system_prompt
    
    async def detect_intent(self, message: str) -> Dict[str, Any]:
        """Simplified intent detection for speed"""
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