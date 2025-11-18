"""
Multi-process SQS worker for processing segmentation jobs.

This module spawns multiple worker processes that independently poll
AWS SQS and process segmentation tasks in parallel.
"""
import logging
import multiprocessing
import signal
import sys
import time
from typing import Optional

from aws_sqs_consumer import Consumer, Message
import json

from app.config import get
from app.tasks import process_manifestation_task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Worker-%(process)d] - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = multiprocessing.Event()


class SegmentationWorker(Consumer):
    """SQS Consumer for processing segmentation tasks"""
    
    def __init__(self, worker_id: int, queue_url: str, region: str):
        """
        Initialize worker with ID for logging
        
        Args:
            worker_id: Unique identifier for this worker process
            queue_url: AWS SQS queue URL
            region: AWS region
        """
        self.worker_id = worker_id
        logger.info(f"Initializing Worker-{worker_id}")
        
        super().__init__(
            queue_url=queue_url,
            region=region,
            polling_wait_time_ms=20000  # Long polling: 20 seconds
        )
    
    def handle_message(self, message: Message):
        """
        Process a single SQS message
        
        Args:
            message: SQS message containing job details
        """
        try:
            # Parse message body
            json_content = json.loads(message.Body)
            
            job_id = json_content.get('job_id')
            manifestation_id = json_content.get('manifestation_id')
            
            if not manifestation_id:
                logger.error(f"Worker-{self.worker_id}: Missing manifestation_id in message")
                raise ValueError("manifestation_id is required")
            
            logger.info(
                f"Worker-{self.worker_id}: Processing job {job_id} "
                f"for manifestation {manifestation_id}"
            )
            
            # Process the task
            result = process_manifestation_task(
                job_id=job_id,
                manifestation_id=manifestation_id
            )
            
            logger.info(
                f"Worker-{self.worker_id}: Successfully completed job {job_id}. "
                f"Result: {result}"
            )
            
        except json.JSONDecodeError as e:
            logger.error(
                f"Worker-{self.worker_id}: Failed to parse message body: {e}",
                exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Worker-{self.worker_id}: Error processing message: {e}",
                exc_info=True
            )
            # Re-raise to let SQS handle retry logic
            raise


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    shutdown_flag.set()


def worker_process(worker_id: int, queue_url: str, region: str):
    """
    Worker process function that runs the SQS consumer
    
    Args:
        worker_id: Unique identifier for this worker
        queue_url: AWS SQS queue URL
        region: AWS region
    """
    # Set up signal handlers for this process
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info(f"Worker-{worker_id} started (PID: {multiprocessing.current_process().pid})")
    
    try:
        # Create consumer instance for this worker
        consumer = SegmentationWorker(
            worker_id=worker_id,
            queue_url=queue_url,
            region=region
        )
        
        logger.info(f"Worker-{worker_id} polling SQS queue: {queue_url}")
        
        # Start consuming messages
        # Note: consumer.start() blocks, so we run it in the main thread
        consumer.start()
        
    except KeyboardInterrupt:
        logger.info(f"Worker-{worker_id} received interrupt signal")
    except Exception as e:
        logger.error(f"Worker-{worker_id} encountered fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info(f"Worker-{worker_id} shutting down")


def main():
    """
    Main function to spawn and manage worker processes
    """
    # Get configuration
    queue_url = get("SQS_QUEUE_URL")
    region = get("AWS_REGION", "us-east-1")
    num_workers = 4  # Number of worker processes
    
    if not queue_url:
        logger.error("SQS_QUEUE_URL not configured. Cannot start workers.")
        sys.exit(1)
    
    logger.info("=" * 80)
    logger.info("Starting SQS Multi-Worker Service")
    logger.info(f"Queue URL: {queue_url}")
    logger.info(f"Region: {region}")
    logger.info(f"Number of workers: {num_workers}")
    logger.info("=" * 80)
    
    # Set up signal handlers for parent process
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create worker processes
    processes = []
    for i in range(num_workers):
        worker_id = i + 1
        process = multiprocessing.Process(
            target=worker_process,
            args=(worker_id, queue_url, region),
            name=f"Worker-{worker_id}"
        )
        process.start()
        processes.append(process)
        logger.info(f"Started Worker-{worker_id} (PID: {process.pid})")
    
    logger.info(f"All {num_workers} workers started successfully")
    
    try:
        # Wait for shutdown signal
        while not shutdown_flag.is_set():
            # Check if any worker died unexpectedly
            for i, process in enumerate(processes):
                if not process.is_alive():
                    logger.warning(
                        f"Worker-{i+1} (PID: {process.pid}) died unexpectedly. "
                        f"Exit code: {process.exitcode}"
                    )
                    # Optionally restart the worker
                    # (For production, consider implementing backoff/retry logic)
            
            time.sleep(5)  # Check every 5 seconds
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        shutdown_flag.set()
    
    # Graceful shutdown
    logger.info("Shutting down all workers...")
    
    for i, process in enumerate(processes):
        worker_id = i + 1
        if process.is_alive():
            logger.info(f"Terminating Worker-{worker_id} (PID: {process.pid})")
            process.terminate()
    
    # Wait for all processes to finish (with timeout)
    timeout = 30  # seconds
    start_time = time.time()
    
    for i, process in enumerate(processes):
        remaining_time = timeout - (time.time() - start_time)
        if remaining_time > 0:
            process.join(timeout=remaining_time)
        
        if process.is_alive():
            logger.warning(
                f"Worker-{i+1} (PID: {process.pid}) did not terminate gracefully. "
                "Forcing kill..."
            )
            process.kill()
            process.join()
    
    logger.info("All workers shut down. Exiting.")
    sys.exit(0)


if __name__ == "__main__":
    main()

