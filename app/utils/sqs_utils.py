"""
SQS utility functions for message handling, retry logic, and DLQ management.
"""
import json
import logging
import threading
import time
from typing import Dict, Any, Optional, Callable
import boto3
from botocore.exceptions import ClientError
from app.config import get

logger = logging.getLogger(__name__)


class SQSHelper:
    """Helper class for SQS operations"""
    
    def __init__(self):
        self.client = boto3.client(
            'sqs',
            region_name=get('AWS_REGION'),
            aws_access_key_id=get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=get('AWS_SECRET_ACCESS_KEY')
        )
        self.queue_url = get('SQS_QUEUE_URL')
        
        if not self.queue_url:
            raise ValueError("SQS_QUEUE_URL environment variable is required")
    
    def send_message(
        self,
        message_body: Dict[str, Any],
        message_group_id: str = "segmentation",
        delay_seconds: int = 0
    ) -> Optional[str]:
        """
        Send a message to SQS queue.
        
        Args:
            message_body: Dictionary to be sent as message body
            message_group_id: Message group ID for FIFO queues
            delay_seconds: Number of seconds to delay the message
            
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            is_fifo = self.queue_url.endswith('.fifo')
            
            params = {
                'QueueUrl': self.queue_url,
                'MessageBody': json.dumps(message_body),
                'DelaySeconds': delay_seconds
            }
            
            # Add FIFO-specific parameters
            if is_fifo:
                params['MessageGroupId'] = message_group_id
                # Use job_id as deduplication ID if available
                if 'job_id' in message_body:
                    params['MessageDeduplicationId'] = str(message_body['job_id'])
            
            response = self.client.send_message(**params)
            message_id = response.get('MessageId')
            
            logger.info(f"Message sent to SQS. MessageId: {message_id}")
            return message_id
            
        except ClientError as e:
            logger.error(f"Failed to send message to SQS: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending message to SQS: {e}", exc_info=True)
            return None
    
    def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete a message from the queue.
        
        Args:
            receipt_handle: The receipt handle of the message to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info(f"Message deleted from SQS queue")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete message from SQS: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting message from SQS: {e}", exc_info=True)
            return False
    
    def change_message_visibility(
        self,
        receipt_handle: str,
        visibility_timeout: int
    ) -> bool:
        """
        Change the visibility timeout of a message.
        Useful for extending processing time or making message available again.
        
        Args:
            receipt_handle: The receipt handle of the message
            visibility_timeout: New visibility timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout
            )
            logger.info(f"Changed message visibility timeout to {visibility_timeout} seconds")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to change message visibility: {e}", exc_info=True)
            return False
    
    def get_queue_attributes(self) -> Dict[str, Any]:
        """
        Get queue attributes including message counts.
        
        Returns:
            Dictionary with queue attributes
        """
        try:
            response = self.client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=[
                    'ApproximateNumberOfMessages',
                    'ApproximateNumberOfMessagesNotVisible',
                    'ApproximateNumberOfMessagesDelayed'
                ]
            )
            return response.get('Attributes', {})
            
        except ClientError as e:
            logger.error(f"Failed to get queue attributes: {e}", exc_info=True)
            return {}
    
    def purge_queue(self) -> bool:
        """
        Delete all messages in the queue (use with caution!).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.purge_queue(QueueUrl=self.queue_url)
            logger.warning(f"Queue purged: {self.queue_url}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to purge queue: {e}", exc_info=True)
            return False


def parse_sqs_message(message: Any) -> Optional[Dict[str, Any]]:
    """
    Parse an SQS message body.
    
    Args:
        message: The message object from SQS
        
    Returns:
        Parsed message body as dictionary, or None if parsing fails
    """
    try:
        if hasattr(message, 'Body'):
            body = message.Body
        elif isinstance(message, dict) and 'Body' in message:
            body = message['Body']
        else:
            logger.error("Invalid message format")
            return None
        
        # Parse JSON body
        parsed_body = json.loads(body)
        return parsed_body
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse message body as JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing message: {e}")
        return None


def get_message_receipt_handle(message: Any) -> Optional[str]:
    """
    Extract receipt handle from a message.
    
    Args:
        message: The message object from SQS
        
    Returns:
        Receipt handle string, or None if not found
    """
    try:
        if hasattr(message, 'ReceiptHandle'):
            return message.ReceiptHandle
        elif isinstance(message, dict) and 'ReceiptHandle' in message:
            return message['ReceiptHandle']
        else:
            logger.error("Could not find ReceiptHandle in message")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting receipt handle: {e}")
        return None


def calculate_retry_delay(retry_count: int, base_delay: int = 60, max_delay: int = 3600) -> int:
    """
    Calculate exponential backoff delay for retries.
    
    Args:
        retry_count: Number of retry attempts so far
        base_delay: Base delay in seconds (default: 60)
        max_delay: Maximum delay in seconds (default: 3600 = 1 hour)
        
    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (2 ** retry_count), max_delay)
    return delay


