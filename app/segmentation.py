"""
Segmentation API - Endpoints for retrieving segmentation results and data.
"""
from fastapi import APIRouter, HTTPException
from milvus_segment_generator.segment import segment_text
import logging
from typing import List, Dict, Any
import os

from app.db.postgres import SessionLocal, get_db
from app.db.models import RootJob
from app.neo4j_database import Neo4JDatabase
from BoEmbedder.gemini import embed_texts_batch
from pymilvus import MilvusClient

segmentation = APIRouter(
    prefix="/segmentation",
    tags=["Segmentation Results"]
)

logger = logging.getLogger(__name__)

@segmentation.get("/{job_id}/status")
def get_segmentation_status(job_id: str):
    try:
        with SessionLocal() as session:
            job = session.query(RootJob).filter(RootJob.job_id == job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            return job
    except:
        raise HTTPException(status_code=500, detail="Failed to get job status, Database read error")


# @segmentation.get("/{manifestation_id}/segments")
# def get_all_segments_by_manifestation(
#     manifestation_id: str,
# ):
#     try:
#         with SessionLocal() as session:
#             root_job = session.query(RootJob).filter(
#                 RootJob.manifestation_id == manifestation_id,
#                 RootJob.status == "COMPLETED"
#             ).order_by(RootJob.created_at.desc()).first()
            
#             if not root_job:
#                 raise HTTPException(
#                     status_code=404,
#                     detail="No completed job found for manifestation"
#                 )
#             return root_job.result_json
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error getting segments: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=500,
#             detail="Failed to get segments, Database error"
#         )
        

@segmentation.get("/")
def get_segments_data_by_job(
    job_id: str,
    manifestation_id: str,
):
    try:
        with SessionLocal() as session:
            root_job = session.query(RootJob).filter(RootJob.manifestation_id == manifestation_id).first()
            if root_job.completed_segments < root_job.total_segments:
                raise HTTPException(status_code=400, detail="Job not completed")
            response = {
                "job_id": job_id,
                "manifestation_id": manifestation_id,
                "segments": root_job.result_json
            }
            return (response), 200
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get all segments relation by manifestation, Database read error, Error: " + str(e))



def get_search_segmentation(text: str, language: str):
    """
    Segment text using the Milvus segment generator.
    """
    try:
        segmentation_result = segment_text(text, language)
        return segmentation_result
    except Exception as e:
        logger.error(f"Error getting search segmentation: {e}", exc_info=True)
        raise HTTPException("Failed to get search segmentation", str(e))


def generate_segments_and_upload_to_vector_db(segments_content: List[Dict[str, Any]], title: str, language: str):
    try:
        # Initialize Milvus client
        MILVUS_URI = os.getenv('MILVUS_URI')
        MILVUS_TOKEN = os.getenv('MILVUS_TOKEN')
        MILVUS_COLLECTION_NAME = os.getenv('MILVUS_COLLECTION_NAME')
        
        client = MilvusClient(
            uri=MILVUS_URI,
            token=MILVUS_TOKEN
        )
        
        data = []
        
        logger.info(f"Generating segments and uploading to vector database")
        for search_segment in segments_content:
            # Add search segment with its embedding
            search_segment_content = search_segment.get('segment_content')
            data.append({
                "id": search_segment.get('segment_id'),
                "text": search_segment_content,
                "title": title,
                "language": language,
                "parent_id": "",
                "dense_vector": embed_texts_batch([search_segment_content])[0]
            })
            # Add overlapping segments with their embeddings
            for each_segment in search_segment.get('segments', []):
                segment_content = each_segment.get('segment_content')
                data.append({
                    "id": each_segment.get('segment_id'),
                    "text": segment_content,
                    "title": title,
                    "language": language,
                    "parent_id": search_segment.get('segment_id'),
                    "dense_vector": embed_texts_batch([segment_content])[0]
                })
        
        # Insert data into Milvus collection
        if data:
            client.insert(collection_name=MILVUS_COLLECTION_NAME, data=data)
            logger.info(f"Successfully inserted {len(data)} segments into Milvus")
        else:
            logger.warning("No data to insert into Milvus")
            
    except Exception as exc:
        logger.error(f"Error generating segments and uploading to vector database: {str(exc)}", exc_info=True)
        raise exc