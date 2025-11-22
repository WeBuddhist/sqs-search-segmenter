from typing import List, Dict, Any, Set
from pymilvus import MilvusClient
from app import config
import logging
from BoEmbedder.gemini import embed_texts_batch

logger = logging.getLogger(__name__)


milvus_collection_name = config.get('MILVUS_COLLECTION_NAME')
milvus_uri = config.get('MILVUS_URI')
milvus_token = config.get('MILVUS_TOKEN')


def generate_segments_and_upload_to_vector_db_with_batch_embedding(
    segments_content: List[Dict[str, Any]], 
    title: str, 
    language: str,
    embedding_batch_size: int = 20
):
    """
    ALTERNATIVE VERSION: Generate embeddings in batches and upload to Milvus.
    
    This version batches BOTH the embedding API calls AND the uploads for maximum efficiency.
    
    ⚠️ IMPORTANT: To use this function, you need to carefully maintain the order
    of texts and their corresponding segment metadata to avoid mix-ups.
    
    Args:
        segments_content: List of segments with content
        title: Title of the work
        language: Language of the text
        embedding_batch_size: How many texts to embed in one API call (default: 20)
    """
    UPLOAD_BATCH_SIZE = 50  # Upload every 50 segments
    
    try:
        client = MilvusClient(uri=milvus_uri, token=milvus_token)
        
        # Collect all segment IDs to check for existence
        all_segment_ids = []
        for search_segment in segments_content:
            all_segment_ids.append(search_segment.get('segment_id'))
            for each_segment in search_segment.get('segments', []):
                all_segment_ids.append(each_segment.get('segment_id'))
        
        # Check which segments already exist (idempotency)
        existing_ids = check_segments_exist_in_milvus(all_segment_ids)
        
        if len(existing_ids) == len(all_segment_ids):
            logger.info(
                f"All {len(all_segment_ids)} segments already exist in Milvus. "
                "Skipping upload (idempotent operation)."
            )
            return
        
        # Collect all new segments that need embeddings
        # Key insight: Keep metadata paired with text in same order
        segments_to_process = []  # List of (segment_metadata, text) tuples
        
        for search_segment in segments_content:
            segment_id = search_segment.get('segment_id')
            if segment_id not in existing_ids:
                segments_to_process.append({
                    'id': segment_id,
                    'text': search_segment.get('segment_content'),
                    'title': title,
                    'language': language,
                    'parent_id': ""
                })
            
            for each_segment in search_segment.get('segments', []):
                child_segment_id = each_segment.get('segment_id')
                if child_segment_id not in existing_ids:
                    segments_to_process.append({
                        'id': child_segment_id,
                        'text': each_segment.get('segment_content'),
                        'title': title,
                        'language': language,
                        'parent_id': segment_id
                    })
        
        total_to_process = len(segments_to_process)
        logger.info(f"Processing {total_to_process} new segments (skipping {len(existing_ids)} existing)")
        
        # Process in batches for embedding
        upload_buffer = []
        for i in range(0, total_to_process, embedding_batch_size):
            batch = segments_to_process[i:i + embedding_batch_size]
            
            # Extract texts in order
            texts = [seg['text'] for seg in batch]
            
            # Generate embeddings for this batch (ONE API call)
            embeddings = embed_texts_batch(texts, api_key=config.get("GEMINI_API_KEY"))
            
            # ⚠️ CRITICAL: Pair embeddings back with correct metadata using SAME order
            for seg_metadata, embedding in zip(batch, embeddings):
                upload_buffer.append({
                    "id": seg_metadata['id'],
                    "text": seg_metadata['text'],
                    "title": seg_metadata['title'],
                    "language": seg_metadata['language'],
                    "parent_id": seg_metadata['parent_id'],
                    "dense_vector": embedding  # ← Correct pairing via zip()
                })
            
            logger.info(f"Generated embeddings for batch {i//embedding_batch_size + 1} ({len(batch)} segments)")
            
            # Upload if buffer is full
            if len(upload_buffer) >= UPLOAD_BATCH_SIZE:
                client.insert(collection_name=milvus_collection_name, data=upload_buffer)
                logger.info(f"Uploaded {len(upload_buffer)} segments to Milvus")
                upload_buffer = []
        
        # Upload remaining
        if upload_buffer:
            client.insert(collection_name=milvus_collection_name, data=upload_buffer)
            logger.info(f"Uploaded final batch of {len(upload_buffer)} segments to Milvus")
        
        logger.info(f"✅ Successfully processed {total_to_process} segments")
        
    except Exception as exc:
        logger.error(f"Error in batch embedding and upload: {str(exc)}", exc_info=True)
        raise exc


