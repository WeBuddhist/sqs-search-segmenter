import queue as queue_module
import logging
from typing import override
from dotenv import load_dotenv
from fastapi import HTTPException

from neo4j import GraphDatabase
from app.neo4j_database_validator import Neo4JDatabaseValidator
import os
from app.neo4j_queries import Queries
from app.identifier import generate_id
logger = logging.getLogger(__name__)

load_dotenv(override=True)

# Singleton driver instance - thread-safe and reusable
_neo4j_driver = None

def get_neo4j_driver():
    """Get or create a singleton Neo4j driver instance."""
    global _neo4j_driver
    if _neo4j_driver is None:
        uri = os.environ.get("NEO4J_URI")
        user = os.environ.get("NEO4J_USER", "neo4j")  # Default to "neo4j" if not set
        password = os.environ.get("NEO4J_PASSWORD")
        logger.info(f"Creating Neo4j driver connection to {uri} with user {user}")
        _neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
        _neo4j_driver.verify_connectivity()
        logger.info("Neo4j driver connection established")
    return _neo4j_driver

class Neo4JDatabase:

    def __init__(self, neo4j_uri: str = None, neo4j_auth: tuple = None):
        # Use singleton driver for better concurrency handling
        if neo4j_uri and neo4j_auth:
            self.__driver = GraphDatabase.driver(neo4j_uri, auth=neo4j_auth)
        else:
            self.__driver = get_neo4j_driver()
        
        self.__validator = Neo4JDatabaseValidator()
        logger.info("Neo4JDatabase instance initialized with shared driver")
    

    def get_session(self):
        """Return a new database session."""
        return self.__driver.session()

    @staticmethod
    def get_segments_by_annotation_id(annotation_id: str):
        db = Neo4JDatabase()
        try:
            with Neo4JDatabase.get_session() as session:
                result =  session.execute_read(
                    lambda tx: tx.run(
                        Queries.segments["get_segments_by_annotation_id"],
                        {
                            "annotation_id": annotation_id
                        }
                    ).data()
                )
                logger.info(f"annotation's id {annotation_id} has {len(result)} segments")
                return result
        except Exception as e:
            logger.error(f"Error getting segments by annotation id: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting segments by annotation id: {e}")


    @staticmethod
    def get_expression_id_by_manifestation_id(manifestation_id: str):
        db = Neo4JDatabase()
        try:
            with db.get_session() as session:
                result = session.execute_read(
                    lambda tx: tx.run(
                        Queries.manifestations["get_expression_id_by_manifestation_id"],
                        {
                            "manifestation_id": manifestation_id
                        }
                    ).single()
                )
                expression_id = result["expression_id"]
                title = result["title"]
                language = result["language"]
                return expression_id, title, language
        except Exception as e:
            logger.error(f"Error getting expression id by manifestation id: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting expression id by manifestation id: {e}")


    @staticmethod
    def get_overlapping_segments_by_search_segments_id(segment_ids: list):
        db = Neo4JDatabase()
        try:
            with db.get_session() as session:
                result = session.execute_read(
                    lambda tx: tx.run(
                        Queries.segments["get_overlapping_segments_by_search_segments_id"],
                        {
                            "segment_ids": segment_ids,
                        }
                    ).data()
                )
                logger.info(f"Overlapping segments: {result}")
                logger.info(f"Fetched {len(result)} overlapping segments from Neo4J database")
                return result
            
        except Exception as e:
            logger.error(f"Error getting overlapping segments by search segments id: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting overlapping segments by search segments id: {e}")


    def create_search_segments(self, segmentation_result: list[dict], manifestation_id: str):
        try:
            # Prepare segments data with IDs
            segments_data = []
            for segment in segmentation_result:
                segment_id = generate_id()
                segments_data.append({
                    "segment_id": segment_id,
                    "span_start": segment.get("span_start"),
                    "span_end": segment.get("span_end")
                })
            
            with self.get_session() as session:
                result = session.execute_write(
                    lambda tx: tx.run(
                        Queries.segments["create_search_segmentation_annotation"],
                        {
                            "segments": segments_data,
                            "manifestation_id": manifestation_id,
                            "annotation_id": generate_id()  
                        }
                    )
                ).data()
                return result
        except Exception as e:
            logger.error(f"Error creating search segments: {e}")
            raise HTTPException(status_code=500, detail=f"Error creating search segments: {e}")