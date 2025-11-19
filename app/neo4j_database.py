import logging
from neo4j import GraphDatabase
from app.neo4j_queries import Queries
from app.identifier import generate_id
from app.config import Config

logger = logging.getLogger(__name__)

# Singleton driver instance - thread-safe and reusable
_neo4j_driver = None

def get_neo4j_driver():
    """Get or create a singleton Neo4j driver instance."""
    global _neo4j_driver
    if _neo4j_driver is None:
        uri = Config.get("NEO4J_URI")
        user = Config.get("NEO4J_USER", "neo4j")  # Default to "neo4j" if not set
        password = Config.get("NEO4J_PASSWORD")
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
        
        logger.info("Neo4JDatabase instance initialized with shared driver")
    

    def get_session(self):
        """Return a new database session."""
        return self.__driver.session()


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
            raise RuntimeError(f"Error getting expression id by manifestation id: {e}")


    @staticmethod
    def get_overlapping_segments_by_search_segments_id(search_segments: list):
        db = Neo4JDatabase()
        segment_ids = [segment.get('segment_id') for segment in search_segments]
        logger.info(f"HERE are the segment ids: {segment_ids}")
        try:
            with db.get_session() as session:
                result = session.execute_read(
                    lambda tx: tx.run(
                        Queries.segments["get_overlapping_segments_by_search_segments_id_grouped"],
                        {
                            "segment_ids": segment_ids
                        }
                    ).data()
                )
                logger.info(f"HERE is the Overlapping segments: {result}")
                return result
        except Exception as e:
            logger.error(f"Error getting overlapping segments: {e}")
            raise RuntimeError(f"Error getting overlapping segments: {e}")


    def create_search_segments(self, segmentation_result: list[dict], manifestation_id: str):
        db = Neo4JDatabase()
        try:
            # Prepare segments data with IDs and flatten span structure
            formatted_segments = []
            for segment in segmentation_result:
                segment_id = generate_id()
                
                formatted_segments.append({
                    "segment_id": segment_id,
                    "span_start": segment.get("span").get("start"),
                    "span_end": segment.get("span").get("end")
                })

            logger.info(f"Creating {len(formatted_segments)} search segments")
            with db.get_session() as session:
                result = session.execute_write(
                    lambda tx: tx.run(
                        Queries.segments["create_search_segmentation_annotation"],
                        {
                            "segments": formatted_segments,
                            "manifestation_id": manifestation_id,
                            "annotation_id": generate_id()  
                        }
                    ).data()
                )
                logger.info(f"Successfully created search segments in Neo4j")
                return result
        except Exception as e:
            logger.error(f"Error creating search segments: {e}")
            raise RuntimeError(f"Error creating search segments: {e}")


    def check_if_search_segments_exist(self, manifestation_id: str):
        db = Neo4JDatabase()
        try:
            with db.get_session() as session:
                result = session.execute_read(
                    lambda tx: tx.run(
                        Queries.segments["check_if_search_segments_exist"],
                        {
                            "manifestation_id": manifestation_id
                        }
                    ).single()
                )
                logger.info(f"Search segments exist for manifestation {manifestation_id}: {result}")
                return result.get("exists")
        except Exception as e:
            logger.error(f"Error checking if search segments exist: {e}")
            raise RuntimeError(f"Error checking if search segments exist: {e}")


    def get_search_segments(self, manifestation_id: str):
        db = Neo4JDatabase()
        try:
            with db.get_session() as session:
                result = session.execute_read(
                    lambda tx: tx.run(
                        Queries.segments["get_search_segments"],
                        {
                            "manifestation_id": manifestation_id
                        }
                    ).data()
                )
                return result
        except Exception as e:
            logger.error(f"Error getting search segments: {e}")
            raise RuntimeError(f"Error getting search segments: {e}")