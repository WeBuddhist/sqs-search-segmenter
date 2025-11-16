import logging

from firebase_admin import storage
from google.cloud.storage.blob import Blob

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self) -> None:
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