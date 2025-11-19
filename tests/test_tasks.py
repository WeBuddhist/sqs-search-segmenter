"""
Tests for tasks.py - Main task processing business logic.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock

from app.tasks import process_manifestation_task


class TestProcessManifestationTask:
    """Test suite for process_manifestation_task function."""
    
    @patch('app.tasks.generate_segments_and_upload_to_vector_db')
    @patch('app.tasks.get_segments_with_content')
    @patch('app.tasks.get_search_segmentation')
    @patch('app.tasks.Storage')
    @patch('app.tasks.Neo4JDatabase')
    def test_process_manifestation_task_success_new_segments(
        self, mock_neo4j, mock_storage, mock_get_segmentation,
        mock_get_segments_content, mock_upload_to_milvus
    ):
        """Test successful processing when creating new search segments."""
        # Setup mocks
        mock_db_instance = MagicMock()
        mock_neo4j.return_value = mock_db_instance
        
        # Mock get_expression_id_by_manifestation_id
        mock_db_instance.get_expression_id_by_manifestation_id.return_value = (
            "expr_123",
            [{"text": "Test Title"}],
            "bo"
        )
        
        # Mock check_if_search_segments_exist (returns False - need to create)
        mock_db_instance.check_if_search_segments_exist.return_value = False
        
        # Mock create_search_segments
        mock_db_instance.create_search_segments.return_value = [
            {"segment_id": "seg_001", "span_start": 0, "span_end": 15}
        ]
        
        # Mock storage
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.retrieve_base_text.return_value = "Test base text content"
        
        # Mock segmentation
        mock_get_segmentation.return_value = [
            {"span": {"start": 0, "end": 15}}
        ]
        
        # Mock Neo4JDatabase static method
        mock_neo4j.get_overlapping_segments_by_search_segments_id.return_value = [
            {
                "input_segment_id": "seg_001",
                "input_span_start": 0,
                "input_span_end": 15,
                "overlapping_segments": []
            }
        ]
        
        # Mock get_segments_with_content
        mock_get_segments_content.return_value = [
            {
                "segment_id": "seg_001",
                "segment_content": "Test content",
                "segments": []
            }
        ]
        
        # Execute
        result = process_manifestation_task(
            job_id="job_123",
            manifestation_id="manifest_456"
        )
        
        # Assertions
        assert result["status"] == "COMPLETED"
        assert result["job_id"] == "job_123"
        assert result["manifestation_id"] == "manifest_456"
        assert result["segments_count"] == 1
        
        # Verify all steps were called
        mock_db_instance.get_expression_id_by_manifestation_id.assert_called_once()
        mock_storage_instance.retrieve_base_text.assert_called_once()
        mock_get_segmentation.assert_called_once()
        mock_db_instance.create_search_segments.assert_called_once()
        mock_upload_to_milvus.assert_called_once()
    
    @patch('app.tasks.generate_segments_and_upload_to_vector_db')
    @patch('app.tasks.get_segments_with_content')
    @patch('app.tasks.get_search_segmentation')
    @patch('app.tasks.Storage')
    @patch('app.tasks.Neo4JDatabase')
    def test_process_manifestation_task_success_existing_segments(
        self, mock_neo4j, mock_storage, mock_get_segmentation,
        mock_get_segments_content, mock_upload_to_milvus
    ):
        """Test successful processing when search segments already exist."""
        # Setup mocks
        mock_db_instance = MagicMock()
        mock_neo4j.return_value = mock_db_instance
        
        mock_db_instance.get_expression_id_by_manifestation_id.return_value = (
            "expr_123",
            [{"text": "Test Title"}],
            "bo"
        )
        
        # Mock check_if_search_segments_exist (returns True - already exist)
        mock_db_instance.check_if_search_segments_exist.return_value = True
        
        # Mock get_search_segments
        mock_db_instance.get_search_segments.return_value = [
            {"segment_id": "seg_001", "span_start": 0, "span_end": 15}
        ]
        
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.retrieve_base_text.return_value = "Test base text"
        
        mock_neo4j.get_overlapping_segments_by_search_segments_id.return_value = [
            {
                "input_segment_id": "seg_001",
                "input_span_start": 0,
                "input_span_end": 15,
                "overlapping_segments": []
            }
        ]
        
        mock_get_segments_content.return_value = [
            {
                "segment_id": "seg_001",
                "segment_content": "Test",
                "segments": []
            }
        ]
        
        # Execute
        result = process_manifestation_task(
            job_id="job_123",
            manifestation_id="manifest_456"
        )
        
        # Assertions
        assert result["status"] == "COMPLETED"
        
        # Verify segmentation was NOT called (segments already exist)
        mock_get_segmentation.assert_not_called()
        mock_db_instance.create_search_segments.assert_not_called()
        
        # Verify get_search_segments WAS called
        mock_db_instance.get_search_segments.assert_called_once()
    
    @patch('app.tasks.generate_segments_and_upload_to_vector_db')
    @patch('app.tasks.get_segments_with_content')
    @patch('app.tasks.get_search_segmentation')
    @patch('app.tasks.Storage')
    @patch('app.tasks.Neo4JDatabase')
    def test_process_manifestation_task_neo4j_error(
        self, mock_neo4j, mock_storage, mock_get_segmentation,
        mock_get_segments_content, mock_upload_to_milvus
    ):
        """Test error handling when Neo4j fails."""
        mock_db_instance = MagicMock()
        mock_neo4j.return_value = mock_db_instance
        
        mock_db_instance.get_expression_id_by_manifestation_id.side_effect = Exception(
            "Neo4j connection failed"
        )
        
        with pytest.raises(Exception, match="Neo4j connection failed"):
            process_manifestation_task(
                job_id="job_123",
                manifestation_id="manifest_456"
            )
    
    @patch('app.tasks.generate_segments_and_upload_to_vector_db')
    @patch('app.tasks.get_segments_with_content')
    @patch('app.tasks.get_search_segmentation')
    @patch('app.tasks.Storage')
    @patch('app.tasks.Neo4JDatabase')
    def test_process_manifestation_task_storage_error(
        self, mock_neo4j, mock_storage, mock_get_segmentation,
        mock_get_segments_content, mock_upload_to_milvus
    ):
        """Test error handling when storage retrieval fails."""
        mock_db_instance = MagicMock()
        mock_neo4j.return_value = mock_db_instance
        
        mock_db_instance.get_expression_id_by_manifestation_id.return_value = (
            "expr_123",
            [{"text": "Test Title"}],
            "bo"
        )
        
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.retrieve_base_text.side_effect = FileNotFoundError(
            "Base text not found"
        )
        
        with pytest.raises(FileNotFoundError, match="Base text not found"):
            process_manifestation_task(
                job_id="job_123",
                manifestation_id="manifest_456"
            )
    
    @patch('app.tasks.generate_segments_and_upload_to_vector_db')
    @patch('app.tasks.get_segments_with_content')
    @patch('app.tasks.get_search_segmentation')
    @patch('app.tasks.Storage')
    @patch('app.tasks.Neo4JDatabase')
    def test_process_manifestation_task_segmentation_error(
        self, mock_neo4j, mock_storage, mock_get_segmentation,
        mock_get_segments_content, mock_upload_to_milvus
    ):
        """Test error handling when segmentation fails."""
        mock_db_instance = MagicMock()
        mock_neo4j.return_value = mock_db_instance
        
        mock_db_instance.get_expression_id_by_manifestation_id.return_value = (
            "expr_123",
            [{"text": "Test Title"}],
            "bo"
        )
        
        mock_db_instance.check_if_search_segments_exist.return_value = False
        
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.retrieve_base_text.return_value = "Test text"
        
        mock_get_segmentation.side_effect = Exception("Segmentation failed")
        
        with pytest.raises(Exception, match="Segmentation failed"):
            process_manifestation_task(
                job_id="job_123",
                manifestation_id="manifest_456"
            )
    
    @patch('app.tasks.generate_segments_and_upload_to_vector_db')
    @patch('app.tasks.get_segments_with_content')
    @patch('app.tasks.get_search_segmentation')
    @patch('app.tasks.Storage')
    @patch('app.tasks.Neo4JDatabase')
    def test_process_manifestation_task_milvus_error(
        self, mock_neo4j, mock_storage, mock_get_segmentation,
        mock_get_segments_content, mock_upload_to_milvus
    ):
        """Test error handling when Milvus upload fails."""
        mock_db_instance = MagicMock()
        mock_neo4j.return_value = mock_db_instance
        
        mock_db_instance.get_expression_id_by_manifestation_id.return_value = (
            "expr_123",
            [{"text": "Test Title"}],
            "bo"
        )
        
        mock_db_instance.check_if_search_segments_exist.return_value = True
        mock_db_instance.get_search_segments.return_value = [
            {"segment_id": "seg_001", "span_start": 0, "span_end": 15}
        ]
        
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.retrieve_base_text.return_value = "Test text"
        
        mock_neo4j.get_overlapping_segments_by_search_segments_id.return_value = []
        mock_get_segments_content.return_value = []
        
        mock_upload_to_milvus.side_effect = Exception("Milvus upload failed")
        
        with pytest.raises(Exception, match="Milvus upload failed"):
            process_manifestation_task(
                job_id="job_123",
                manifestation_id="manifest_456"
            )
    
    @patch('app.tasks.generate_segments_and_upload_to_vector_db')
    @patch('app.tasks.get_segments_with_content')
    @patch('app.tasks.get_search_segmentation')
    @patch('app.tasks.Storage')
    @patch('app.tasks.Neo4JDatabase')
    def test_process_manifestation_task_with_overlapping_segments(
        self, mock_neo4j, mock_storage, mock_get_segmentation,
        mock_get_segments_content, mock_upload_to_milvus
    ):
        """Test processing with overlapping segments."""
        mock_db_instance = MagicMock()
        mock_neo4j.return_value = mock_db_instance
        
        mock_db_instance.get_expression_id_by_manifestation_id.return_value = (
            "expr_123",
            [{"text": "Test Title"}],
            "bo"
        )
        
        mock_db_instance.check_if_search_segments_exist.return_value = True
        mock_db_instance.get_search_segments.return_value = [
            {"segment_id": "seg_001", "span_start": 0, "span_end": 15}
        ]
        
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.retrieve_base_text.return_value = "Test base text content"
        
        # Mock overlapping segments
        mock_neo4j.get_overlapping_segments_by_search_segments_id.return_value = [
            {
                "input_segment_id": "seg_001",
                "input_span_start": 0,
                "input_span_end": 15,
                "overlapping_segments": [
                    {"segment_id": "overlap_001", "span_start": 0, "span_end": 10},
                    {"segment_id": "overlap_002", "span_start": 10, "span_end": 15}
                ]
            }
        ]
        
        mock_get_segments_content.return_value = [
            {
                "segment_id": "seg_001",
                "segment_content": "Test base text",
                "segments": [
                    {"segment_id": "overlap_001", "segment_content": "Test base "},
                    {"segment_id": "overlap_002", "segment_content": "text"}
                ]
            }
        ]
        
        result = process_manifestation_task(
            job_id="job_123",
            manifestation_id="manifest_456"
        )
        
        assert result["status"] == "COMPLETED"
        assert result["segments_count"] == 1
        
        # Verify upload was called with correct structure
        mock_upload_to_milvus.assert_called_once()
        call_args = mock_upload_to_milvus.call_args
        segments_content = call_args[1]["segments_content"]
        
        assert len(segments_content) == 1
        assert len(segments_content[0]["segments"]) == 2