class VisibilityTimeoutExtender:
    """
    Automatically extends SQS message visibility timeout during long-running tasks.
    
    This prevents messages from becoming visible again while still being processed,
    which would cause duplicate processing by other workers.
    
    Usage:
        with VisibilityTimeoutExtender(receipt_handle, extension_interval=300):
            # Your long-running task here
            process_job()
    """
    
    def __init__(
        self,
        receipt_handle: str,
        queue_url: str,
        region: str,
        extension_interval: int = 300,  # Extend every 5 minutes
        visibility_timeout: int = 900   # Extend by 15 minutes each time
    ):
        """
        Initialize the visibility timeout extender.
        
        Args:
            receipt_handle: The message's receipt handle
            queue_url: SQS queue URL
            region: AWS region
            extension_interval: How often to extend (seconds)
            visibility_timeout: How much to extend by (seconds)
        """
        self.receipt_handle = receipt_handle
        self.queue_url = queue_url
        self.region = region
        self.extension_interval = extension_interval
        self.visibility_timeout = visibility_timeout
        self.running = False
        self.thread = None
        self.client = None
        
    def __enter__(self):
        """Start the heartbeat thread when entering context"""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the heartbeat thread when exiting context"""
        self.stop()
        return False
    
    def start(self):
        """Start the background heartbeat thread"""
        if self.running:
            logger.warning("VisibilityTimeoutExtender already running")
            return
        
        self.running = True
        self.client = boto3.client('sqs', region_name=self.region)
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()
        logger.info(
            f"Started visibility timeout heartbeat (interval: {self.extension_interval}s, "
            f"timeout: {self.visibility_timeout}s)"
        )
    
    def stop(self):
        """Stop the background heartbeat thread"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Stopped visibility timeout heartbeat")
    
    def _heartbeat_loop(self):
        """Background thread that periodically extends visibility timeout"""
        while self.running:
            try:
                # Wait for the extension interval
                for _ in range(self.extension_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                
                if not self.running:
                    break
                
                # Extend the visibility timeout
                self.client.change_message_visibility(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=self.receipt_handle,
                    VisibilityTimeout=self.visibility_timeout
                )
                logger.debug(
                    f"Extended message visibility timeout by {self.visibility_timeout}s"
                )
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == 'InvalidParameterValue':
                    logger.warning(
                        "Message may have been deleted or processed. Stopping heartbeat."
                    )
                    break
                else:
                    logger.error(f"Failed to extend visibility timeout: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in heartbeat loop: {e}")
                break


def process_with_heartbeat(
    message,
    task_func: Callable,
    queue_url: str,
    region: str,
    extension_interval: int = 300,
    visibility_timeout: int = 900
) -> Any:
    """
    Process a task with automatic visibility timeout extension.
    
    Args:
        message: SQS message object (must have ReceiptHandle attribute)
        task_func: Function to execute (receives no arguments)
        queue_url: SQS queue URL
        region: AWS region
        extension_interval: How often to extend visibility (seconds)
        visibility_timeout: How much to extend by (seconds)
        
    Returns:
        Result from task_func
        
    Raises:
        Any exception from task_func
    """
    receipt_handle = get_message_receipt_handle(message)
    if not receipt_handle:
        raise ValueError("Could not extract receipt handle from message")
    
    with VisibilityTimeoutExtender(
        receipt_handle=receipt_handle,
        queue_url=queue_url,
        region=region,
        extension_interval=extension_interval,
        visibility_timeout=visibility_timeout
    ):
        return task_func()

