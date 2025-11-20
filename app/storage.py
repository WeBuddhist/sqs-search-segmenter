import logging
import os
import firebase_admin
from firebase_admin import credentials, storage
from app.config import Config

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (singleton pattern)
_firebase_initialized = False

def _initialize_firebase():
    """Initialize Firebase Admin SDK if not already initialized."""
    global _firebase_initialized
    if not _firebase_initialized:
        try:
            # Try to get existing app
            firebase_admin.get_app()
            _firebase_initialized = True
            logger.info("Firebase app already initialized")
        except ValueError:
            # App doesn't exist, initialize it
            cred_path = Config.get("GOOGLE_CLOUD_API")
            storage_bucket = Config.get("FIREBASE_STORAGE_BUCKET")
            
            if not cred_path:
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set in environment variables")
            
            if not storage_bucket:
                raise ValueError("FIREBASE_STORAGE_BUCKET not set in environment variables")
            
            if not os.path.exists(cred_path):
                raise FileNotFoundError(f"Firebase credentials file not found: {cred_path}")
            
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {"storageBucket": storage_bucket})
            logger.info(f"Firebase initialized with credentials from {cred_path}")
            _firebase_initialized = True

class Storage:
    def __init__(self) -> None:
        _initialize_firebase()
        self.bucket = storage.bucket()

    @staticmethod
    def _base_text_path(expression_id: str, manifestation_id: str) -> str:
        return f"base_texts/{expression_id}/{manifestation_id}.txt"

    def _get_file(self, storage_path: str) -> bytes:
        blob = self.bucket.blob(storage_path)
        blob.reload()

        if not blob.exists():
            raise FileNotFoundError(f"File not found in storage: {storage_path}")

        file_data = blob.download_as_bytes()
        logger.info("Retrieved from storage: %s, size: %s", storage_path, len(file_data))
        return file_data

    def retrieve_base_text(self,expression_id: str, manifestation_id: str) -> str:
        """Fetch base text content from Firebase Storage.

        Expects the file stored at base_texts/{expression_id}/{manifestation_id}.txt
        (consistent with existing storage utilities).
        """
        data = self._get_file(Storage._base_text_path(expression_id, manifestation_id))
        return data.decode("utf-8")