"""
Tests for config.py - Configuration management.
"""
import pytest
import os
from unittest.mock import patch


class TestConfig:
    """Test suite for configuration management."""
    
    def test_get_env_var_dev_environment(self, monkeypatch):
        """Test environment variable retrieval in dev environment."""
        monkeypatch.setenv("ENVIRONMENT", "dev")
        monkeypatch.setenv("DEV_NEO4J_URI", "bolt://localhost:7687")
        
        # Reimport to pick up new env vars
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["NEO4J_URI"] == "bolt://localhost:7687"
    
    def test_get_env_var_prod_environment(self, monkeypatch):
        """Test environment variable retrieval in prod environment."""
        monkeypatch.setenv("ENVIRONMENT", "prod")
        monkeypatch.setenv("PROD_NEO4J_URI", "bolt://prod-server:7687")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["NEO4J_URI"] == "bolt://prod-server:7687"
    
    def test_get_env_var_test_environment(self, monkeypatch):
        """Test environment variable retrieval in test environment."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("TEST_NEO4J_URI", "bolt://test-server:7687")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["NEO4J_URI"] == "bolt://test-server:7687"
    
    def test_get_function(self, monkeypatch):
        """Test the get() function."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("TEST_NEO4J_URI", "bolt://localhost:7687")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        result = config_module.get("NEO4J_URI")
        assert result == "bolt://localhost:7687"
    
    def test_get_function_with_default(self, monkeypatch):
        """Test get() function with default value."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        result = config_module.get("NONEXISTENT_KEY", "default_value")
        assert result == "default_value"
    
    def test_gemini_api_key_no_prefix(self, monkeypatch):
        """Test that GEMINI_API_KEY doesn't use environment prefix."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key_123")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["GEMINI_API_KEY"] == "test_gemini_key_123"
    
    def test_log_level_default(self, monkeypatch):
        """Test LOG_LEVEL default value."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["LOG_LEVEL"] == "INFO"
    
    def test_log_level_custom(self, monkeypatch):
        """Test custom LOG_LEVEL value."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.Config["LOG_LEVEL"] == "DEBUG"
    
    def test_environment_default(self, monkeypatch):
        """Test default environment is 'dev'."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        
        import importlib
        import app.config as config_module
        importlib.reload(config_module)
        
        assert config_module.ENVIRONMENT == "dev"
    
    def test_all_config_keys_exist(self, monkeypatch):
        """Test that all expected config keys are defined."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        
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