def check_segments_exist_in_milvus(segment_ids: List[str]) -> Set[str]:
    """
    Check which segment IDs already exist in Milvus.
    
    Args:
        segment_ids: List of segment IDs to check
        
    Returns:
        Set of segment IDs that already exist
    """
    try:
        if not segment_ids:
            return set()
            
        client = MilvusClient(uri=milvus_uri, token=milvus_token)
        
        # Query Milvus to check if these IDs exist
        existing_ids = set()
        
        # Milvus doesn't have a direct "exists" check, so we query by ID
        # We'll do this in batches to avoid overwhelming the system
        batch_size = 100
        for i in range(0, len(segment_ids), batch_size):
            batch = segment_ids[i:i+batch_size]
            
            # Use get to fetch by primary key (id)
            results = client.get(
                collection_name=milvus_collection_name,
                ids=batch
            )
            
            # Extract IDs from results
            for result in results:
                if result:
                    existing_ids.add(result.get('id'))
        
        logger.info(f"Found {len(existing_ids)} existing segments out of {len(segment_ids)}")
        return existing_ids
        
    except Exception as e:
        logger.warning(f"Error checking segments in Milvus: {e}. Assuming none exist.")
        return set()


def generate_segments_and_upload_to_vector_db(segments_content: List[Dict[str, Any]], title: str, language: str):
    """
    Generate embeddings and upload segments to Milvus vector database.
    
    This function is idempotent - it checks which segments already exist
    and only uploads new ones, preventing duplicate work.
    
    Uses batch uploading to reduce memory usage and provide incremental progress.
    
    Args:
        segments_content: List of segments with content
        title: Title of the work
        language: Language of the text
    """
    BATCH_SIZE = 50  # Upload every 50 segments to reduce memory and provide progress
    
    try:
        client = MilvusClient(
            uri=milvus_uri,
            token=milvus_token
        )
        
        # Collect all segment IDs to check for existence
        all_segment_ids = []
        for search_segment in segments_content:
            all_segment_ids.append(search_segment.get('segment_id'))
            for each_segment in search_segment.get('segments', []):
                all_segment_ids.append(each_segment.get('segment_id'))
        
        # Check which segments already exist (idempotency)
        existing_ids = check_segments_exist_in_milvus(all_segment_ids)
        
        if len(existing_ids) == len(all_segment_ids):
            logger.info(
                f"All {len(all_segment_ids)} segments already exist in Milvus. "
                "Skipping upload (idempotent operation)."
            )
            return
        
        # Helper function to upload a batch
        def upload_batch(batch_data: List[Dict], batch_num: int):
            if batch_data:
                client.insert(collection_name=milvus_collection_name, data=batch_data)
                logger.info(f"Uploaded batch #{batch_num}: {len(batch_data)} segments")
        
        batch_data = []
        batch_number = 1
        skipped_count = 0
        total_uploaded = 0
        
        logger.info(f"Generating embeddings and uploading to vector database (batch size: {BATCH_SIZE})")
        
        for search_segment in segments_content:
            # Add search segment with its embedding (if not exists)
            segment_id = search_segment.get('segment_id')
            if segment_id not in existing_ids:
                search_segment_content = search_segment.get('segment_content')
                
                # Generate embedding
                dense_vector = embed_texts_batch(
                    [search_segment_content], 
                    api_key=config.get("GEMINI_API_KEY")
                )[0]
                
                batch_data.append({
                    "id": segment_id,
                    "text": search_segment_content,
                    "title": title,
                    "language": language,
                    "parent_id": "",
                    "dense_vector": dense_vector
                })
                
                # Upload batch if full
                if len(batch_data) >= BATCH_SIZE:
                    upload_batch(batch_data, batch_number)
                    total_uploaded += len(batch_data)
                    batch_data = []  # Clear batch
                    batch_number += 1
            else:
                skipped_count += 1
            
            # Add overlapping segments with their embeddings (if not exists)
            for each_segment in search_segment.get('segments', []):
                child_segment_id = each_segment.get('segment_id')
                if child_segment_id not in existing_ids:
                    segment_content = each_segment.get('segment_content')
                    
                    # Generate embedding
                    dense_vector = embed_texts_batch(
                        [segment_content], 
                        api_key=config.get("GEMINI_API_KEY")
                    )[0]
                    
                    batch_data.append({
                        "id": child_segment_id,
                        "text": segment_content,
                        "title": title,
                        "language": language,
                        "parent_id": segment_id,
                        "dense_vector": dense_vector
                    })
                    
                    # Upload batch if full
                    if len(batch_data) >= BATCH_SIZE:
                        upload_batch(batch_data, batch_number)
                        total_uploaded += len(batch_data)
                        batch_data = []  # Clear batch
                        batch_number += 1
                else:
                    skipped_count += 1
        
        # Upload remaining segments in final batch
        if batch_data:
            upload_batch(batch_data, batch_number)
            total_uploaded += len(batch_data)
        
        logger.info(
            f"✅ Successfully uploaded {total_uploaded} new segments to Milvus "
            f"in {batch_number} batch(es) (skipped {skipped_count} existing segments)"
        )
            
    except Exception as exc:
        logger.error(f"Error generating segments and uploading to vector database: {str(exc)}", exc_info=True)
        raise exc


