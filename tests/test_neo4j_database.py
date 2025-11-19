"""
Tests for neo4j_database.py - Neo4j database operations.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock

from app.neo4j_database import Neo4JDatabase, get_neo4j_driver


class TestNeo4JDatabase:
    """Test suite for Neo4JDatabase class."""
    
    @patch('app.neo4j_database.GraphDatabase')
    @patch('app.neo4j_database.Config')
    def test_neo4j_database_initialization_with_singleton(self, mock_config, mock_graph_db):
        """Test Neo4JDatabase initialization using singleton driver."""
        mock_config.get.side_effect = lambda key, default=None: {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password"
        }.get(key, default)
        
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db.driver.return_value = mock_driver
        
        # Reset global driver
        import app.neo4j_database as neo4j_module
        neo4j_module._neo4j_driver = None
        
        db = Neo4JDatabase()
        assert db is not None
    
    @patch('app.neo4j_database.GraphDatabase')
    def test_neo4j_database_initialization_with_custom_credentials(self, mock_graph_db):
        """Test Neo4JDatabase initialization with custom credentials."""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        db = Neo4JDatabase(
            neo4j_uri="bolt://custom:7687",
            neo4j_auth=("custom_user", "custom_pass")
        )
        
        mock_graph_db.driver.assert_called_with(
            "bolt://custom:7687",
            auth=("custom_user", "custom_pass")
        )
    
    @patch('app.neo4j_database.GraphDatabase')
    @patch('app.neo4j_database.Config')
    def test_get_expression_id_by_manifestation_id_success(
        self, mock_config, mock_graph_db, sample_manifestation_id
    ):
        """Test successful retrieval of expression ID."""
        mock_config.get.side_effect = lambda key, default=None: {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password"
        }.get(key, default)
        
        # Mock the transaction result that returns from tx.run().single()
        mock_tx_result = MagicMock()
        mock_record = {
            "expression_id": "expr_123",
            "title": [{"language": "bo", "text": "Test Title"}],
            "language": "bo"
        }
        mock_tx_result.single.return_value = mock_record
        
        # Mock session
        mock_session = MagicMock()
        mock_session.execute_read.return_value = mock_record
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        
        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db.driver.return_value = mock_driver
        
        # Reset global driver
        import app.neo4j_database as neo4j_module
        neo4j_module._neo4j_driver = None
        
        expression_id, title, language = Neo4JDatabase.get_expression_id_by_manifestation_id(
            sample_manifestation_id
        )
        
        assert expression_id == "expr_123"
        assert title == [{"language": "bo", "text": "Test Title"}]
        assert language == "bo"
    
    @patch('app.neo4j_database.GraphDatabase')
    @patch('app.neo4j_database.Config')
    def test_get_expression_id_by_manifestation_id_not_found(
        self, mock_config, mock_graph_db, sample_manifestation_id
    ):
        """Test handling when manifestation is not found."""
        mock_config.get.side_effect = lambda key, default=None: {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password"
        }.get(key, default)
        
        # The function wraps exceptions in RuntimeError
        mock_session = MagicMock()
        
        # Make execute_read raise an exception
        def raise_error(func):
            raise Exception("Not found")
        
        mock_session.execute_read.side_effect = raise_error
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        
        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db.driver.return_value = mock_driver
        
        # Reset global driver
        import app.neo4j_database as neo4j_module
        neo4j_module._neo4j_driver = None
        
        with pytest.raises(RuntimeError):
            Neo4JDatabase.get_expression_id_by_manifestation_id(sample_manifestation_id)
    
    @patch('app.neo4j_database.GraphDatabase')
    @patch('app.neo4j_database.Config')
    def test_get_overlapping_segments_success(
        self, mock_config, mock_graph_db, sample_search_segments
    ):
        """Test successful retrieval of overlapping segments."""
        mock_config.get.side_effect = lambda key, default=None: {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password"
        }.get(key, default)
        
        mock_result = [
            {
                "input_segment_id": "search_seg_001",
                "input_span_start": 0,
                "input_span_end": 15,
                "overlapping_segments": [
                    {"segment_id": "overlap_001", "span_start": 0, "span_end": 10}
                ]
            }
        ]
        
        mock_session = MagicMock()
        mock_session.execute_read.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        
        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db.driver.return_value = mock_driver
        
        # Reset global driver
        import app.neo4j_database as neo4j_module
        neo4j_module._neo4j_driver = None
        
        result = Neo4JDatabase.get_overlapping_segments_by_search_segments_id(
            sample_search_segments
        )
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["input_segment_id"] == "search_seg_001"
    
    @patch('app.neo4j_database.generate_id')
    @patch('app.neo4j_database.GraphDatabase')
    @patch('app.neo4j_database.Config')
    def test_create_search_segments_success(
        self, mock_config, mock_graph_db, mock_generate_id,
        sample_segments, sample_manifestation_id
    ):
        """Test successful creation of search segments."""
        mock_config.get.side_effect = lambda key, default=None: {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password"
        }.get(key, default)
        
        mock_generate_id.side_effect = lambda: f"seg_{mock_generate_id.call_count}"
        
        mock_session = MagicMock()
        mock_result = [{"segment_id": "seg_1"}]
        mock_session.execute_write.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        
        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver
        
        # Reset global driver
        import app.neo4j_database as neo4j_module
        neo4j_module._neo4j_driver = None
        
        db = Neo4JDatabase()
        result = db.create_search_segments(sample_segments, sample_manifestation_id)
        
        assert result is not None
    
    @patch('app.neo4j_database.GraphDatabase')
    @patch('app.neo4j_database.Config')
    def test_check_if_search_segments_exist_true(
        self, mock_config, mock_graph_db, sample_manifestation_id
    ):
        """Test checking if search segments exist (returns True)."""
        mock_config.get.side_effect = lambda key, default=None: {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password"
        }.get(key, default)
        
        # The execute_read should return the record that has .get("exists") method
        mock_record = {"exists": True}
        
        mock_session = MagicMock()
        mock_session.execute_read.return_value = mock_record
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        
        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db.driver.return_value = mock_driver
        
        # Reset global driver
        import app.neo4j_database as neo4j_module
        neo4j_module._neo4j_driver = None
        
        db = Neo4JDatabase()
        result = db.check_if_search_segments_exist(sample_manifestation_id)
        
        assert result is True
    
    @patch('app.neo4j_database.GraphDatabase')
    @patch('app.neo4j_database.Config')
    def test_check_if_search_segments_exist_false(
        self, mock_config, mock_graph_db, sample_manifestation_id
    ):
        """Test checking if search segments exist (returns False)."""
        mock_config.get.side_effect = lambda key, default=None: {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password"
        }.get(key, default)
        
        # The execute_read should return the record that has .get("exists") method
        mock_record = {"exists": False}
        
        mock_session = MagicMock()
        mock_session.execute_read.return_value = mock_record
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        
        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db.driver.return_value = mock_driver
        
        # Reset global driver
        import app.neo4j_database as neo4j_module
        neo4j_module._neo4j_driver = None
        
        db = Neo4JDatabase()
        result = db.check_if_search_segments_exist(sample_manifestation_id)
        
        assert result is False
    
    @patch('app.neo4j_database.GraphDatabase')
    @patch('app.neo4j_database.Config')
    def test_get_search_segments_success(
        self, mock_config, mock_graph_db, sample_manifestation_id
    ):
        """Test successful retrieval of search segments."""
        mock_config.get.side_effect = lambda key, default=None: {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password"
        }.get(key, default)
        
        mock_result = [
            {"segment_id": "seg_001", "span_start": 0, "span_end": 15},
            {"segment_id": "seg_002", "span_start": 16, "span_end": 35}
        ]
        
        mock_session = MagicMock()
        mock_session.execute_read.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        
        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db.driver.return_value = mock_driver
        
        # Reset global driver
        import app.neo4j_database as neo4j_module
        neo4j_module._neo4j_driver = None
        
        db = Neo4JDatabase()
        result = db.get_search_segments(sample_manifestation_id)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["segment_id"] == "seg_001"

