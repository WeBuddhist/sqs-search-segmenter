from aws_sqs_consumer import Consumer, Message
from app.tasks import process_manifestation_task
from app.config import get
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

queue_url = get("SQS_SEARCH_SEGMENTATION_QUEUE_URL")

class SimpleConsumer(Consumer):
    def handle_message(self, message: Message):
        json_content = json.loads(message.Body)

        job_id = json_content['job_id']
        manifestation_id = json_content['manifestation_id']
        logger.info(f"Processing job {job_id} for manifestation {manifestation_id}")
        process_manifestation_task(
            job_id=job_id,
            manifestation_id=manifestation_id
        )
        logger.info(f"Job {job_id} for manifestation {manifestation_id} processed successfully")


consumer = SimpleConsumer(
    queue_url=queue_url,
    region=get("AWS_REGION"),
    polling_wait_time_ms=50
)

if __name__ == "__main__":
    logger.info("Starting SQS consumer")
    consumer.start()

        