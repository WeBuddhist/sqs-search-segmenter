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
        # segment_text returns a tuple: (segments_list, text)
        segments, _ = segment_text(text, language)
        logger.info(f"Raw segmentation result type: {type(segments)}")
        logger.info(f"Raw segmentation result: {segments}")
        
        return segments
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
            print(search_segment)
            data.append({
                "id": search_segment.get('segment_id'),
                "text": search_segment_content,
                "title": title,
                "language": language,
                "parent_id": "",
                "dense_vector": embed_texts_batch([search_segment_content], api_key=os.getenv("GEMINI_API_KEY") )[0]
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
                    "dense_vector": embed_texts_batch([segment_content], api_key=os.getenv("GEMINI_API_KEY"))[0]
                })
        
        # Insert data into Milvus collection
        logger.info(f"HERE is the data to insert into Milvus: {data}")
        if data:
            client.insert(collection_name=MILVUS_COLLECTION_NAME, data=data)
            logger.info(f"Successfully inserted {len(data)} segments into Milvus")
        else:
            logger.warning("No data to insert into Milvus")
            
    except Exception as exc:
        logger.error(f"Error generating segments and uploading to vector database: {str(exc)}", exc_info=True)
        raise exc