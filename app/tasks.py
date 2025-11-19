"""
Task processing module - Core logic for processing segmentation jobs.

This module contains the main task processing functions that:
1. Fetch data from Neo4j
2. Process segmentation logic
3. Upload results to vector database
4. Log processing status
"""
import logging
from typing import Dict, Any
from dotenv import load_dotenv

from app.neo4j_database import Neo4JDatabase
from app.storage import Storage
from app.segmentation import get_search_segmentation, get_segments_with_content
from app.milvus_database import generate_segments_and_upload_to_vector_db


load_dotenv(override=True)
logger = logging.getLogger(__name__)


def process_manifestation_task(job_id: str, manifestation_id: str) -> Dict[str, Any]:
    """
    Main task processing function for segmentation jobs.
    
    This function:
    1. Fetches data from Neo4j (expression_id, title, language)
    2. Retrieves base text from storage
    3. Processes segments with content
    4. Uploads results to vector database
    5. Logs processing status
    
    Args:
        job_id: UUID of the job (for logging/tracking)
        manifestation_id: ID of the manifestation to process
        
    Returns:
        Dictionary with job results
        
    Raises:
        Exception: Any error during processing (will trigger SQS retry)
    """
    logger.info(f"[Job {job_id}] Starting processing for manifestation {manifestation_id}")
    
    try:
        # Initialize connections
        db = Neo4JDatabase()
        storage = Storage()

        # Fetch data from Neo4j
        expression_id, title, language = db.get_expression_id_by_manifestation_id(
            manifestation_id=manifestation_id
        )
        title = title[0]['text'] if title else ""
        logger.info(f"[Job {job_id}] Manifestation id: {manifestation_id} has Expression id: {expression_id}")
        
        # Retrieve base text from storage
        logger.info(f"[Job {job_id}] Language: {language}, Title: {title}")
        base_text = storage.retrieve_base_text(
            expression_id=expression_id,
            manifestation_id=manifestation_id
        )
        logger.info(f"[Job {job_id}] Retrieved base text with {len(base_text)} characters")

        check_if_search_segments_exist = db.check_if_search_segments_exist(manifestation_id)
        if check_if_search_segments_exist:
            search_segments = db.get_search_segments(manifestation_id)
            logger.info(f"[Job {job_id}] Fetched {len(search_segments)} search segments from Neo4j")
        else:
            segmentation_result = get_search_segmentation(base_text, language)
            logger.info(f"[Job {job_id}] Segmented base text into {len(segmentation_result)} segments")
            search_segments = db.create_search_segments(segmentation_result, manifestation_id)
            logger.info(f"[Job {job_id}] Created {len(search_segments)} search segments in Neo4j")
            
        overlapping_mappings = Neo4JDatabase.get_overlapping_segments_by_search_segments_id(search_segments)
        logger.info(f"[Job {job_id}] Fetched {len(overlapping_mappings)} overlapping segments")

        # Process segments with content
        logger.info(f"[Job {job_id}] Processing segments with content")
        segments_with_content = get_segments_with_content(
            segments=overlapping_mappings,
            base_text=base_text
        )
        logger.info(f"[Job {job_id}] Processed {len(segments_with_content)} segments with content")
        
        generate_segments_and_upload_to_vector_db(
            segments_content=segments_with_content,
            title=title,
            language=language
        )
        logger.info(f"[Job {job_id}] ✅ Successfully completed processing for manifestation {manifestation_id}")

        return {
            "job_id": job_id,
            "manifestation_id": manifestation_id,
            "segments_count": len(segments_with_content),
            "status": "COMPLETED"
        }
    
    except Exception as exc:
        logger.error(
            f"[Job {job_id}] ❌ FAILED processing manifestation {manifestation_id}: {str(exc)}",
            exc_info=True
        )
        
        # Re-raise to trigger SQS retry
        raise exc
    