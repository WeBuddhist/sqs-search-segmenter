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
        base_text = "སངས་རྒྱས་ལ་བསྟོད་པ་གང་ཚེ་རྐང་གཉིས་མ་ཟེར་བ་དེ་རེད།ནམ་ཞིག་མི་ཚང་མའི་གཙོ་བོ་ཁྱོད་སྐྱེ་དུས། ས་གཞི་འདིའི་ཐོག་ལ་གོམ་པ་བདུན་སྤོས་ནས། ‘འཇིག་རྟེན་འདིའི་ནང་ལ་ང་རང་གཙོ་བོ་ཡིན།’ ཟེར་ནས་ལབ་པ་རེད། དུས་དེར་མཁས་པ་ཁྱོད་ལ་ཕྱག་འཚལ་གྱི་ཡོད།དང་པོ་དགའ་ལྡན་ལྷའི་ཡུལ་ནས་ཡོང་། རྒྱལ་པོའི་ཕོ་བྲང་ནང་ལ་ཨ་མའི་མངལ་དུ་འཛུལ། ལུམྦི་ནི་སྐྱེད་མོས་ཚལ་ནང་ལ་སྐྱེས། ལྷ་ཚང་མའི་ནང་གི་ལྷ་ཆེ་ཤོས་ཁྱོད་ལ་ཕྱག་འཚལ་གྱི་ཡོད།ཕོ་བྲང་ནང་ལ་མ་མ་སུམ་ཅུ་སོ་གཉིས་ཀྱིས་ལྟ་སྐྱོང་བྱས། ཤཱཀྱའི་གྲོང་ཁྱེར་ནང་ལ་གཞོན་ནུ་སྐབས་ཀྱི་རྩེད་མོ་བརྩེས། སེར་སྐྱའི་གྲོང་ཁྱེར་ནང་ལ་ས་འཚོ་མ་ཟེར་བ་དེ་མནའ་མར་བླངས། འཇིག་རྟེན་འདིའི་ནང་ལ་འགྲན་ཟླ་མེད་པ་ཁྱོད་ལ་ཕྱག་འཚལ་གྱི་ཡོད།གྲོང་ཁྱེར་གྱི་སྒོ་བཞིའི་ནང་ལ་ཕྱིན་ནས་སེམས་སྐྱོ་པོ་ཆགས་པའི་རྣམ་འགྱུར་བསྟན། མཆོད་རྟེན་རྣམ་དག་ཟེར་བའི་འགྲམ་ལ་རང་གི་སྐྲ་བྲེགས། ནཻ་རཉྫ་ནཱ་ཟེར་བའི་གཙང་པོའི་འགྲམ་ལ་ལུས་སེམས་ལ་དཀའ་ལས་བཏང་ནས་སྒོམ་བརྒྱབ། སེམས་ཀྱི་སྐྱོན་ཚང་མ་མེད་པ་ཁྱོད་ལ་ཕྱག་འཚལ་གྱི་ཡོད།རྒྱལ་པོའི་ཁབ་ཟེར་བའི་ས་ཆ་དེར་གླང་ཆེན་སྨྱོན་པ་ཞིག་བཏུལ། ཡངས་པ་ཅན་ཟེར་བའི་ས་ཆ་དེར་སྤྲེའུ་ཞིག་གིས་སྦྲང་རྩི་ཕུལ། མ་ག་དྷ་ཟེར་བའི་ས་ཆ་དེར་སངས་རྒྱས། ཤེས་རབ་མེ་ནང་བཞིན་འབར་མཁན་ཁྱོད་ལ་ཕྱག་འཚལ་གྱི་ཡོད།ཝཱ་ར་ཎཱ་སི་ལ་དང་པོ་ཆོས་བཤད། ཛེ་ཏའི་ཚལ་ཟེར་བའི་ནང་ལ་རྫུ་འཕྲུལ་ཆེན་པོ་བསྟན། རྩྭ་མཆོག་གྲོང་ཟེར་བའི་ས་ཆ་དེར་གྲོངས། སེམས་ནམ་མཁའ་ནང་བཞིན་ཡངས་པ་ཁྱོད་ལ་ཕྱག་འཚལ་གྱི་ཡོད།ངས་སངས་རྒྱས་ཀྱི་བྱ་བ་བྱས་པ་ཚོ་ལ་བསྟོད་པ་ཐུང་ཐུང་འདི་བྲིས་པའི་དགེ་བ་འདིས། སེམས་ཅན་ཚང་མའི་བྱ་སྤྱོད་ཚང་མ་ཡང་སངས་རྒྱས་ཀྱི་བྱ་སྤྱོད་ནང་བཞིན་ཏག་ཏག་ཆགས་པར་ཤོག བསྟོད་པ་འདི་སློབ་དཔོན་དཔའ་བོ་ཟེར་མཁན་དེས་བྲིས་པ་རེད།"
        logger.info(f"Retrieved base text with {len(base_text)} characters")
        

        segmentation_result = get_search_segmentation(base_text, language)
        segmentation_result = [
            {
                "span": {
                    "start": 0,
                    "end": 1391
                }
            }
        ]
        logger.info(f"Segmentation result: {segmentation_result}")
        search_segments = db.create_search_segments(segmentation_result, manifestation_id)
        logger.info(f"Created {len(search_segments)} search segments in Neo4j")
        
        logger.info(f"Fetching overlapping segments from Neo4j")
        # Extract segment IDs from search_segments
        overlapping_mappings = Neo4JDatabase.get_overlapping_segments_by_search_segments_id(search_segments)
        logger.info(f"Fetched {len(overlapping_mappings)} overlapping segments")

        # Process segments with content
        logger.info(f"Processing segments with content")
        segments_with_content = _get_segments_with_content(
            search_segments=search_segments,
            overlapping_segments=overlapping_mappings,
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
    logger.info(f"Getting segments with content for {len(segments)} search segments")
    segments_with_content = []
    
    try:
        for search_segment in segments:
            span_start = search_segment.get('span').get('start')
            span_end = search_segment.get('span').get('end')
            segment_id = search_segment.get('segment_id')
            overlapping_segments = search_segment.get('segments')
            
            # Skip if span is out of bounds
            if span_end > len(base_text) or span_start >= len(base_text):
                continue
            
            # Extract search segment content
            search_segment_content = base_text[span_start:span_end]
            
            # Extract overlapping segments for this search segment
            overlapping_content = []
            for overlapping_segment in overlapping_segments:
                overlap_start = overlapping_segment.get('span').get('start')
                overlap_end = overlapping_segment.get('span').get('end')
                overlap_segment_id = overlapping_segment.get('overlapping_segment_id') 
                
                # Skip if span is out of bounds
                if overlap_end > len(base_text) or overlap_start >= len(base_text):
                    continue
                
                overlapping_content.append({
                    "segment_id": overlap_segment_id,
                    "segment_content": base_text[overlap_start:overlap_end]
                })
            
            data = {
                "segment_id": segment_id,
                "segment_content": search_segment_content,
                "segments": overlapping_content
            }
            segments_with_content.append(data)
        
        logger.info(f"Successfully processed {len(segments_with_content)} segments with content")
        return segments_with_content
        
    except Exception as exc:
        logger.error(f"Error getting segments with content: {str(exc)}", exc_info=True)
        raise exc

if __name__ == "__main__":
    process_manifestation_task(manifestation_id="qqyEEnVA4IrQ510gxvxWD")
    