# app/core/startup.py - Minimal startup without embeddings

import logging
from app.config import settings
from app.database.database import check_database_health
from app.services.azure_storage_service import AzureStorageService

logger = logging.getLogger(__name__)

class ApplicationStartup:
    """Handle application startup tasks"""
    
    @staticmethod
    async def initialize():
        """Initialize application"""
        
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        
        # 1. Check database connectivity
        if not check_database_health():
            logger.error("Database connection failed")
            # Continue anyway - some endpoints might still work
        else:
            logger.info("✓ Database connection established")
        
        # 2. Test Azure Storage connection
        try:
            storage_service = AzureStorageService()
            # Just create the client, don't test with actual file operations
            logger.info("✓ Azure Storage client initialized")
        except Exception as e:
            logger.warning(f"Azure Storage initialization warning: {e}")
            # Don't fail startup
        
        # 3. Log configuration summary
        logger.info("Configuration Summary:")
        logger.info(f"  - OpenAI Model: {settings.OPENAI_MODEL}")
        logger.info(f"  - Quick Responses: Enabled")
        logger.info(f"  - Project Cache TTL: {settings.PROJECT_CACHE_TTL_MINUTES} minutes")
        
        logger.info("✓ Application initialized")
    
    @staticmethod
    def configure_logging():
        """Configure logging"""
        
        # Set log level
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Reduce noise from libraries
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("azure").setLevel(logging.WARNING)
        
        if not settings.DEBUG:
            logging.getLogger("sqlalchemy").setLevel(logging.WARNING)