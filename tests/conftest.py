"""
Pytest configuration and shared fixtures.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import os


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for testing."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value = session
    driver.verify_connectivity.return_value = None
    return driver


@pytest.fixture
def mock_firebase_storage():
    """Mock Firebase storage for testing."""
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    return mock_bucket, mock_blob


@pytest.fixture
def mock_milvus_client():
    """Mock Milvus client for testing."""
    client = MagicMock()
    client.insert.return_value = None
    return client


@pytest.fixture
def sample_manifestation_id():
    """Sample manifestation ID for testing."""
    return "test_manifestation_123"


@pytest.fixture
def sample_expression_id():
    """Sample expression ID for testing."""
    return "test_expression_456"


@pytest.fixture
def sample_base_text():
    """Sample Tibetan text for testing."""
    return "བཀྲ་ཤིས་བདེ་ལེགས། ང་ནི་སློབ་གྲྭ་བ་ཞིག་ཡིན། དགོང་མོ་བདེ་ལེགས།"


@pytest.fixture
def sample_segments():
    """Sample segmentation result for testing."""
    return [
        {
            "span": {"start": 0, "end": 15},
            "segment_id": "seg_001"
        },
        {
            "span": {"start": 16, "end": 35},
            "segment_id": "seg_002"
        },
        {
            "span": {"start": 36, "end": 52},
            "segment_id": "seg_003"
        }
    ]


@pytest.fixture
def sample_search_segments():
    """Sample search segments from Neo4j."""
    return [
        {
            "segment_id": "search_seg_001",
            "span_start": 0,
            "span_end": 15
        },
        {
            "segment_id": "search_seg_002",
            "span_start": 16,
            "span_end": 35
        }
    ]


@pytest.fixture
def sample_overlapping_segments():
    """Sample overlapping segments mapping."""
    return [
        {
            "input_segment_id": "search_seg_001",
            "input_span_start": 0,
            "input_span_end": 15,
            "overlapping_segments": [
                {"segment_id": "overlap_001", "span_start": 0, "span_end": 10},
                {"segment_id": "overlap_002", "span_start": 10, "span_end": 15}
            ]
        },
        {
            "input_segment_id": "search_seg_002",
            "input_span_start": 16,
            "input_span_end": 35,
            "overlapping_segments": [
                {"segment_id": "overlap_003", "span_start": 16, "span_end": 25},
                {"segment_id": "overlap_004", "span_start": 25, "span_end": 35}
            ]
        }
    ]


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    env_vars = {
        "ENVIRONMENT": "test",
        "TEST_NEO4J_URI": "bolt://localhost:7687",
        "TEST_NEO4J_USER": "neo4j",
        "TEST_NEO4J_PASSWORD": "test_password",
        "TEST_AWS_REGION": "us-east-1",
        "TEST_SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue",
        "TEST_MILVUS_URI": "http://localhost:19530",
        "TEST_MILVUS_TOKEN": "test_token",
        "TEST_MILVUS_COLLECTION_NAME": "test_collection",
        "TEST_GOOGLE_APPLICATION_CREDENTIALS": "/path/to/credentials.json",
        "TEST_FIREBASE_STORAGE_BUCKET": "test-bucket.appspot.com",
        "GEMINI_API_KEY": "test_gemini_key",
        "LOG_LEVEL": "DEBUG"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def mock_segment_text():
    """Mock milvus_segment_generator.segment.segment_text function."""
    with patch('app.segmentation.segment_text') as mock:
        mock.return_value = (
            [
                {"span": {"start": 0, "end": 15}},
                {"span": {"start": 16, "end": 35}},
                {"span": {"start": 36, "end": 52}}
            ],
            "བཀྲ་ཤིས་བདེ་ལེགས། ང་ནི་སློབ་གྲྭ་བ་ཞིག་ཡིན། དགོང་མོ་བདེ་ལེགས།"
        )
        yield mock


@pytest.fixture
def mock_embed_texts_batch():
    """Mock BoEmbedder.gemini.embed_texts_batch function."""
    with patch('BoEmbedder.gemini.embed_texts_batch') as mock:
        mock.return_value = [[0.1] * 768]  # Mock 768-dimensional embedding
        yield mock

