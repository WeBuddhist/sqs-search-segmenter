import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# Get the current environment (dev, test, or prod)
ENVIRONMENT = os.getenv('ENVIRONMENT', 'prod').lower()


def get_env_var(var_name: str, default=None):
    """
    Get environment variable with support for environment-specific prefixes.
    
    Tries in order:
    1. {ENVIRONMENT}_{var_name} (e.g., DEV_NEO4J_URI)
    2. {var_name} (e.g., NEO4J_URI)
    3. default value
    
    Examples:
        If ENVIRONMENT=dev:
        - get_env_var('NEO4J_URI') will try DEV_NEO4J_URI, then NEO4J_URI
        - get_env_var('GEMINI_API_KEY') will try DEV_GEMINI_API_KEY, then GEMINI_API_KEY
    """
    # Try environment-specific variable first (e.g., DEV_NEO4J_URI)
    env_specific_var = f"{ENVIRONMENT}_{var_name}"
    value = os.getenv(env_specific_var)
    
    if value is not None:
        return value
    
    # Fall back to non-prefixed variable (e.g., NEO4J_URI)
    value = os.getenv(var_name)
    
    if value is not None:
        return value
    
    # Return default
    return default


Config = {
    # Environment info
    "ENVIRONMENT": ENVIRONMENT,
    
    # Neo4j Configuration
    "NEO4J_URI": get_env_var('NEO4J_URI'),
    "NEO4J_USER": get_env_var('NEO4J_USER', 'neo4j'),
    "NEO4J_PASSWORD": get_env_var('NEO4J_PASSWORD'),
    
    # AWS SQS Configuration
    "AWS_REGION": get_env_var('AWS_REGION', 'us-east-1'),
    "AWS_ACCESS_KEY_ID": get_env_var('AWS_ACCESS_KEY_ID'),
    "AWS_SECRET_ACCESS_KEY": get_env_var('AWS_SECRET_ACCESS_KEY'),
    "SQS_QUEUE_URL": get_env_var('SQS_QUEUE_URL'),
    "SQS_VISIBILITY_TIMEOUT": int(get_env_var('SQS_VISIBILITY_TIMEOUT', '900')),  # 15 minutes
    "SQS_HEARTBEAT_INTERVAL": int(get_env_var('SQS_HEARTBEAT_INTERVAL', '300')),  # 5 minutes
    
    # Milvus Configuration
    "MILVUS_URI": get_env_var('MILVUS_URI'),
    "MILVUS_TOKEN": get_env_var('MILVUS_TOKEN'),
    "MILVUS_COLLECTION_NAME": get_env_var('MILVUS_COLLECTION_NAME'),
    
    # Firebase Configuration
    "GOOGLE_APPLICATION_CREDENTIALS": get_env_var('GOOGLE_APPLICATION_CREDENTIALS'),
    "FIREBASE_STORAGE_BUCKET": get_env_var('FIREBASE_STORAGE_BUCKET'),
    
    # API Keys
    "GEMINI_API_KEY": get_env_var('GEMINI_API_KEY'),
    
    # Logging
    "LOG_LEVEL": get_env_var('LOG_LEVEL', 'INFO'),
}


def get(key: str, default=None):
    return Config.get(key, default)