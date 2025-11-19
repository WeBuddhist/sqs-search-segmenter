"""
Tests for neo4j_queries.py - Neo4j query builders and templates.
"""
import pytest
from app.neo4j_queries import Queries


class TestQueries:
    """Test suite for Queries class."""
    
    def test_primary_nomen_query(self):
        """Test primary_nomen query builder."""
        result = Queries.primary_nomen("e", "HAS_TITLE")
        
        assert "(e)-[:HAS_TITLE]->(e_n:Nomen)" in result
        assert "e_lt:LocalizedText" in result
        assert "e_l:Language" in result
        assert "language: e_l.code" in result
        assert "text: e_lt.text" in result
    
    def test_alternative_nomen_query(self):
        """Test alternative_nomen query builder."""
        result = Queries.alternative_nomen("e", "HAS_TITLE")
        
        assert "(e)-[:HAS_TITLE]->(:Nomen)<-[:ALTERNATIVE_OF]-(e_an:Nomen)" in result
        assert "e_at:LocalizedText" in result
        assert "e_al:Language" in result
    
    def test_direct_localized_text_query(self):
        """Test direct_localized_text query builder."""
        result = Queries.direct_localized_text("cat", "HAS_TITLE")
        
        assert "(cat)-[:HAS_TITLE]->(cat_lt:LocalizedText)" in result
        assert "cat_l:Language" in result
        assert "language: cat_l.code" in result
        assert "text: cat_lt.text" in result
    
    def test_get_expression_type_query(self):
        """Test get_expression_type query builder."""
        result = Queries.get_expression_type("e")
        
        assert "CASE" in result
        assert "e.type = 'translation'" in result
        assert "e.type = 'commentary'" in result
        assert "e.type = 'root'" in result
        assert "ELSE 'none'" in result
    
    def test_get_category_fragment_query(self):
        """Test get_category_fragment query builder."""
        result = Queries.get_category_fragment("e")
        
        assert "(e)-[:EXPRESSION_OF]->(ef_work:Work)" in result
        assert "ef_cat:Category" in result
        assert "HAS_TITLE" in result
    
    def test_expression_fragment_query(self):
        """Test expression_fragment query builder."""
        result = Queries.expression_fragment("e")
        
        assert "id: e.id" in result
        assert "contributors:" in result
        assert "HAS_CONTRIBUTION" in result
        assert "Person" in result
        assert "AI" in result
        assert "date: e.date" in result
        assert "language:" in result
        assert "copyright:" in result
        assert "license:" in result
    
    def test_manifestations_queries(self):
        """Test manifestations query dictionary."""
        query = Queries.manifestations["get_expression_id_by_manifestation_id"]
        
        assert "MATCH" in query
        assert "Expression" in query
        assert "Manifestation" in query
        assert "$manifestation_id" in query
        assert "ManifestationType {name: 'critical'}" in query
        assert "RETURN" in query
        assert "expression_id" in query
        assert "title" in query
        assert "language" in query
    
    def test_segments_create_search_segmentation_annotation_query(self):
        """Test create_search_segmentation_annotation query."""
        query = Queries.segments["create_search_segmentation_annotation"]
        
        assert "MATCH (m:Manifestation {id: $manifestation_id})" in query
        assert "MERGE (ann:Annotation {id: $annotation_id})" in query
        assert "MERGE (ann_type:AnnotationType {name: 'search_segmentation'})" in query
        assert "UNWIND $segments AS segment_data" in query
        assert "MERGE (seg:Segment {id: segment_data.segment_id})" in query
        assert "SET seg.span_start = segment_data.span_start" in query
        assert "SET seg.span_end = segment_data.span_end" in query or "seg.span_end = segment_data.span_end" in query
        assert "RETURN" in query
    
    def test_segments_check_if_search_segments_exist_query(self):
        """Test check_if_search_segments_exist query."""
        query = Queries.segments["check_if_search_segments_exist"]
        
        assert "OPTIONAL MATCH" in query
        assert "Manifestation {id: $manifestation_id}" in query
        assert "AnnotationType {name: 'search_segmentation'}" in query
        assert "RETURN" in query
        assert "CASE WHEN" in query
        assert "exists" in query
    
    def test_segments_get_search_segments_query(self):
        """Test get_search_segments query."""
        query = Queries.segments["get_search_segments"]
        
        assert "MATCH" in query
        assert "Manifestation {id: $manifestation_id}" in query
        assert "AnnotationType {name: 'search_segmentation'}" in query
        assert "Segment" in query
        assert "RETURN" in query
        assert "segment_id" in query
        assert "span_start" in query
        assert "span_end" in query
        assert "ORDER BY seg.span_start" in query
    
    def test_segments_get_overlapping_segments_query(self):
        """Test get_overlapping_segments_by_search_segments_id_grouped query."""
        query = Queries.segments["get_overlapping_segments_by_search_segments_id_grouped"]
        
        assert "UNWIND $segment_ids AS input_segment_id" in query
        assert "MATCH (input_seg:Segment {id: input_segment_id})" in query
        assert "AnnotationType {name: 'segmentation'}" in query
        assert "seg.span_start < input_seg.span_end" in query
        assert "seg.span_end > input_seg.span_start" in query
        assert "collect({" in query
        assert "overlapping_segments" in query
        assert "ORDER BY input_segment_id" in query
    
    def test_segments_get_search_segmentation_segments_query(self):
        """Test get_search_segmentation_segments query."""
        query = Queries.segments["get_search_segmentation_segments"]
        
        assert "MATCH" in query
        assert "Manifestation {id: $manifestation_id}" in query
        assert "AnnotationType {name: 'search_segmentation'}" in query
        assert "Segment" in query
        assert "RETURN" in query
        assert "segment_id" in query
    
    def test_queries_have_all_expected_keys(self):
        """Test that all expected query keys exist."""
        expected_manifestation_keys = ["get_expression_id_by_manifestation_id"]
        expected_segment_keys = [
            "create_search_segmentation_annotation",
            "check_if_search_segments_exist",
            "get_search_segments",
            "get_overlapping_segments_by_search_segments_id_grouped",
            "get_search_segmentation_segments"
        ]
        
        for key in expected_manifestation_keys:
            assert key in Queries.manifestations
            assert isinstance(Queries.manifestations[key], str)
            assert len(Queries.manifestations[key]) > 0
        
        for key in expected_segment_keys:
            assert key in Queries.segments
            assert isinstance(Queries.segments[key], str)
            assert len(Queries.segments[key]) > 0

