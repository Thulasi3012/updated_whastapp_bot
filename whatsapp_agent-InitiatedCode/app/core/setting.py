# app/core/settings.py

from app.config import settings

# Re-export settings for easy access
OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_MODEL = settings.OPENAI_MODEL

# Add this line to fix the immediate error - even if we don't use embeddings
OPENAI_EMBEDDING_MODEL = settings.OPENAI_EMBEDDING_MODEL if hasattr(settings, 'OPENAI_EMBEDDING_MODEL') else "text-embedding-3-small"

# Database settings
DATABASE_URL = settings.DATABASE_URL

# Use Pinecone for vectors 
USE_PINECONE_VECTORS = settings.USE_PINECONE_VECTORS