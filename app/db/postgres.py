from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get
import logging

logger = logging.getLogger(__name__)

# Get database URL from config
POSTGRES_URL = get("POSTGRES_URL")

if not POSTGRES_URL:
    raise ValueError("POSTGRES_URL environment variable is required")

# Create engine with connection pooling
engine = create_engine(
    POSTGRES_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Additional connections if pool is exhausted
    echo=False,  # Set to True for SQL query logging during development
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    try:
        # Import all models to ensure they're registered with Base
        from app.db.models import RootJob, ManifestationTask, Base
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def get_db():
    """
    Dependency for FastAPI routes to get database session.
    Usage:
        @app.get("/")
        def route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
