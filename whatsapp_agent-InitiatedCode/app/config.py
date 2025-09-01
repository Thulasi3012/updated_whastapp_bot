# app/config.py - Enhanced with Multi-Model LLM Support

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from urllib.parse import quote_plus
from typing import Literal

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "AdVinciMate-API"
    APP_VERSION: str = "3.0.0"  # Updated version for multi-model support
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Chat Mode Configuration
    CHAT_MODE: str = os.getenv("CHAT_MODE", "hybrid")  # "hybrid" or "full_llm"
    
    # LLM Provider Configuration - NEW
    LLM_PROVIDER: Literal["openai", "claude", "gemini"] = os.getenv("LLM_PROVIDER", "openai")
    
    # Database settings - Optimized for read performance
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "advincidb")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    
    # Connection pool settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_TIMEOUT: int = 10
    DB_CONNECT_TIMEOUT: int = 5
    DB_POOL_RECYCLE: int = 300
    
    @property
    def DATABASE_URL(self) -> str:
        encoded_password = quote_plus(self.DB_PASSWORD)
        url = f"postgresql+psycopg2://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        url += f"?connect_timeout={self.DB_CONNECT_TIMEOUT}"
        url += f"&application_name=advinci_chat"
        return url
    
    # OpenAI settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5")
    OPENAI_FAST_MODEL: str = "gpt-5"
    OPENAI_FULL_LLM_MODEL: str = os.getenv("OPENAI_FULL_LLM_MODEL", "gpt-4o")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Claude settings - NEW
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-20241022")
    CLAUDE_FAST_MODEL: str = "claude-3-5-haiku-20241022"
    CLAUDE_FULL_LLM_MODEL: str = os.getenv("CLAUDE_FULL_LLM_MODEL", "claude-3-5-sonnet-20241022")
    CLAUDE_MAX_TOKENS: int = 4096
    
    # Gemini settings - NEW
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    GEMINI_FAST_MODEL: str = "gemini-2.0-flash-exp"
    GEMINI_FULL_LLM_MODEL: str = os.getenv("GEMINI_FULL_LLM_MODEL", "gemini-1.5-pro")
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192
    
    # Provider-agnostic settings
    LLM_TEMPERATURE: float = 0.7
    LLM_TIMEOUT: int = 15 if os.getenv("CHAT_MODE") == "full_llm" else 10
    LLM_MAX_RETRIES: int = 2
    
    # Cache settings for different providers
    ENABLE_PROVIDER_CACHING: bool = os.getenv("ENABLE_PROVIDER_CACHING", "True").lower() == "true"
    CLAUDE_CACHE_TTL_MINUTES: int = 120  # Claude prompt caching duration
    GEMINI_CACHE_TTL_MINUTES: int = 60   # Gemini context caching duration
    OPENAI_CACHE_SEED: int = 12345       # OpenAI cached input seed
    
    # Token limits based on provider and mode
    @property
    def MAX_TOKENS(self) -> int:
        if self.LLM_PROVIDER == "claude":
            return 1000 if self.CHAT_MODE == "full_llm" else 300
        elif self.LLM_PROVIDER == "gemini":
            return 2048 if self.CHAT_MODE == "full_llm" else 500
        else:  # openai
            return 500 if self.CHAT_MODE == "full_llm" else 150
    
    # Context settings for Full LLM mode
    FULL_LLM_MAX_CONTEXT_TOKENS: int = 8000
    FULL_LLM_CONTEXT_TIMEOUT: int = 10
    
    # Disable vector/embedding features
    USE_PINECONE_VECTORS: bool = False
    USE_EMBEDDINGS: bool = False
    
    # Azure Storage settings
    AZURE_STORAGE_ACCOUNT_NAME: str = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_DATA_CONTAINER: str = os.getenv("AZURE_DATA_CONTAINER", "data-dev")
    
    # Storage optimization
    AZURE_STORAGE_TIMEOUT: int = 3
    AZURE_STORAGE_MAX_RETRIES: int = 1
    
    # Project information caching
    PROJECT_CACHE_TTL_MINUTES: int = 10
    PROJECT_CONTEXT_TIMEOUT: float = 3.0
    
    # Chat performance settings - Provider dependent
    @property
    def MAX_CONVERSATION_HISTORY(self) -> int:
        if self.CHAT_MODE == "full_llm":
            return 10
        return 5
    
    QUICK_RESPONSE_ENABLED: bool = True
    RESPONSE_CACHE_TTL_SECONDS: int = 300
    
    # Conversation settings
    DEFAULT_AGENT_NAME: str = "Maaya"
    USE_THINKING_PHRASES: bool = True
    USE_EXCITEMENT_PHRASES: bool = True
    EMOJI_PROBABILITY: float = 0.3
    FOLLOW_UP_PROBABILITY: float = 0.2
    
    # Email settings (optional)
    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USERNAME: str = os.getenv("EMAIL_USERNAME", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")
    EMAIL_TO: str = os.getenv("EMAIL_TO", "")
    
    # API Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Monitoring
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_SLOW_QUERIES: bool = True
    SLOW_QUERY_THRESHOLD_MS: int = 1000
    
    # Project folder mapping
    PROJECT_FOLDER_MAP: dict = {
        "1": "Aavaas",
        "2": "Elevender",
        "3": "CasagrandTudor",
        "4": "NorthCounty",
        "5": "PalacioCourt"
    }
    
    # Storage folder prefix
    STORAGE_FOLDER_PREFIX: str = "Company/"
    
    # Validation
    def __post_init__(self):
        if self.CHAT_MODE not in ["hybrid", "full_llm"]:
            raise ValueError(f"Invalid CHAT_MODE: {self.CHAT_MODE}. Must be 'hybrid' or 'full_llm'")
        if self.LLM_PROVIDER not in ["openai", "claude", "gemini"]:
            raise ValueError(f"Invalid LLM_PROVIDER: {self.LLM_PROVIDER}. Must be 'openai', 'claude', or 'gemini'")

# Create settings instance
settings = Settings()