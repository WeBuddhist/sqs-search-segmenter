from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.enqueue import router as job_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SQS Search Segmenter API",
    description="API service for enqueuing OpenPecha segmentation jobs to AWS SQS",
    version="1.0.0"
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
        "service": "SQS Search Segmenter API",
        "version": "1.0.0",
        "status": "running",
        "description": "API for enqueuing segmentation jobs. Workers process jobs separately.",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "api",
        "note": "Workers run separately - check worker logs for processing status"
    }

# Include routers
app.include_router(job_router)  # Job management API (/jobs)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="localhost", port=8080, reload=True)