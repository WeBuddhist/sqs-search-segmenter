import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# Get the current environment (dev or prod)
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev').lower()

def _get_env_var(var_name: str, default=None):
    """
    Get environment-specific variable.
    First tries {ENV}_{var_name}, then falls back to {var_name}.
    """
    if ENVIRONMENT == 'dev':
        env_prefix = 'DEV_'
    elif ENVIRONMENT == 'prod':
        env_prefix = 'PROD_'
    elif ENVIRONMENT == 'test':
        env_prefix = 'TEST_'
    else:
        raise ValueError(f"Invalid environment: {ENVIRONMENT}")

    env_specific_var = f"{env_prefix}{var_name}"
    
    return os.getenv(env_specific_var)

Config = {
    # Environment info
    "ENVIRONMENT": ENVIRONMENT,
    
    # Neo4j Configuration
    "NEO4J_URI": _get_env_var('NEO4J_URI', None),
    "NEO4J_USER": _get_env_var('NEO4J_USER', None),
    "NEO4J_PASSWORD": _get_env_var('NEO4J_PASSWORD', None),
    
    # AWS SQS Configuration
    "AWS_REGION": _get_env_var('AWS_REGION', 'us-east-1'),
    "AWS_ACCESS_KEY_ID": _get_env_var('AWS_ACCESS_KEY_ID', None),
    "AWS_SECRET_ACCESS_KEY": _get_env_var('AWS_SECRET_ACCESS_KEY', None),
    "SQS_QUEUE_URL": _get_env_var('SQS_QUEUE_URL', None),
    
    # Milvus Configuration
    "MILVUS_URI": _get_env_var('MILVUS_URI', None),
    "MILVUS_TOKEN": _get_env_var('MILVUS_TOKEN', None),
    "MILVUS_COLLECTION_NAME": _get_env_var('MILVUS_COLLECTION_NAME'),
    
    # Firebase Configuration
    "GOOGLE_APPLICATION_CREDENTIALS": _get_env_var('GOOGLE_APPLICATION_CREDENTIALS', None),
    "FIREBASE_STORAGE_BUCKET": _get_env_var('FIREBASE_STORAGE_BUCKET', None),
    
    # API Keys (environment agnostic)
    "GEMINI_API_KEY": os.getenv('GEMINI_API_KEY', None),
    
    # Logging
    "LOG_LEVEL": os.getenv('LOG_LEVEL', 'INFO'),
}


def get(key: str, default=None):
    return Config.get(key, default)