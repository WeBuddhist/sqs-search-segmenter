"""
Simple tests for Milvus idempotency and batch upload functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.milvus_database import (
    check_segments_exist_in_milvus,
    generate_segments_and_upload_to_vector_db
)


class TestMilvusIdempotency:
    """Test idempotent upload to Milvus"""
    
    @patch('app.milvus_database.MilvusClient')
    def test_check_segments_exist_returns_existing_ids(self, mock_client_class):
        """Test checking which segments already exist in Milvus"""
        # Mock Milvus client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock response: segments A and B exist, C doesn't
        mock_client.get.return_value = [
            {'id': 'segment-A'},
            {'id': 'segment-B'}
        ]
        
        segment_ids = ['segment-A', 'segment-B', 'segment-C']
        existing = check_segments_exist_in_milvus(segment_ids)
        
        # Should return only existing IDs
        assert 'segment-A' in existing
        assert 'segment-B' in existing
        assert 'segment-C' not in existing
    
    @patch('app.milvus_database.MilvusClient')
    def test_check_segments_exist_handles_empty_list(self, mock_client_class):
        """Test checking with empty segment list"""
        existing = check_segments_exist_in_milvus([])
        
        # Should return empty set
        assert len(existing) == 0
        assert isinstance(existing, set)
    
    @patch('app.milvus_database.embed_texts_batch')
    @patch('app.milvus_database.check_segments_exist_in_milvus')
    @patch('app.milvus_database.MilvusClient')
    def test_upload_skips_existing_segments(
        self, 
        mock_client_class, 
        mock_check_exists,
        mock_embed
    ):
        """Test that upload skips segments that already exist"""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Segment A already exists
        mock_check_exists.return_value = {'segment-A'}
        
        # Mock embeddings
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        
        # Test data: 2 segments, one exists
        segments = [
            {
                'segment_id': 'segment-A',
                'segment_content': 'Text A',
                'segments': []
            },
            {
                'segment_id': 'segment-B',
                'segment_content': 'Text B',
                'segments': []
            }
        ]
        
        # Call the function
        generate_segments_and_upload_to_vector_db(
            segments_content=segments,
            title="Test Title",
            language="en"
        )
        
        # Should only embed segment B (not A, since it exists)
        assert mock_embed.call_count == 1
        embed_call_args = mock_embed.call_args[0][0]
        assert 'Text B' in embed_call_args
        assert 'Text A' not in embed_call_args
        
        # Should only insert segment B
        mock_client.insert.assert_called()
        inserted_data = mock_client.insert.call_args[1]['data']
        assert len(inserted_data) == 1
        assert inserted_data[0]['id'] == 'segment-B'
    
    @patch('app.milvus_database.check_segments_exist_in_milvus')
    @patch('app.milvus_database.MilvusClient')
    def test_upload_skips_when_all_exist(self, mock_client_class, mock_check_exists):
        """Test that upload is skipped entirely when all segments exist"""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # All segments exist
        mock_check_exists.return_value = {'segment-A', 'segment-B'}
        
        # Test data
        segments = [
            {
                'segment_id': 'segment-A',
                'segment_content': 'Text A',
                'segments': []
            },
            {
                'segment_id': 'segment-B',
                'segment_content': 'Text B',
                'segments': []
            }
        ]
        
        # Call the function
        generate_segments_and_upload_to_vector_db(
            segments_content=segments,
            title="Test Title",
            language="en"
        )
        
        # Should NOT insert anything
        mock_client.insert.assert_not_called()
    
    @patch('app.milvus_database.embed_texts_batch')
    @patch('app.milvus_database.check_segments_exist_in_milvus')
    @patch('app.milvus_database.MilvusClient')
    def test_batch_upload_works(self, mock_client_class, mock_check_exists, mock_embed):
        """Test that batch uploading happens when batch size is reached"""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_check_exists.return_value = set()  # No existing segments
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        
        # Create 60 segments (should trigger 2 batches: 50 + 10)
        segments = [
            {
                'segment_id': f'segment-{i}',
                'segment_content': f'Text {i}',
                'segments': []
            }
            for i in range(60)
        ]
        
        # Call the function
        generate_segments_and_upload_to_vector_db(
            segments_content=segments,
            title="Test Title",
            language="en"
        )
        
        # Should insert in 2 batches (50 + 10)
        assert mock_client.insert.call_count == 2
        
        # First batch should have 50 segments
        first_batch = mock_client.insert.call_args_list[0][1]['data']
        assert len(first_batch) == 50
        
        # Second batch should have 10 segments
        second_batch = mock_client.insert.call_args_list[1][1]['data']
        assert len(second_batch) == 10


class TestMilvusBatchEmbedding:
    """Test batch embedding functionality (optional alternative)"""
    
    @patch('app.milvus_database.embed_texts_batch')
    @patch('app.milvus_database.check_segments_exist_in_milvus')
    @patch('app.milvus_database.MilvusClient')
    def test_embeddings_paired_correctly_with_segments(
        self, 
        mock_client_class, 
        mock_check_exists,
        mock_embed
    ):
        """Test that embeddings are correctly paired with their segments"""
        from app.milvus_database import generate_segments_and_upload_to_vector_db_with_batch_embedding
        
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_check_exists.return_value = set()
        
        # Mock embeddings - return predictable values
        def mock_embed_func(texts, **kwargs):
            # Return embeddings that encode the text length
            # So we can verify correct pairing
            return [[float(len(text)), 0.0, 0.0] for text in texts]
        
        mock_embed.side_effect = mock_embed_func
        
        # Test data with different length texts
        segments = [
            {
                'segment_id': 'seg-1',
                'segment_content': 'ABC',  # length 3
                'segments': []
            },
            {
                'segment_id': 'seg-2',
                'segment_content': 'ABCDE',  # length 5
                'segments': []
            }
        ]
        
        # Call the batch embedding function
        generate_segments_and_upload_to_vector_db_with_batch_embedding(
            segments_content=segments,
            title="Test",
            language="en",
            embedding_batch_size=10
        )
        
        # Get the inserted data
        inserted_data = mock_client.insert.call_args[1]['data']
        
        # Verify correct pairing: seg-1 with length-3 embedding
        seg1_data = [d for d in inserted_data if d['id'] == 'seg-1'][0]
        assert seg1_data['dense_vector'][0] == 3.0  # Embedding for 3-char text
        
        # Verify correct pairing: seg-2 with length-5 embedding
        seg2_data = [d for d in inserted_data if d['id'] == 'seg-2'][0]
        assert seg2_data['dense_vector'][0] == 5.0  # Embedding for 5-char text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

