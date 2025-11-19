"""
Tests for storage.py - Firebase Storage operations.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from app.storage import Storage, _initialize_firebase
import firebase_admin


class TestStorage:
    """Test suite for Storage class."""
    
    @patch('app.storage.credentials')
    @patch('app.storage.firebase_admin')
    @patch('app.storage.storage')
    @patch('app.storage.Config')
    @patch('os.path.exists', return_value=True)
    def test_storage_initialization(self, mock_exists, mock_config, mock_storage, mock_firebase_admin, mock_credentials):
        """Test Storage initialization."""
        mock_config.get.side_effect = lambda key: {
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json",
            "FIREBASE_STORAGE_BUCKET": "test-bucket.appspot.com"
        }.get(key)
        
        # Reset the global flag
        import app.storage as storage_module
        storage_module._firebase_initialized = False
        
        # Mock firebase_admin functions
        mock_firebase_admin.get_app.side_effect = ValueError("No app")
        mock_cred = MagicMock()
        mock_credentials.Certificate.return_value = mock_cred
        mock_firebase_admin.initialize_app.return_value = None
        
        # Mock storage bucket
        mock_bucket = MagicMock()
        mock_storage.bucket.return_value = mock_bucket
        
        storage = Storage()
        assert storage.bucket is not None
        
        # Verify initialization was called correctly
        mock_credentials.Certificate.assert_called_once_with("/path/to/creds.json")
        mock_firebase_admin.initialize_app.assert_called_once_with(
            mock_cred, {"storageBucket": "test-bucket.appspot.com"}
        )
    
    def test_base_text_path(self, sample_expression_id, sample_manifestation_id):
        """Test _base_text_path static method."""
        path = Storage._base_text_path(sample_expression_id, sample_manifestation_id)
        expected = f"base_texts/{sample_expression_id}/{sample_manifestation_id}.txt"
        assert path == expected
    
    @patch('app.storage.firebase_admin')
    @patch('app.storage.storage')
    @patch('app.storage.Config')
    def test_retrieve_base_text_success(
        self, mock_config, mock_storage, mock_firebase_admin,
        sample_expression_id, sample_manifestation_id, sample_base_text
    ):
        """Test successful retrieval of base text."""
        mock_config.get.side_effect = lambda key: {
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json",
            "FIREBASE_STORAGE_BUCKET": "test-bucket.appspot.com"
        }.get(key)
        
        mock_firebase_admin.get_app.return_value = MagicMock()
        
        # Mock bucket and blob
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_bytes.return_value = sample_base_text.encode('utf-8')
        mock_bucket.blob.return_value = mock_blob
        mock_storage.bucket.return_value = mock_bucket
        
        storage = Storage()
        result = storage.retrieve_base_text(sample_expression_id, sample_manifestation_id)
        
        assert result == sample_base_text
        mock_blob.download_as_bytes.assert_called_once()
    
    @patch('app.storage.firebase_admin')
    @patch('app.storage.storage')
    @patch('app.storage.Config')
    def test_retrieve_base_text_file_not_found(
        self, mock_config, mock_storage, mock_firebase_admin,
        sample_expression_id, sample_manifestation_id
    ):
        """Test retrieval when file doesn't exist."""
        mock_config.get.side_effect = lambda key: {
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json",
            "FIREBASE_STORAGE_BUCKET": "test-bucket.appspot.com"
        }.get(key)
        
        mock_firebase_admin.get_app.return_value = MagicMock()
        
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob
        mock_storage.bucket.return_value = mock_bucket
        
        storage = Storage()
        
        with pytest.raises(FileNotFoundError):
            storage.retrieve_base_text(sample_expression_id, sample_manifestation_id)
    
    @patch('app.storage.firebase_admin')
    @patch('app.storage.Config')
    def test_initialize_firebase_missing_credentials(self, mock_config, mock_firebase_admin):
        """Test initialization with missing credentials."""
        mock_config.get.side_effect = lambda key: None
        mock_firebase_admin.get_app.side_effect = ValueError("No app")
        
        # Reset the global flag
        import app.storage as storage_module
        storage_module._firebase_initialized = False
        
        with pytest.raises(ValueError, match="GOOGLE_APPLICATION_CREDENTIALS not set"):
            storage = Storage()
    
    @patch('app.storage.firebase_admin')
    @patch('app.storage.Config')
    def test_initialize_firebase_missing_bucket(self, mock_config, mock_firebase_admin):
        """Test initialization with missing storage bucket."""
        mock_config.get.side_effect = lambda key: {
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json"
        }.get(key)
        mock_firebase_admin.get_app.side_effect = ValueError("No app")
        
        # Reset the global flag
        import app.storage as storage_module
        storage_module._firebase_initialized = False
        
        with pytest.raises(ValueError, match="FIREBASE_STORAGE_BUCKET not set"):
            storage = Storage()
    
    @patch('app.storage.firebase_admin')
    @patch('app.storage.storage')
    @patch('app.storage.Config')
    def test_get_file_download_error(
        self, mock_config, mock_storage, mock_firebase_admin,
        sample_expression_id, sample_manifestation_id
    ):
        """Test handling of download errors."""
        mock_config.get.side_effect = lambda key: {
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json",
            "FIREBASE_STORAGE_BUCKET": "test-bucket.appspot.com"
        }.get(key)
        
        mock_firebase_admin.get_app.return_value = MagicMock()
        
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_bytes.side_effect = Exception("Download failed")
        mock_bucket.blob.return_value = mock_blob
        mock_storage.bucket.return_value = mock_bucket
        
        storage = Storage()
        
        with pytest.raises(Exception, match="Download failed"):
            storage.retrieve_base_text(sample_expression_id, sample_manifestation_id)

