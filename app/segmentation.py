"""
Segmentation API - Endpoints for retrieving segmentation results and data.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from milvus_segment_generator.segment import segment_text
import logging

from app.db.postgres import SessionLocal, get_db
from app.db.models import RootJob, ManifestationTask
from app.neo4j_database import Neo4JDatabase

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


@segmentation.get("/{manifestation_id}/segments")
def get_all_segments_by_manifestation(
    manifestation_id: str,
):
    try:
        with SessionLocal() as session:
            root_job = session.query(RootJob).filter(
                RootJob.manifestation_id == manifestation_id,
                RootJob.status == "COMPLETED"
            ).order_by(RootJob.created_at.desc()).first()
            
            if not root_job:
                raise HTTPException(
                    status_code=404,
                    detail="No completed job found for manifestation"
                )
            return root_job.result_json
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting segments: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get segments, Database error"
        )
        

@segmentation.get("/{manifestation_id}/")
def get_segments_data_by_manifestation(
    manifestation_id: str,
):
    try:
        with SessionLocal() as session:
            root_job = session.query(RootJob).filter(RootJob.manifestation_id == manifestation_id).first()
            if root_job.completed_segments < root_job.total_segments:
                raise HTTPException(status_code=400, detail="Job not completed")
            
            segments_with_content = session.query(ManifestationTask).filter(ManifestationTask.manifestation_id == manifestation_id).first().result_json

            response = {
                "manifestation_id": manifestation_id,
                "all_segments": segments_with_content
            }
            return response
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