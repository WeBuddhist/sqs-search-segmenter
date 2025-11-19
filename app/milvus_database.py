from typing import List, Dict, Any
from pymilvus import MilvusClient
from app import config
import logging
from BoEmbedder.gemini import embed_texts_batch

logger = logging.getLogger(__name__)


milvus_collection_name = config.get('MILVUS_COLLECTION_NAME')
milvus_uri = config.get('MILVUS_URI')
milvus_token = config.get('MILVUS_TOKEN')


def generate_segments_and_upload_to_vector_db(segments_content: List[Dict[str, Any]], title: str, language: str):
    try:
        client = MilvusClient(
            uri=milvus_uri,
            token=milvus_token
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
                "dense_vector": embed_texts_batch([search_segment_content], api_key=config.get("GEMINI_API_KEY") )[0]
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
                    "dense_vector": embed_texts_batch([segment_content], api_key=config.get("GEMINI_API_KEY"))[0]
                })
        
        if data:
            client.insert(collection_name=milvus_collection_name, data=data)
            logger.info(f"Successfully inserted {len(data)} segments into Milvus")
        else:
            logger.warning("No data to insert into Milvus")
            
    except Exception as exc:
        logger.error(f"Error generating segments and uploading to vector database: {str(exc)}", exc_info=True)
        raise exc