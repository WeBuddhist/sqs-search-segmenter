from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import threading

from app.config import get
from app.sqs_service import consumer
from app.api.enqueue import router as job_router
from app.segmentation import segmentation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

consumer_thread = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI.
    Runs startup and shutdown logic.
    """
    # Startup: Start SQS consumer in background thread
    logger.info("🚀 Starting SQS consumer in background thread...")
    global consumer_thread
    consumer_thread = threading.Thread(
        target=consumer.start,
        daemon=True,  # Thread will exit when main program exits
        name="SQSConsumerThread"
    )
    consumer_thread.start()
    logger.info("✅ SQS consumer thread started")
    
    yield  # Application runs here
    
    # Shutdown: Clean up (optional)
    logger.info("🛑 Shutting down SQS consumer...")
    # Note: daemon threads are automatically terminated on shutdown

app = FastAPI(
    title="SQS Search Segmenter",
    description="Background job processing service for OpenPecha segment analysis using AWS SQS",
    version="1.0.0",
    lifespan=lifespan  # Register the lifespan handler
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoints
@app.get("/")
def root():
    """Root endpoint with service information"""
    return {
        "service": "SQS Search Segmenter",
        "version": "1.0.0",
        "status": "running",
        "sqs_consumer": "active" if consumer_thread and consumer_thread.is_alive() else "inactive",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "sqs_consumer_running": consumer_thread.is_alive() if consumer_thread else False,
        "components": {
            "api": "up",
            "sqs_consumer": "up" if consumer_thread and consumer_thread.is_alive() else "down"
        }
    }

# Include routers
app.include_router(job_router)  # Job management API (/jobs)
app.include_router(segmentation)  # Segmentation API (/segmentation)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="localhost", port=8080, reload=True)