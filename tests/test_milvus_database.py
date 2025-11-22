"""
Tests for milvus_database.py - Milvus vector database operations.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock

from app.milvus_database import generate_segments_and_upload_to_vector_db, delete_segments


class TestMilvusDatabase:
    """Test suite for Milvus database operations."""
    
    @patch('app.milvus_database.milvus_collection_name', 'test_collection')
    @patch('app.milvus_database.milvus_uri', 'http://localhost:19530')
    @patch('app.milvus_database.milvus_token', 'test_token')
    @patch('app.milvus_database.MilvusClient')
    @patch('app.milvus_database.embed_texts_batch')
    @patch('app.milvus_database.config')
    def test_generate_segments_and_upload_success(
        self, mock_config, mock_embed, mock_milvus_client
    ):
        """Test successful generation and upload of segments to Milvus."""
        # Setup mocks
        mock_config.get.return_value = "test_key"  # for GEMINI_API_KEY
        
        # embed_texts_batch returns a list of embeddings, but we always pass single text
        # so it returns [[embedding]] and we take [0]
        mock_embed.return_value = [[0.1] * 768]  # Mock embedding vector
        
        mock_client_instance = MagicMock()
        mock_milvus_client.return_value = mock_client_instance
        
        segments_content = [
            {
                "segment_id": "search_seg_001",
                "segment_content": "Test content 1",
                "segments": [
                    {"segment_id": "overlap_001", "segment_content": "Overlap 1"},
                    {"segment_id": "overlap_002", "segment_content": "Overlap 2"}
                ]
            },
            {
                "segment_id": "search_seg_002",
                "segment_content": "Test content 2",
                "segments": []
            }
        ]
        
        generate_segments_and_upload_to_vector_db(
            segments_content=segments_content,
            title="Test Title",
            language="bo"
        )
        
        # Verify MilvusClient was instantiated correctly
        mock_milvus_client.assert_called_once_with(
            uri="http://localhost:19530",
            token="test_token"
        )
        
        # Verify insert was called
        mock_client_instance.insert.assert_called_once()
        
        # Verify the data structure
        call_args = mock_client_instance.insert.call_args
        assert call_args[1]["collection_name"] == "test_collection"
        data = call_args[1]["data"]
        
        # Should have 3 items: 1 search segment + 2 overlapping + 1 search segment
        assert len(data) == 4
        
        # Check search segment
        assert data[0]["id"] == "search_seg_001"
        assert data[0]["text"] == "Test content 1"
        assert data[0]["title"] == "Test Title"
        assert data[0]["language"] == "bo"
        assert data[0]["parent_id"] == ""
        assert "dense_vector" in data[0]
        
        # Check overlapping segments
        assert data[1]["id"] == "overlap_001"
        assert data[1]["parent_id"] == "search_seg_001"
        assert data[2]["id"] == "overlap_002"
        assert data[2]["parent_id"] == "search_seg_001"
    
    @patch('app.milvus_database.MilvusClient')
    @patch('app.milvus_database.embed_texts_batch')
    @patch('app.milvus_database.config')
    def test_generate_segments_empty_list(
        self, mock_config, mock_embed, mock_milvus_client
    ):
        """Test handling of empty segments list."""
        mock_config.get.side_effect = lambda key: {
            "MILVUS_COLLECTION_NAME": "test_collection",
            "MILVUS_URI": "http://localhost:19530",
            "MILVUS_TOKEN": "test_token",
            "GEMINI_API_KEY": "test_key"
        }.get(key)
        
        mock_client_instance = MagicMock()
        mock_milvus_client.return_value = mock_client_instance
        
        generate_segments_and_upload_to_vector_db(
            segments_content=[],
            title="Test Title",
            language="bo"
        )
        
        # Insert should not be called with empty data
        mock_client_instance.insert.assert_not_called()
    
    @patch('app.milvus_database.MilvusClient')
    @patch('app.milvus_database.embed_texts_batch')
    @patch('app.milvus_database.config')
    def test_generate_segments_no_overlapping(
        self, mock_config, mock_embed, mock_milvus_client
    ):
        """Test segments without overlapping segments."""
        mock_config.get.side_effect = lambda key: {
            "MILVUS_COLLECTION_NAME": "test_collection",
            "MILVUS_URI": "http://localhost:19530",
            "MILVUS_TOKEN": "test_token",
            "GEMINI_API_KEY": "test_key"
        }.get(key)
        
        mock_embed.return_value = [[0.1] * 768]
        mock_client_instance = MagicMock()
        mock_milvus_client.return_value = mock_client_instance
        
        segments_content = [
            {
                "segment_id": "search_seg_001",
                "segment_content": "Test content",
                "segments": []
            }
        ]
        
        generate_segments_and_upload_to_vector_db(
            segments_content=segments_content,
            title="Test Title",
            language="bo"
        )
        
        call_args = mock_client_instance.insert.call_args
        data = call_args[1]["data"]
        
        # Should only have 1 search segment
        assert len(data) == 1
        assert data[0]["id"] == "search_seg_001"
        assert data[0]["parent_id"] == ""
    
    @patch('app.milvus_database.MilvusClient')
    @patch('app.milvus_database.embed_texts_batch')
    @patch('app.milvus_database.config')
    def test_generate_segments_embedding_error(
        self, mock_config, mock_embed, mock_milvus_client
    ):
        """Test handling of embedding generation errors."""
        mock_config.get.side_effect = lambda key: {
            "MILVUS_COLLECTION_NAME": "test_collection",
            "MILVUS_URI": "http://localhost:19530",
            "MILVUS_TOKEN": "test_token",
            "GEMINI_API_KEY": "test_key"
        }.get(key)
        
        mock_embed.side_effect = Exception("Embedding failed")
        mock_client_instance = MagicMock()
        mock_milvus_client.return_value = mock_client_instance
        
        segments_content = [
            {
                "segment_id": "search_seg_001",
                "segment_content": "Test content",
                "segments": []
            }
        ]
        
        with pytest.raises(Exception, match="Embedding failed"):
            generate_segments_and_upload_to_vector_db(
                segments_content=segments_content,
                title="Test Title",
                language="bo"
            )
    
    @patch('app.milvus_database.MilvusClient')
    @patch('app.milvus_database.embed_texts_batch')
    @patch('app.milvus_database.config')
    def test_generate_segments_milvus_insert_error(
        self, mock_config, mock_embed, mock_milvus_client
    ):
        """Test handling of Milvus insert errors."""
        mock_config.get.side_effect = lambda key: {
            "MILVUS_COLLECTION_NAME": "test_collection",
            "MILVUS_URI": "http://localhost:19530",
            "MILVUS_TOKEN": "test_token",
            "GEMINI_API_KEY": "test_key"
        }.get(key)
        
        mock_embed.return_value = [[0.1] * 768]
        mock_client_instance = MagicMock()
        mock_client_instance.insert.side_effect = Exception("Insert failed")
        mock_milvus_client.return_value = mock_client_instance
        
        segments_content = [
            {
                "segment_id": "search_seg_001",
                "segment_content": "Test content",
                "segments": []
            }
        ]
        
        with pytest.raises(Exception, match="Insert failed"):
            generate_segments_and_upload_to_vector_db(
                segments_content=segments_content,
                title="Test Title",
                language="bo"
            )


class TestDeleteSegments:
    """Test suite for delete_segments function."""
    
    @patch('app.milvus_database.milvus_collection_name', 'test_collection')
    @patch('app.milvus_database.milvus_uri', 'http://localhost:19530')
    @patch('app.milvus_database.milvus_token', 'test_token')
    @patch('app.milvus_database.MilvusClient')
    def test_delete_segments_success(self, mock_milvus_client):
        """Test successful deletion of segments."""
        mock_client_instance = MagicMock()
        mock_milvus_client.return_value = mock_client_instance
        
        segment_ids = ["seg_001", "seg_002", "seg_003"]
        
        result = delete_segments(segment_ids)
        
        # Verify MilvusClient was instantiated correctly
        mock_milvus_client.assert_called_once_with(
            uri="http://localhost:19530",
            token="test_token"
        )
        
        # Verify delete was called
        mock_client_instance.delete.assert_called_once()
        
        # Verify call arguments
        call_args = mock_client_instance.delete.call_args
        assert call_args[1]["collection_name"] == "test_collection"
        assert call_args[1]["ids"] == segment_ids
        
        # Verify return value
        assert result["total_requested"] == 3
        assert result["total_deleted"] == 3
        assert result["batches_processed"] == 1
    
    @patch('app.milvus_database.milvus_collection_name', 'test_collection')
    @patch('app.milvus_database.milvus_uri', 'http://localhost:19530')
    @patch('app.milvus_database.milvus_token', 'test_token')
    @patch('app.milvus_database.MilvusClient')
    def test_delete_segments_large_batch(self, mock_milvus_client):
        """Test deletion with multiple batches."""
        mock_client_instance = MagicMock()
        mock_milvus_client.return_value = mock_client_instance
        
        # Create 250 segment IDs (will be split into 3 batches of 100, 100, 50)
        segment_ids = [f"seg_{i:03d}" for i in range(250)]
        
        result = delete_segments(segment_ids, batch_size=100)
        
        # Verify delete was called 3 times
        assert mock_client_instance.delete.call_count == 3
        
        # Verify return value
        assert result["total_requested"] == 250
        assert result["total_deleted"] == 250
        assert result["batches_processed"] == 3
    
    @patch('app.milvus_database.milvus_collection_name', 'test_collection')
    @patch('app.milvus_database.milvus_uri', 'http://localhost:19530')
    @patch('app.milvus_database.milvus_token', 'test_token')
    @patch('app.milvus_database.MilvusClient')
    def test_delete_segments_empty_list(self, mock_milvus_client):
        """Test deletion with empty segment list."""
        mock_client_instance = MagicMock()
        mock_milvus_client.return_value = mock_client_instance
        
        result = delete_segments([])
        
        # Verify delete was never called
        mock_client_instance.delete.assert_not_called()
        
        # Verify return value
        assert result["total_requested"] == 0
        assert result["total_deleted"] == 0
        assert result["batches_processed"] == 0
    
    @patch('app.milvus_database.milvus_collection_name', 'test_collection')
    @patch('app.milvus_database.milvus_uri', 'http://localhost:19530')
    @patch('app.milvus_database.milvus_token', 'test_token')
    @patch('app.milvus_database.MilvusClient')
    def test_delete_segments_partial_failure(self, mock_milvus_client):
        """Test deletion with partial batch failures."""
        mock_client_instance = MagicMock()
        mock_milvus_client.return_value = mock_client_instance
        
        # Make the second batch fail
        mock_client_instance.delete.side_effect = [
            None,  # First batch succeeds
            Exception("Network error"),  # Second batch fails
            None   # Third batch succeeds
        ]
        
        segment_ids = [f"seg_{i:03d}" for i in range(250)]
        
        result = delete_segments(segment_ids, batch_size=100)
        
        # Should continue processing despite batch failure
        assert mock_client_instance.delete.call_count == 3
        
        # Only 2 batches succeeded (batch 1: 100, batch 3: 50 = 150 segments)
        assert result["total_requested"] == 250
        assert result["total_deleted"] == 150
        assert result["batches_processed"] == 3
    
    @patch('app.milvus_database.milvus_collection_name', 'test_collection')
    @patch('app.milvus_database.milvus_uri', 'http://localhost:19530')
    @patch('app.milvus_database.milvus_token', 'test_token')
    @patch('app.milvus_database.MilvusClient')
    def test_delete_segments_client_initialization_error(self, mock_milvus_client):
        """Test handling of Milvus client initialization error."""
        mock_milvus_client.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            delete_segments(["seg_001"])

