from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
import json
import boto3
from uuid import uuid4
from datetime import datetime, timezone

from app.config import get

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/jobs",
    tags=["Job Management"]
)

# Initialize SQS client
sqs_client = boto3.client(
    'sqs',
    region_name=get('AWS_REGION'),
    aws_access_key_id=get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=get('AWS_SECRET_ACCESS_KEY')
)


class CreateJobRequest(BaseModel):
    """Request model for creating a new segmentation job"""
    manifestation_id: str


class CreateJobResponse(BaseModel):
    """Response model for job creation"""
    job_id: str
    manifestation_id: str
    message: str


@router.post("/create", response_model=CreateJobResponse)
def create_segmentation_job(request: CreateJobRequest):
    """
    Create a new segmentation job and enqueue it to SQS (fire-and-forget).
    
    Steps:
    1. Generate job ID
    2. Send message to SQS queue with manifestation_id
    3. Return job_id to client for reference
    """
    try:
        # Generate job ID for tracking
        job_id = str(uuid4())
        
        logger.info(f"Creating job {job_id} for manifestation {request.manifestation_id}")
        
        # Send message to SQS
        queue_url = get("SQS_QUEUE_URL")
        if not queue_url:
            raise ValueError("SQS_QUEUE_URL not configured")
        
        message_body = {
            "job_id": job_id,
            "manifestation_id": request.manifestation_id,
            "task_type": "segment_processing",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Check if using FIFO queue
        is_fifo = queue_url.endswith('.fifo')
        
        sqs_params = {
            'QueueUrl': queue_url,
            'MessageBody': json.dumps(message_body)
        }
        
        # Add FIFO-specific parameters
        if is_fifo:
            sqs_params['MessageGroupId'] = 'segmentation'
            sqs_params['MessageDeduplicationId'] = job_id
        
        response = sqs_client.send_message(**sqs_params)
        
        logger.info(f"Successfully enqueued job {job_id} to SQS. MessageId: {response.get('MessageId')}")
        
        return CreateJobResponse(
            job_id=job_id,
            manifestation_id=request.manifestation_id,
            message=f"Job enqueued successfully. MessageId: {response.get('MessageId')}"
        )
        
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enqueue job: {str(e)}"
        )