def delete_segments(segment_ids: List[str], batch_size: int = 3000) -> Dict[str, Any]:
    """
    Delete segments from Milvus vector database by segment IDs.
    
    Processes deletion in batches to handle large numbers of segments efficiently.
    
    Args:
        segment_ids: List of segment IDs to delete
        batch_size: Number of segments to delete per batch (default: 100)
        
    Returns:
        Dictionary with deletion statistics
        
    Raises:
        Exception: If deletion fails
    """
    try:
        client = MilvusClient(uri=milvus_uri, token=milvus_token)
        
        total_requested = len(segment_ids)
        total_deleted = 0
        batches_processed = 0
        
        logger.info(f"Starting deletion of {total_requested} segments in batches of {batch_size}")
        
        # Process deletions in batches
        for i in range(0, len(segment_ids), batch_size):
            batch = segment_ids[i:i + batch_size]
            batches_processed += 1
            
            try:
                # Delete segments by IDs
                client.delete(
                    collection_name=milvus_collection_name,
                    ids=batch
                )
                
                batch_count = len(batch)
                total_deleted += batch_count
                
                logger.info(
                    f"Batch {batches_processed}: Deleted {batch_count} segments "
                    f"(Progress: {total_deleted}/{total_requested})"
                )
                
            except Exception as batch_error:
                logger.error(
                    f"Error deleting batch {batches_processed} (IDs: {batch[:5]}...): {batch_error}",
                    exc_info=True
                )
                # Continue with other batches even if one fails
                continue
        
        logger.info(
            f"✅ Deletion complete: {total_deleted}/{total_requested} segments deleted "
            f"in {batches_processed} batch(es)"
        )
        
        return {
            "total_requested": total_requested,
            "total_deleted": total_deleted,
            "batches_processed": batches_processed
        }
        
    except Exception as exc:
        logger.error(f"Error deleting segments from Milvus: {str(exc)}", exc_info=True)
        raise exc