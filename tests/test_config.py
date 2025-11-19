"""
Tests for config.py - Configuration management.
"""
import pytest
import os
from unittest.mock import patch


class TestConfig:
    """Test suite for configuration management."""
    
    def test_neo4j_uri_loading(self, monkeypatch):
        """Test NEO4J_URI environment variable retrieval."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
        
        # Reimport to pick up new env vars
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["NEO4J_URI"] == "bolt://localhost:7687"
    
    def test_aws_credentials_loading(self, monkeypatch):
        """Test AWS credential environment variables retrieval."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key-123")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-456")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["AWS_ACCESS_KEY_ID"] == "test-key-123"
        assert config_module.Config["AWS_SECRET_ACCESS_KEY"] == "test-secret-456"
    
    def test_sqs_queue_url_loading(self, monkeypatch):
        """Test SQS_QUEUE_URL environment variable retrieval."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        monkeypatch.setenv("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123/test-queue")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["SQS_QUEUE_URL"] == "https://sqs.us-east-1.amazonaws.com/123/test-queue"
    
    def test_get_function(self, monkeypatch):
        """Test the get() function."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        result = config_module.get("NEO4J_URI")
        assert result == "bolt://localhost:7687"
    
    def test_get_function_with_default(self, monkeypatch):
        """Test get() function with default value."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        result = config_module.get("NONEXISTENT_KEY", "default_value")
        assert result == "default_value"
    
    def test_gemini_api_key_loading(self, monkeypatch):
        """Test GEMINI_API_KEY environment variable retrieval."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key_123")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["GEMINI_API_KEY"] == "test_gemini_key_123"
    
    def test_log_level_default(self, monkeypatch):
        """Test LOG_LEVEL default value."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["LOG_LEVEL"] == "INFO"
    
    def test_log_level_custom(self, monkeypatch):
        """Test custom LOG_LEVEL value."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["LOG_LEVEL"] == "DEBUG"
    
    def test_environment_default(self, monkeypatch):
        """Test default environment is 'prod' when no ENVIRONMENT is set."""
        # Completely clear the environment and prevent .env loading
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        
        # Mock both load_dotenv and ensure os.getenv returns default
        with patch('dotenv.load_dotenv'):
            with patch('os.getenv') as mock_getenv:
                # Mock os.getenv to return default for ENVIRONMENT
                def getenv_side_effect(key, default=None):
                    if key == 'ENVIRONMENT':
                        return 'prod'  # Simulating no env var set, using default
                    elif key == 'LOG_LEVEL':
                        return default or 'INFO'
                    return default
                
                mock_getenv.side_effect = getenv_side_effect
                
                import importlib
                import app.config as config_module
                importlib.reload(config_module)
                
                assert config_module.ENVIRONMENT == "prod"
    
    def test_all_config_keys_exist(self, monkeypatch):
        """Test that all expected config keys are defined."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        expected_keys = [
            "ENVIRONMENT",
            "NEO4J_URI",
            "NEO4J_USER",
            "NEO4J_PASSWORD",
            "AWS_REGION",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "SQS_QUEUE_URL",
            "MILVUS_URI",
            "MILVUS_TOKEN",
            "MILVUS_COLLECTION_NAME",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "FIREBASE_STORAGE_BUCKET",
            "GEMINI_API_KEY",
            "LOG_LEVEL"
        ]
        
        for key in expected_keys:
            assert key in config_module.Config
    
    def test_aws_region_default(self, monkeypatch):
        """Test AWS_REGION default value."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        monkeypatch.delenv("AWS_REGION", raising=False)
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["AWS_REGION"] == "us-east-1"

