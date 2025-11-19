"""
Tests for identifier.py - ID generation utilities.
"""
import pytest
from app.identifier import generate_id


class TestGenerateId:
    """Test suite for generate_id function."""
    
    def test_generate_id_default_length(self):
        """Test that generate_id creates an ID with default length 21."""
        id_str = generate_id()
        assert len(id_str) == 21
    
    def test_generate_id_custom_length(self):
        """Test that generate_id respects custom length parameter."""
        lengths = [10, 15, 30, 50]
        for length in lengths:
            id_str = generate_id(size=length)
            assert len(id_str) == length
    
    def test_generate_id_characters(self):
        """Test that generated IDs only contain valid characters."""
        valid_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        id_str = generate_id(size=100)
        
        for char in id_str:
            assert char in valid_chars
    
    def test_generate_id_uniqueness(self):
        """Test that generate_id produces unique IDs."""
        ids = [generate_id() for _ in range(1000)]
        # Check that all IDs are unique
        assert len(ids) == len(set(ids))
    
    def test_generate_id_zero_length(self):
        """Test generate_id with zero length."""
        id_str = generate_id(size=0)
        assert len(id_str) == 0
        assert id_str == ""
    
    def test_generate_id_large_length(self):
        """Test generate_id with large length."""
        id_str = generate_id(size=1000)
        assert len(id_str) == 1000

