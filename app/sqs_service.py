from aws_sqs_consumer import Consumer, Message
from app.tasks import process_manifestation_task
from app.config import get
import json

queue_url = get("SQS_QUEUE_URL")


class SegmentationConsumer(Consumer):
    def handle_message(self, message: Message):
        json_content = json.loads(message.Body)
        
        manifestation_id = json_content['manifestation_id']
        job_id = json_content['job_id']

        result = process_manifestation_task(
            job_id=job_id,
            manifestation_id=manifestation_id
        )
        print("Processing result:", result)


consumer = SegmentationConsumer(
    queue_url=queue_url,
    region=get("AWS_REGION"),
    polling_wait_time_ms=20000
)