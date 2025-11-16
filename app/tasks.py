"""
Task processing module - Core logic for processing segmentation jobs.

This module contains the main task processing functions that:
1. Fetch data from Neo4j
2. Process segmentation logic
3. Store results in Postgres
4. Update job status
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from app.models import Segment
from sqlalchemy import update
from dotenv import load_dotenv

from app.db.postgres import SessionLocal
from app.db.models import ManifestationTask, RootJob
from app.neo4j_database import Neo4JDatabase
from app.storage import Storage
from app.segmentation import get_search_segmentation


load_dotenv(override=True)
logger = logging.getLogger(__name__)


def process_manifestation_task(job_id: str, manifestation_id: str) -> Dict[str, Any]:
    """
    Main task processing function for segmentation jobs.
    
    This function:
    1. Updates job status to IN_PROGRESS
    2. Fetches data from Neo4j (expression_id, annotation_id, segments)
    3. Retrieves base text from storage
    4. Processes segments with content
    5. Stores results in Postgres
    6. Updates job progress
    
    Args:
        job_id: UUID of the job
        manifestation_id: ID of the manifestation to process
        
    Returns:
        Dictionary with job results
        
    Raises:
        Exception: Any error during processing (will trigger SQS retry)
    """
    try:
        logger.info(f"Processing manifestation {manifestation_id} for job {job_id}")

        # Update job status to IN_PROGRESS
        _update_root_job_status(job_id=job_id, status="IN_PROGRESS")
        _update_manifestation_task_record(
            job_id=job_id,
            manifestation_id=manifestation_id,
            status="IN_PROGRESS"
        )
        logger.info(f"Job {job_id} status updated to IN_PROGRESS")

        # Initialize connections
        db = Neo4JDatabase()
        storage = Storage()

        # Fetch data from Neo4j
        logger.info(f"Fetching expression and annotation IDs from Neo4j")
        expression_id = db.get_expression_id_by_manifestation_id(
            manifestation_id=manifestation_id
        )
        logger.info(f"Manifestation id: {manifestation_id} has Expression id: {expression_id}")
        # Retrieve base text from storage
        logger.info(f"Retrieving base text from storage")
        base_text = storage.retrieve_base_text(
            expression_id=expression_id,
            manifestation_id=manifestation_id
        )
        logger.info(f"Retrieved base text with {len(base_text)} characters")
        

        segmentation_result = get_search_segmentation(base_text, language="tibetan")
        search_segments = db.create_search_segments(segmentation_result)
        logger.info(f"Created {len(search_segments)} search segments in Neo4j")
        
        logger.info(f"Fetching overlapping segments from Neo4j")
        overlapping_segments = db.get_overlapping_segments_by_manifestation_id_and_search_segments(
            manifestation_id=manifestation_id,
            search_segments=search_segments
        )
        logger.info(f"Fetched {len(overlapping_segments)} overlapping segments")

        # Process segments with content
        logger.info(f"Processing segments with content")
        segments_with_content = _get_segments_with_content(
            search_segments=search_segments,
            overlapping_segments=overlapping_segments,
            base_text=base_text
        )
        logger.info(f"Processed {len(segments_with_content)} segments with content")
        
        # Store results in database
        logger.info(f"Storing results in database")
        _store_all_segments_in_db(
            job_id=job_id,
            manifestation_id=manifestation_id,
            result_json=segments_with_content
        )
        logger.info(f"Results stored successfully")
    
        return {
            "job_id": job_id,
            "manifestation_id": manifestation_id,
            "segments_count": len(segments_with_content),
            "status": "COMPLETED"
        }
    
    except Exception as exc:
        logger.error(
            f"Error processing manifestation {manifestation_id} for job {job_id}: {str(exc)}",
            exc_info=True
        )
        
        # Update status to FAILED (will be retried by SQS)
        _update_manifestation_task_record(
            job_id=job_id,
            manifestation_id=manifestation_id,
            status="FAILED",
            error_message=str(exc)
        )
        
        # Re-raise to trigger SQS retry
        raise exc
    

def process_search_segments_task(job_id, manifestation_id: str):
    try:
        logger.info(f"Processing search segments for job {job_id}")
        logger.info(f"Updating root job status to IN_PROGRESS")
        _update_root_job_status(job_id=job_id)
        logger.info(f"Updating root job record in database to IN_PROGRESS")
        _update_manifestation_task_record(job_id=job_id, manifestation_id=manifestation_id, status="IN_PROGRESS")
    except Exception as exc:
        logger.error(f"Error processing search segments for job {job_id}")
        logger.error(f"Error message: {str(exc)}")
        raise exc


def _update_manifestation_task_record(job_id, manifestation_id, status, error_message=None):
    with SessionLocal() as session:
        manifestation_task = session.query(ManifestationTask).filter(ManifestationTask.job_id == job_id, ManifestationTask.manifestation_id == manifestation_id).update({
            "status": status,
            "error_message": error_message,
            "updated_at": datetime.now(timezone.utc)
        })
        session.commit()
        _update_root_job_status(job_id=job_id, status=status)


def _update_manifestation_task_record(job_id, manifestation_id, status, error_message=None):
    with SessionLocal() as session:
        manifestation_task = session.query(ManifestationTask).filter(ManifestationTask.job_id == job_id, ManifestationTask.manifestation_id == manifestation_id).update({
            "status": status,
            "error_message": error_message,
            "updated_at": datetime.now(timezone.utc)
        })
        session.commit()
        _update_root_job_status(job_id=job_id, status=status)


def _update_root_job_status(job_id: str, status: str):
    """Update the status of a root job"""
    with SessionLocal() as session:
        session.execute(
            update(RootJob)
            .where(RootJob.job_id == job_id)
            .values(status=status, updated_at=datetime.now(timezone.utc))
        )
        session.commit()
        logger.info(f"Updated root job {job_id} status to {status}")
    

def _store_all_segments_in_db(job_id, manifestation_id, result_json):
    with SessionLocal() as session:
        manifestation_task = session.query(ManifestationTask).filter(ManifestationTask.job_id == job_id, ManifestationTask.manifestation_id == manifestation_id)
        if manifestation_task is not None:
            manifestation_task.result_json = result_json
            manifestation_task.status = "COMPLETED"
            manifestation_task.updated_at = datetime.now(timezone.utc)
            logger.info(f"Updated manifestation task record in ManifestationTask table with manifestation id = {manifestation_id}")
            session.commit()
            _update_root_job_status(job_id=job_id, status="COMPLETED")


def _get_segments_with_content(
    search_segments: List[Dict[str, Any]],
    overlapping_segments: List[Dict[str, Any]],
    base_text: str
) -> List[Dict[str, Any]]:
    """
    Extract content for search segments and their overlapping segments.
    
    Args:
        search_segments: List of search segment dictionaries with span info
        overlapping_segments: List of overlapping segment dictionaries
        base_text: Base text to extract content from
        
    Returns:
        List of dictionaries with segment IDs and content
    """
    logger.info(f"Getting segments with content for {len(search_segments)} search segments")
    segments_with_content = []
    
    try:
        for search_segment in search_segments:
            span_start = search_segment.get('span_start', 0)
            span_end = search_segment.get('span_end', 0)
            
            # Skip if span is out of bounds
            if span_end > len(base_text) or span_start >= len(base_text):
                logger.warning(
                    f"Search segment {search_segment.get('search_segment_id')} "
                    f"span ({span_start}:{span_end}) exceeds base text length ({len(base_text)})"
                )
                continue
            
            # Extract search segment content
            search_segment_content = base_text[span_start:span_end]
            
            # Extract overlapping segments for this search segment
            overlapping_content = []
            for overlapping_segment in overlapping_segments:
                overlap_start = overlapping_segment.get('span_start', 0)
                overlap_end = overlapping_segment.get('span_end', 0)
                
                # Skip if span is out of bounds
                if overlap_end > len(base_text) or overlap_start >= len(base_text):
                    continue
                
                overlapping_content.append({
                    "segment_id": overlapping_segment.get('segment_id'),
                    "segment_content": base_text[overlap_start:overlap_end],
                    "span_start": overlap_start,
                    "span_end": overlap_end
                })
            
            data = {
                "search_segment_id": search_segment.get('search_segment_id'),
                "search_segment_content": search_segment_content,
                "span_start": span_start,
                "span_end": span_end,
                "segments": overlapping_content
            }
            segments_with_content.append(data)
        
        logger.info(f"Successfully processed {len(segments_with_content)} segments with content")
        return segments_with_content
        
    except Exception as exc:
        logger.error(f"Error getting segments with content: {str(exc)}", exc_info=True)
        raise exc