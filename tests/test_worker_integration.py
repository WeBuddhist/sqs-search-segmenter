"""
Simple integration tests for worker with heartbeat functionality.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.worker import SegmentationWorker


class TestWorkerWithHeartbeat:
    """Test worker integration with visibility timeout extension"""
    
    @patch('app.worker.process_manifestation_task')
    @patch('app.worker.VisibilityTimeoutExtender')
    @patch('app.worker.get')
    def test_worker_uses_heartbeat_during_processing(
        self, 
        mock_get,
        mock_extender_class,
        mock_process_task
    ):
        """Test that worker starts heartbeat when processing a message"""
        # Setup config
        mock_get.side_effect = lambda key, default=None: {
            'SQS_VISIBILITY_TIMEOUT': 900,
            'SQS_HEARTBEAT_INTERVAL': 300
        }.get(key, default)
        
        # Mock the extender
        mock_extender = MagicMock()
        mock_extender_class.return_value = mock_extender
        
        # Mock successful task processing
        mock_process_task.return_value = {
            'job_id': 'test-job-123',
            'status': 'COMPLETED'
        }
        
        # Create worker
        worker = SegmentationWorker(
            worker_id=1,
            queue_url="https://test-queue.amazonaws.com",
            region="us-east-1"
        )
        
        # Create mock message
        mock_message = Mock()
        mock_message.Body = json.dumps({
            'job_id': 'test-job-123',
            'manifestation_id': 'manifest-456'
        })
        mock_message.ReceiptHandle = 'test-receipt-handle'
        
        # Process the message
        worker.handle_message(mock_message)
        
        # Verify heartbeat extender was created with correct parameters
        mock_extender_class.assert_called_once()
        call_kwargs = mock_extender_class.call_args[1]
        assert call_kwargs['receipt_handle'] == 'test-receipt-handle'
        assert call_kwargs['queue_url'] == "https://test-queue.amazonaws.com"
        assert call_kwargs['region'] == "us-east-1"
        assert call_kwargs['extension_interval'] == 300
        assert call_kwargs['visibility_timeout'] == 900
        
        # Verify extender was used as context manager
        mock_extender.__enter__.assert_called_once()
        mock_extender.__exit__.assert_called_once()
        
        # Verify task was actually processed
        mock_process_task.assert_called_once_with(
            job_id='test-job-123',
            manifestation_id='manifest-456'
        )
    
    @patch('app.worker.process_manifestation_task')
    @patch('app.worker.VisibilityTimeoutExtender')
    @patch('app.worker.get')
    def test_worker_heartbeat_stops_after_task_completes(
        self,
        mock_get,
        mock_extender_class,
        mock_process_task
    ):
        """Test that heartbeat stops when task completes"""
        mock_get.side_effect = lambda key, default=None: {
            'SQS_VISIBILITY_TIMEOUT': 900,
            'SQS_HEARTBEAT_INTERVAL': 300
        }.get(key, default)
        
        mock_extender = MagicMock()
        mock_extender_class.return_value = mock_extender
        mock_process_task.return_value = {'status': 'COMPLETED'}
        
        worker = SegmentationWorker(
            worker_id=1,
            queue_url="https://test-queue.amazonaws.com",
            region="us-east-1"
        )
        
        mock_message = Mock()
        mock_message.Body = json.dumps({
            'job_id': 'test-123',
            'manifestation_id': 'manifest-456'
        })
        mock_message.ReceiptHandle = 'test-receipt'
        
        # Process message
        worker.handle_message(mock_message)
        
        # Verify __exit__ was called (heartbeat stopped)
        assert mock_extender.__exit__.called
    
    @patch('app.worker.process_manifestation_task')
    @patch('app.worker.VisibilityTimeoutExtender')
    @patch('app.worker.get')
    def test_worker_heartbeat_stops_even_on_error(
        self,
        mock_get,
        mock_extender_class,
        mock_process_task
    ):
        """Test that heartbeat stops even if task fails"""
        mock_get.side_effect = lambda key, default=None: {
            'SQS_VISIBILITY_TIMEOUT': 900,
            'SQS_HEARTBEAT_INTERVAL': 300
        }.get(key, default)
        
        mock_extender = MagicMock()
        mock_extender_class.return_value = mock_extender
        
        # Make task fail
        mock_process_task.side_effect = Exception("Processing failed!")
        
        worker = SegmentationWorker(
            worker_id=1,
            queue_url="https://test-queue.amazonaws.com",
            region="us-east-1"
        )
        
        mock_message = Mock()
        mock_message.Body = json.dumps({
            'job_id': 'test-123',
            'manifestation_id': 'manifest-456'
        })
        mock_message.ReceiptHandle = 'test-receipt'
        
        # Process message (should raise exception)
        with pytest.raises(Exception, match="Processing failed!"):
            worker.handle_message(mock_message)
        
        # Verify __exit__ was still called (heartbeat stopped even on error)
        assert mock_extender.__exit__.called
    
    @patch('app.worker.get')
    def test_worker_handles_missing_manifestation_id(self, mock_get):
        """Test that worker raises error when manifestation_id is missing"""
        mock_get.side_effect = lambda key, default=None: {
            'SQS_VISIBILITY_TIMEOUT': 900,
            'SQS_HEARTBEAT_INTERVAL': 300
        }.get(key, default)
        
        worker = SegmentationWorker(
            worker_id=1,
            queue_url="https://test-queue.amazonaws.com",
            region="us-east-1"
        )
        
        # Message without manifestation_id
        mock_message = Mock()
        mock_message.Body = json.dumps({
            'job_id': 'test-123'
            # manifestation_id is missing!
        })
        mock_message.ReceiptHandle = 'test-receipt'
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="manifestation_id is required"):
            worker.handle_message(mock_message)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

