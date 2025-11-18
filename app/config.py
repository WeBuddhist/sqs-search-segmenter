import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

Config = {
    "NEO4J_URI": os.getenv('NEO4J_URI', None),
    "NEO4J_USER": os.getenv('NEO4J_USER', None),
    "NEO4J_PASSWORD": os.getenv('NEO4J_PASSWORD', None),
    "POSTGRES_URL": os.getenv('POSTGRES_URL', 'postgresql://admin:pechaAdmin@localhost:5435/pecha'),
    
    # AWS SQS Configuration
    "AWS_REGION": os.getenv('AWS_REGION', 'us-east-1'),
    "AWS_ACCESS_KEY_ID": os.getenv('AWS_ACCESS_KEY_ID', None),
    "AWS_SECRET_ACCESS_KEY": os.getenv('AWS_SECRET_ACCESS_KEY', None),
    "SQS_SEARCH_SEGMENTATION_QUEUE_URL": os.getenv('SQS_SEARCH_SEGMENTATION_QUEUE_URL', None),
    
    # Milvus Configuration
    "MILVUS_URI": os.getenv('MILVUS_URI', None),
    "MILVUS_TOKEN": os.getenv('MILVUS_TOKEN', None),
    "MILVUS_COLLECTION_NAME": os.getenv('MILVUS_COLLECTION_NAME', 'segments'),
    
    # Firebase Configuration
    "GOOGLE_APPLICATION_CREDENTIALS": os.getenv('GOOGLE_APPLICATION_CREDENTIALS', None),
}


def get(key: str, default=None):
    return Config.get(key, default)