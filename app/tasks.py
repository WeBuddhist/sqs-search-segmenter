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
from app.db.models import RootJob
from app.neo4j_database import Neo4JDatabase
from app.storage import Storage
from app.segmentation import get_search_segmentation, generate_segments_and_upload_to_vector_db


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
        # Update job status to IN_PROGRESS
        _update_root_job_status(job_id=job_id, status="IN_PROGRESS")
        logger.info(f"Job {job_id} status updated to IN_PROGRESS")

        # Initialize connections
        db = Neo4JDatabase()
        storage = Storage()

        # Fetch data from Neo4j
        expression_id, title, language = db.get_expression_id_by_manifestation_id(
            manifestation_id=manifestation_id
        )
        title = title[0]['text'] if title else ""
        logger.info(f"Manifestation id: {manifestation_id} has Expression id: {expression_id}")
        # Retrieve base text from storage
        logger.info(f"Language: {language}, Title: {title}")
        # base_text = storage.retrieve_base_text(
        #     expression_id=expression_id,
        #     manifestation_id=manifestation_id
        # )
        logger.info(f"Retrieved base text with {len(base_text)} characters")
        

        segmentation_result = get_search_segmentation(base_text, language)
        logger.info(f"Segmentation result: {segmentation_result}")
        check_if_search_segments_exist = db.check_if_search_segments_exist(manifestation_id)
        if check_if_search_segments_exist:
            search_segments = db.get_search_segments(manifestation_id)
            logger.info(f"Fetched {len(search_segments)} search segments from Neo4j")
        else:
            logger.info(f"Search segments do not exist for manifestation {manifestation_id}, creating new search segments")
            search_segments = db.create_search_segments(segmentation_result, manifestation_id)
            logger.info(f"Created {len(search_segments)} search segments in Neo4j")
            
        overlapping_mappings = Neo4JDatabase.get_overlapping_segments_by_search_segments_id(search_segments)
        logger.info(f"Fetched {len(overlapping_mappings)} overlapping segments")

        # Process segments with content
        logger.info(f"Processing segments with content")
        segments_with_content = _get_segments_with_content(
            segments=overlapping_mappings,
            base_text=base_text
        )
        logger.info(f"Processed {len(segments_with_content)} segments with content")
        
        generate_segments_and_upload_to_vector_db(
            segments_content=segments_with_content,
            title=title,
            language="tibetan"
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
        _update_root_job_status(
            job_id=job_id,
            status="FAILED"
        )
        
        # Re-raise to trigger SQS retry
        raise exc
    

def process_search_segments_task(job_id, manifestation_id: str):
    try:
        logger.info(f"Processing search segments for job {job_id}")
        _update_root_job_status(job_id=job_id, status="IN_PROGRESS")
    except Exception as exc:
        logger.error(f"Error processing search segments for job {job_id}: {str(exc)}", exc_info=True)
        raise exc


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


def _get_segments_with_content(
    segments: List[Dict[str, Any]],
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
    logger.info(f"Getting segments with content for {segments} search segments")
    segments_with_content = []
    
    try:
        for search_segment in segments:
            span_start = search_segment.get('input_span_start')
            span_end = search_segment.get('input_span_end')
            search_segment_id = search_segment.get('input_segment_id')
            overlapping_segments = search_segment.get('overlapping_segments')
            logger.info(f"HERE is the search segment {span_start} and {span_end}")
            # Skip if span is out of bounds
            if span_end > len(base_text) or span_start >= len(base_text):
                continue
            
            # Extract search segment content
            search_segment_content = base_text[span_start:span_end]
            
            # Extract overlapping segments for this search segment
            overlapping_content = []
            for overlapping_segment in overlapping_segments:
                overlap_start = overlapping_segment.get('span_start')
                overlap_end = overlapping_segment.get('span_end')
                overlap_segment_id = overlapping_segment.get('segment_id') 
                logger.info(f"HERE is the overlap segment {overlap_start} and {overlap_end}")
                # Skip if span is out of bounds
                if overlap_end > len(base_text) or overlap_start >= len(base_text):
                    continue
                
                overlapping_content.append({
                    "segment_id": overlap_segment_id,
                    "segment_content": base_text[overlap_start:overlap_end]
                })
            
            data = {
                "segment_id": search_segment_id,
                "segment_content": search_segment_content,
                "segments": overlapping_content
            }
            segments_with_content.append(data)
        
        logger.info(f"Successfully processed {len(segments_with_content)} segments with content")
        return segments_with_content
        
    except Exception as exc:
        logger.error(f"Error getting segments with content: {str(exc)}", exc_info=True)
        raise exc
    