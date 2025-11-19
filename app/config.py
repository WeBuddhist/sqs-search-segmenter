import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# Get the current environment (dev or prod)
ENVIRONMENT = os.getenv('ENVIRONMENT', 'prod').lower()

Config = {
    # Environment info
    "ENVIRONMENT": ENVIRONMENT,
    
    # Neo4j Configuration
    "NEO4J_URI": os.getenv('NEO4J_URI'),
    "NEO4J_USER": os.getenv('NEO4J_USER'),
    "NEO4J_PASSWORD": os.getenv('NEO4J_PASSWORD'),
    
    # AWS SQS Configuration
    "AWS_REGION": os.getenv('AWS_REGION', 'us-east-1'),
    "AWS_ACCESS_KEY_ID": os.getenv('AWS_ACCESS_KEY_ID'),
    "AWS_SECRET_ACCESS_KEY": os.getenv('AWS_SECRET_ACCESS_KEY'),
    "SQS_QUEUE_URL": os.getenv('SQS_QUEUE_URL'),
    
    # Milvus Configuration
    "MILVUS_URI": os.getenv('MILVUS_URI'),
    "MILVUS_TOKEN": os.getenv('MILVUS_TOKEN'),
    "MILVUS_COLLECTION_NAME": os.getenv('MILVUS_COLLECTION_NAME'),
    
    # Firebase Configuration
    "GOOGLE_APPLICATION_CREDENTIALS": os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
    "FIREBASE_STORAGE_BUCKET": os.getenv('FIREBASE_STORAGE_BUCKET'),
    
    # API Keys
    "GEMINI_API_KEY": os.getenv('GEMINI_API_KEY'),
    
    # Logging
    "LOG_LEVEL": os.getenv('LOG_LEVEL', 'INFO'),
}


def get(key: str, default=None):
    return Config.get(key, default)