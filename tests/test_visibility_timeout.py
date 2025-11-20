"""
Simple tests for SQS visibility timeout extension functionality.
"""
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.utils.sqs_utils import VisibilityTimeoutExtender


class TestVisibilityTimeoutExtender:
    """Test the visibility timeout heartbeat mechanism"""
    
    @patch('app.utils.sqs_utils.boto3.client')
    def test_heartbeat_starts_and_stops(self, mock_boto_client):
        """Test that heartbeat thread starts and stops correctly"""
        mock_sqs = Mock()
        mock_boto_client.return_value = mock_sqs
        
        extender = VisibilityTimeoutExtender(
            receipt_handle="test-receipt-handle",
            queue_url="https://test-queue.amazonaws.com",
            region="us-east-1",
            extension_interval=1,  # 1 second for fast testing
            visibility_timeout=30
        )
        
        # Start the heartbeat
        extender.start()
        assert extender.running is True
        assert extender.thread is not None
        
        # Stop the heartbeat
        extender.stop()
        assert extender.running is False
    
    @patch('app.utils.sqs_utils.boto3.client')
    def test_heartbeat_extends_visibility(self, mock_boto_client):
        """Test that heartbeat actually calls SQS to extend visibility"""
        mock_sqs = Mock()
        mock_boto_client.return_value = mock_sqs
        
        extender = VisibilityTimeoutExtender(
            receipt_handle="test-receipt-handle",
            queue_url="https://test-queue.amazonaws.com",
            region="us-east-1",
            extension_interval=1,  # 1 second
            visibility_timeout=60
        )
        
        # Start and wait for at least one extension
        extender.start()
        time.sleep(1.5)  # Wait for extension to happen
        extender.stop()
        
        # Verify SQS was called to change visibility
        mock_sqs.change_message_visibility.assert_called()
        call_args = mock_sqs.change_message_visibility.call_args[1]
        assert call_args['ReceiptHandle'] == "test-receipt-handle"
        assert call_args['VisibilityTimeout'] == 60
    
    @patch('app.utils.sqs_utils.boto3.client')
    def test_context_manager_usage(self, mock_boto_client):
        """Test using VisibilityTimeoutExtender with 'with' statement"""
        mock_sqs = Mock()
        mock_boto_client.return_value = mock_sqs
        
        # Use context manager
        with VisibilityTimeoutExtender(
            receipt_handle="test-receipt-handle",
            queue_url="https://test-queue.amazonaws.com",
            region="us-east-1",
            extension_interval=1,
            visibility_timeout=30
        ) as extender:
            # Inside context, should be running
            assert extender.running is True
            time.sleep(0.1)
        
        # Outside context, should be stopped
        assert extender.running is False
    
    @patch('app.utils.sqs_utils.boto3.client')
    def test_heartbeat_with_task_execution(self, mock_boto_client):
        """Test that heartbeat works while a task is running"""
        mock_sqs = Mock()
        mock_boto_client.return_value = mock_sqs
        
        task_completed = False
        
        # Simulate a task that takes 2 seconds
        with VisibilityTimeoutExtender(
            receipt_handle="test-receipt-handle",
            queue_url="https://test-queue.amazonaws.com",
            region="us-east-1",
            extension_interval=1,
            visibility_timeout=30
        ):
            time.sleep(2)  # Simulate work
            task_completed = True
        
        assert task_completed is True
        # Should have called extend at least once
        assert mock_sqs.change_message_visibility.call_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

