from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging
import json
import boto3
from uuid import uuid4
from datetime import datetime, timezone

from app.db.postgres import get_db, SessionLocal
from app.db.models import RootJob, ManifestationTask
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
    total_segments: Optional[int] = None  # Will be calculated if not provided


class CreateJobResponse(BaseModel):
    """Response model for job creation"""
    job_id: str
    manifestation_id: str
    total_segments: int
    status: str
    message: str


@router.post("/create", response_model=CreateJobResponse)
def create_segmentation_job(
    request: CreateJobRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new segmentation job and enqueue it to SQS.
    
    Steps:
    1. Calculate total_segments if not provided (query Neo4j)
    2. Create RootJob entry in Postgres with status='QUEUED'
    3. Create ManifestationTask entry in Postgres
    4. Send message to SQS queue
    5. Return job_id to client
    """
    try:
        # Generate job ID
        job_id = uuid4()
        
        # Get total segments if not provided
        total_segments = request.total_segments
        if total_segments is None:
            # Query Neo4j to get segment count
            from app.neo4j_database import Neo4JDatabase
            neo4j_db = Neo4JDatabase()
            
            try:
                expression_id, annotation_id = neo4j_db.get_expression_id_and_search_segmentation_id_by_manifestation_id(
                    manifestation_id=request.manifestation_id
                )
                segments = neo4j_db.get_segments_by_annotation_id(annotation_id=annotation_id)
                total_segments = len(segments) if segments else 1
                logger.info(f"Calculated total_segments={total_segments} for manifestation {request.manifestation_id}")
            except Exception as e:
                logger.warning(f"Could not calculate segments from Neo4j: {e}. Using default value 1")
                total_segments = 1
        
        # Create RootJob entry
        root_job = RootJob(
            job_id=job_id,
            manifestation_id=request.manifestation_id,
            total_segments=total_segments,
            completed_segments=0,
            status="QUEUED",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(root_job)
        
        # Create ManifestationTask entry
        manifestation_task = ManifestationTask(
            task_id=uuid4(),
            job_id=job_id,
            manifestation_id=request.manifestation_id,
            status="QUEUED",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(manifestation_task)
        
        # Commit to database
        db.commit()
        logger.info(f"Created job {job_id} for manifestation {request.manifestation_id}")
        
        # Send message to SQS
        queue_url = get("SQS_QUEUE_URL")
        if not queue_url:
            raise ValueError("SQS_QUEUE_URL not configured")
        
        message_body = {
            "job_id": str(job_id),
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
            sqs_params['MessageDeduplicationId'] = str(job_id)
        
        response = sqs_client.send_message(**sqs_params)
        
        logger.info(f"Enqueued job {job_id} to SQS. MessageId: {response.get('MessageId')}")
        
        return CreateJobResponse(
            job_id=str(job_id),
            manifestation_id=request.manifestation_id,
            total_segments=total_segments,
            status="QUEUED",
            message=f"Job created and enqueued successfully. MessageId: {response.get('MessageId')}"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create job: {str(e)}"
        )


@router.get("/{job_id}/status")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Get the status of a job by job_id.
    
    Returns job details including:
    - Overall job status
    - Progress (completed_segments / total_segments)
    - All manifestation tasks
    """
    try:
        # Query root job
        root_job = db.query(RootJob).filter(RootJob.job_id == job_id).first()
        
        if not root_job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Query related tasks
        tasks = db.query(ManifestationTask).filter(
            ManifestationTask.job_id == job_id
        ).all()
        
        return {
            "job_id": str(root_job.job_id),
            "manifestation_id": root_job.manifestation_id,
            "status": root_job.status,
            "total_segments": root_job.total_segments,
            "completed_segments": root_job.completed_segments,
            "progress_percentage": (root_job.completed_segments / root_job.total_segments * 100) if root_job.total_segments > 0 else 0,
            "created_at": root_job.created_at.isoformat() if root_job.created_at else None,
            "updated_at": root_job.updated_at.isoformat() if root_job.updated_at else None,
            "tasks": [
                {
                    "task_id": str(task.task_id),
                    "manifestation_id": task.manifestation_id,
                    "status": task.status,
                    "error_message": task.error_message,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                }
                for task in tasks
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/{job_id}/results")
def get_job_results(job_id: str, db: Session = Depends(get_db)):
    """
    Get the results of a completed job.
    
    Returns the result_json from all completed tasks.
    """
    try:
        # Query root job
        root_job = db.query(RootJob).filter(RootJob.job_id == job_id).first()
        
        if not root_job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if root_job.status != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed yet. Current status: {root_job.status}"
            )
        
        # Query completed tasks
        tasks = db.query(ManifestationTask).filter(
            ManifestationTask.job_id == job_id,
            ManifestationTask.status == "COMPLETED"
        ).all()
        
        return {
            "job_id": str(root_job.job_id),
            "manifestation_id": root_job.manifestation_id,
            "status": root_job.status,
            "results": [
                {
                    "task_id": str(task.task_id),
                    "manifestation_id": task.manifestation_id,
                    "result_json": task.result_json,
                    "result_location": task.result_location,
                }
                for task in tasks
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job results: {str(e)}"
        )

