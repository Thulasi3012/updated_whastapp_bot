from sqlalchemy import create_engine, pool, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import time
import logging

logger = logging.getLogger(__name__)

# Create database engine with optimized settings for chat workload
engine = create_engine(
    settings.DATABASE_URL,
    # Use NullPool for better performance in async environments
    poolclass=pool.QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Test connections before using
    
    # Connection arguments optimized for read-heavy workload
    connect_args={
        "connect_timeout": settings.DB_CONNECT_TIMEOUT,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "options": "-c statement_timeout=10000"  # 10 second statement timeout
    },
    
    # Execution options
    execution_options={
        "isolation_level": "READ COMMITTED",  # Better for read-heavy workloads
    }
)

# Add connection pool logging if debug mode
if settings.DEBUG:
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_connection, connection_record):
        logger.info(f"Pool connection established: {id(dbapi_connection)}")
    
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        logger.debug(f"Connection checked out from pool: {id(dbapi_connection)}")

# Create session factory with optimized settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,  # Don't auto-flush for better performance
    bind=engine,
    expire_on_commit=False  # Don't expire objects after commit
)

# Base class for models
Base = declarative_base()

# Optimized dependency to get DB session
def get_db():
    """Get database session with automatic cleanup"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# Helper function for read-only operations (can use different transaction isolation)
def get_db_readonly():
    """Get database session optimized for read-only operations"""
    db = SessionLocal()
    try:
        # Set session to read-only mode for better performance
        db.execute("SET TRANSACTION READ ONLY")
        yield db
    finally:
        db.close()

# Create tables function
def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)

# Database health check
def check_database_health():
    """Check if database is accessible"""
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
def get_background_session():
    """
    Get a fresh database session for background tasks.
    This returns a new session that should be manually closed after use.
    """
    return SessionLocal()