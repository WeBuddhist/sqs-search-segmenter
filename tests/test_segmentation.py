"""
Tests for segmentation.py - Text segmentation business logic.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.segmentation import get_search_segmentation, get_segments_with_content


class TestGetSearchSegmentation:
    """Test suite for get_search_segmentation function."""
    
    def test_get_search_segmentation_success(self, mock_segment_text, sample_base_text):
        """Test successful segmentation of text."""
        result = get_search_segmentation(sample_base_text, "bo")
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert all("span" in segment for segment in result)
        mock_segment_text.assert_called_once_with(sample_base_text, "bo")
    
    def test_get_search_segmentation_empty_text(self, mock_segment_text):
        """Test segmentation with empty text."""
        mock_segment_text.return_value = ([], "")
        result = get_search_segmentation("", "bo")
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_search_segmentation_different_languages(self, mock_segment_text, sample_base_text):
        """Test segmentation with different language codes."""
        languages = ["bo", "en", "zh"]
        
        for lang in languages:
            result = get_search_segmentation(sample_base_text, lang)
            assert isinstance(result, list)
    
    def test_get_search_segmentation_exception(self, mock_segment_text, sample_base_text):
        """Test that exceptions are properly raised."""
        mock_segment_text.side_effect = Exception("Segmentation failed")
        
        with pytest.raises(RuntimeError) as exc_info:
            get_search_segmentation(sample_base_text, "bo")
        
        assert "Segmentation failed" in str(exc_info.value)


class TestGetSegmentsWithContent:
    """Test suite for get_segments_with_content function."""
    
    def test_get_segments_with_content_success(self, sample_overlapping_segments, sample_base_text):
        """Test successful extraction of segment content."""
        result = get_segments_with_content(sample_overlapping_segments, sample_base_text)
        
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Check first segment
        first_segment = result[0]
        assert "segment_id" in first_segment
        assert "segment_content" in first_segment
        assert "segments" in first_segment
        assert first_segment["segment_id"] == "search_seg_001"
        assert first_segment["segment_content"] == sample_base_text[0:15]
        assert len(first_segment["segments"]) == 2
    
    def test_get_segments_with_content_overlapping(self, sample_overlapping_segments, sample_base_text):
        """Test that overlapping segments are correctly extracted."""
        result = get_segments_with_content(sample_overlapping_segments, sample_base_text)
        
        first_segment = result[0]
        overlapping = first_segment["segments"]
        
        assert len(overlapping) == 2
        assert overlapping[0]["segment_id"] == "overlap_001"
        assert overlapping[0]["segment_content"] == sample_base_text[0:10]
        assert overlapping[1]["segment_id"] == "overlap_002"
        assert overlapping[1]["segment_content"] == sample_base_text[10:15]
    
    def test_get_segments_with_content_empty_segments(self, sample_base_text):
        """Test with empty segments list."""
        result = get_segments_with_content([], sample_base_text)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_segments_with_content_out_of_bounds(self, sample_base_text):
        """Test handling of out-of-bounds spans."""
        segments = [
            {
                "input_segment_id": "seg_001",
                "input_span_start": 0,
                "input_span_end": 1000,  # Out of bounds
                "overlapping_segments": []
            }
        ]
        
        result = get_segments_with_content(segments, sample_base_text)
        
        # Out-of-bounds segment should be skipped
        assert len(result) == 0
    
    def test_get_segments_with_content_overlapping_out_of_bounds(self, sample_base_text):
        """Test handling of out-of-bounds overlapping segments."""
        segments = [
            {
                "input_segment_id": "seg_001",
                "input_span_start": 0,
                "input_span_end": 15,
                "overlapping_segments": [
                    {"segment_id": "overlap_001", "span_start": 0, "span_end": 10},
                    {"segment_id": "overlap_002", "span_start": 100, "span_end": 200}  # Out of bounds
                ]
            }
        ]
        
        result = get_segments_with_content(segments, sample_base_text)
        
        assert len(result) == 1
        # Only the valid overlapping segment should be included
        assert len(result[0]["segments"]) == 1
        assert result[0]["segments"][0]["segment_id"] == "overlap_001"
    
    def test_get_segments_with_content_no_overlapping(self, sample_base_text):
        """Test segments with no overlapping segments."""
        segments = [
            {
                "input_segment_id": "seg_001",
                "input_span_start": 0,
                "input_span_end": 15,
                "overlapping_segments": []
            }
        ]
        
        result = get_segments_with_content(segments, sample_base_text)
        
        assert len(result) == 1
        assert result[0]["segment_id"] == "seg_001"
        assert result[0]["segments"] == []
    
    def test_get_segments_with_content_exception_propagation(self):
        """Test that exceptions are properly propagated."""
        segments = [{"invalid": "data"}]  # Missing required keys
        
        with pytest.raises(Exception):
            get_segments_with_content(segments, "test text")

