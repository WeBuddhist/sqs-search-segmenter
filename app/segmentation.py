"""
Segmentation API - Endpoints for retrieving segmentation results and data.
"""
from fastapi import APIRouter, HTTPException
from milvus_segment_generator.segment import segment_text
import logging
from typing import List, Dict, Any


segmentation = APIRouter(
    prefix="/segmentation",
    tags=["Segmentation Results"]
)

logger = logging.getLogger(__name__)


def get_search_segmentation(text: str, language: str):
    """
    Segment text using the Milvus segment generator.
    """
    try:
        # segment_text returns a tuple: (segments_list, text)
        segments, _ = segment_text(text, language)
        logger.info(f"Raw segmentation result: {segments}")
        return segments
    except Exception as e:
        logger.error(f"Error getting search segmentation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get search segmentation: {str(e)}")


def get_segments_with_content(
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
    