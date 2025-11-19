"""
Tests for sqs_service.py - SQS consumer and message handling.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import json

from app.sqs_service import SegmentationConsumer


class TestSegmentationConsumer:
    """Test suite for SegmentationConsumer class."""
    
    @patch('app.sqs_service.process_manifestation_task')
    def test_handle_message_success(self, mock_process_task):
        """Test successful message handling."""
        mock_process_task.return_value = {
            "job_id": "job_123",
            "manifestation_id": "manifest_456",
            "status": "COMPLETED"
        }
        
        # Create consumer with mock queue URL
        with patch('app.sqs_service.get') as mock_get:
            mock_get.side_effect = lambda key: {
                "SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/test",
                "AWS_REGION": "us-east-1"
            }.get(key)
            
            consumer = SegmentationConsumer(
                queue_url="https://sqs.us-east-1.amazonaws.com/123/test",
                region="us-east-1",
                polling_wait_time_ms=20000
            )
        
        # Create mock message
        mock_message = Mock()
        mock_message.Body = json.dumps({
            "manifestation_id": "manifest_456",
            "job_id": "job_123"
        })
        
        # Handle message
        consumer.handle_message(mock_message)
        
        # Verify task was called correctly
        mock_process_task.assert_called_once_with(
            job_id="job_123",
            manifestation_id="manifest_456"
        )
    
    @patch('app.sqs_service.process_manifestation_task')
    def test_handle_message_with_different_ids(self, mock_process_task):
        """Test message handling with various ID formats."""
        mock_process_task.return_value = {"status": "COMPLETED"}
        
        with patch('app.sqs_service.get') as mock_get:
            mock_get.side_effect = lambda key: {
                "SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/test",
                "AWS_REGION": "us-east-1"
            }.get(key)
            
            consumer = SegmentationConsumer(
                queue_url="https://sqs.us-east-1.amazonaws.com/123/test",
                region="us-east-1",
                polling_wait_time_ms=20000
            )
        
        test_cases = [
            ("manifest_001", "job_001"),
            ("test-manifest-123", "test-job-123"),
            ("MAN_ABC_XYZ", "JOB_ABC_XYZ")
        ]
        
        for manifest_id, job_id in test_cases:
            mock_message = Mock()
            mock_message.Body = json.dumps({
                "manifestation_id": manifest_id,
                "job_id": job_id
            })
            
            consumer.handle_message(mock_message)
            
            mock_process_task.assert_called_with(
                job_id=job_id,
                manifestation_id=manifest_id
            )
    
    @patch('app.sqs_service.process_manifestation_task')
    def test_handle_message_task_failure(self, mock_process_task):
        """Test message handling when task processing fails."""
        mock_process_task.side_effect = Exception("Processing failed")
        
        with patch('app.sqs_service.get') as mock_get:
            mock_get.side_effect = lambda key: {
                "SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/test",
                "AWS_REGION": "us-east-1"
            }.get(key)
            
            consumer = SegmentationConsumer(
                queue_url="https://sqs.us-east-1.amazonaws.com/123/test",
                region="us-east-1",
                polling_wait_time_ms=20000
            )
        
        mock_message = Mock()
        mock_message.Body = json.dumps({
            "manifestation_id": "manifest_456",
            "job_id": "job_123"
        })
        
        # The exception should propagate (SQS will retry)
        with pytest.raises(Exception, match="Processing failed"):
            consumer.handle_message(mock_message)
    
    @patch('app.sqs_service.process_manifestation_task')
    def test_handle_message_invalid_json(self, mock_process_task):
        """Test message handling with invalid JSON."""
        with patch('app.sqs_service.get') as mock_get:
            mock_get.side_effect = lambda key: {
                "SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/test",
                "AWS_REGION": "us-east-1"
            }.get(key)
            
            consumer = SegmentationConsumer(
                queue_url="https://sqs.us-east-1.amazonaws.com/123/test",
                region="us-east-1",
                polling_wait_time_ms=20000
            )
        
        mock_message = Mock()
        mock_message.Body = "Invalid JSON{"
        
        with pytest.raises(json.JSONDecodeError):
            consumer.handle_message(mock_message)
    
    @patch('app.sqs_service.process_manifestation_task')
    def test_handle_message_missing_fields(self, mock_process_task):
        """Test message handling with missing required fields."""
        with patch('app.sqs_service.get') as mock_get:
            mock_get.side_effect = lambda key: {
                "SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/test",
                "AWS_REGION": "us-east-1"
            }.get(key)
            
            consumer = SegmentationConsumer(
                queue_url="https://sqs.us-east-1.amazonaws.com/123/test",
                region="us-east-1",
                polling_wait_time_ms=20000
            )
        
        # Missing manifestation_id
        mock_message = Mock()
        mock_message.Body = json.dumps({"job_id": "job_123"})
        
        with pytest.raises(KeyError):
            consumer.handle_message(mock_message)
        
        # Missing job_id
        mock_message.Body = json.dumps({"manifestation_id": "manifest_456"})
        
        with pytest.raises(KeyError):
            consumer.handle_message(mock_message)
    
    @patch('app.sqs_service.get')
    def test_consumer_initialization(self, mock_get):
        """Test SegmentationConsumer initialization."""
        mock_get.side_effect = lambda key: {
            "SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/test",
            "AWS_REGION": "us-east-1"
        }.get(key)
        
        consumer = SegmentationConsumer(
            queue_url="https://sqs.us-east-1.amazonaws.com/123/test",
            region="us-east-1",
            polling_wait_time_ms=20000
        )
        
        assert consumer is not None

