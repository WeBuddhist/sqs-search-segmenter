from app.identifier import generate_id


class Queries:
    @staticmethod
    def primary_nomen(label, relationship):
        return f"""
        ({label})-[:{relationship}]->({label}_n:Nomen)-[:HAS_LOCALIZATION]->
        ({label}_lt:LocalizedText)-[:HAS_LANGUAGE]->({label}_l:Language) | {{
            language: {label}_l.code,
            text: {label}_lt.text
        }}
    """

    @staticmethod
    def alternative_nomen(label, relationship):
        return f"""
        ({label})-[:{relationship}]->(:Nomen)<-[:ALTERNATIVE_OF]-({label}_an:Nomen) | [
            ({label}_an)-[:HAS_LOCALIZATION]->({label}_at:LocalizedText)-[:HAS_LANGUAGE]->({label}_al:Language) | {{
                language: {label}_al.code,
                text: {label}_at.text
            }}
        ]
    """

    @staticmethod
    def direct_localized_text(label, relationship):
        return f"""
        ({label})-[:{relationship}]->({label}_lt:LocalizedText)-[:HAS_LANGUAGE]->({label}_l:Language) | {{
            language: {label}_l.code,
            text: {label}_lt.text
        }}
    """

    @staticmethod
    def get_expression_type(label):
        return f"""
        CASE
            WHEN {label}.type = 'translation' THEN 'translation'
            WHEN {label}.type = 'commentary' THEN 'commentary'
            WHEN {label}.type = 'root' THEN 'root'
            ELSE 'none'
        END
    """

    @staticmethod
    def get_category_fragment(label):
        return f"""
        [({label})-[:EXPRESSION_OF]->(ef_work:Work)-[:BELONGS_TO]->(ef_cat:Category) | [
            {Queries.direct_localized_text('ef_cat', 'HAS_TITLE')}
        ]][0
    """

    @staticmethod
    def expression_fragment(label):
        return f"""
{{
    id: {label}.id,
    contributors: (
        [({label})-[:HAS_CONTRIBUTION]->(ef_contrib:Contribution)-[:BY]->(ef_person:Person) | {{
            person_id: ef_person.id,
            person_bdrc_id: ef_person.bdrc,
            role: [(ef_contrib)-[:WITH_ROLE]->(ef_role:RoleType) | ef_role.name][0]
        }}]
        +
        [({label})-[:HAS_CONTRIBUTION]->(ef_contrib:Contribution)-[:BY]->(ef_ai:AI) | {{
            ai_id: ef_ai.id,
            role: [(ef_contrib)-[:WITH_ROLE]->(ef_role:RoleType) | ef_role.name][0]
        }}]
    ),
    date: {label}.date,
    title: [{Queries.primary_nomen(label, 'HAS_TITLE')}],
    alt_titles: [{Queries.alternative_nomen(label, 'HAS_TITLE')}],
    language: [({label})-[:HAS_LANGUAGE]->(ef_lang:Language) | ef_lang.code][0],
    category_id: {Queries.get_category_fragment(label)},
    copyright: [({label})-[:HAS_COPYRIGHT]->(ef_copyright:Copyright) | ef_copyright.name][0],
    license: [({label})-[:HAS_LICENSE]->(ef_license:License) | ef_license.name][0]
}}
"""


Queries.manifestations = {
    "get_expression_id_by_manifestation_id": f"""
MATCH (e:Expression)<-[:MANIFESTATION_OF]-(m:Manifestation {{id: $manifestation_id}})-[:HAS_TYPE]->(:ManifestationType {{name: 'critical'}})
RETURN e.id as expression_id,
       [{Queries.primary_nomen('e', 'HAS_TITLE')}] as title,
       [(e)-[:HAS_LANGUAGE]->(lang:Language) | lang.code][0] as language
"""
}


Queries.segments = {
    "create_search_segmentation_annotation": """
MATCH (m:Manifestation {id: $manifestation_id})
MERGE (ann:Annotation {id: $annotation_id})
MATCH (ann_type:AnnotationType {name: 'search_segmentation'})
MERGE (ann)-[:HAS_TYPE]->(ann_type)
MERGE (ann)-[:ANNOTATION_OF]->(m)
WITH ann, m
UNWIND $segments AS segment_data
MERGE (seg:Segment {id: segment_data.segment_id})
SET seg.span_start = segment_data.span_start,
    seg.span_end = segment_data.span_end
MERGE (seg)-[:SEGMENTATION_OF]->(ann)
RETURN seg.id as segment_id
""",
    "check_if_search_segments_exist": """
OPTIONAL MATCH (m:Manifestation {id: $manifestation_id})<-[:ANNOTATION_OF]-(ann:Annotation)-[:HAS_TYPE]->(:AnnotationType {name: 'search_segmentation'})
RETURN CASE WHEN ann IS NOT NULL THEN true ELSE false END as exists
""",
    "get_search_segments": """
MATCH (m:Manifestation {id: $manifestation_id})<-[:ANNOTATION_OF]-(ann:Annotation)-[:HAS_TYPE]->(:AnnotationType {name: 'search_segmentation'})
MATCH (seg:Segment)-[:SEGMENTATION_OF]->(ann)
RETURN seg.id as segment_id,
       seg.span_start as span_start,
       seg.span_end as span_end
ORDER BY seg.span_start
""",
    "get_overlapping_segments_by_search_segments_id_grouped": """
UNWIND $segment_ids AS input_segment_id
MATCH (input_seg:Segment {id: input_segment_id})-[:SEGMENTATION_OF]->(input_ann:Annotation)-[:ANNOTATION_OF]->(m:Manifestation)
MATCH (seg_ann:Annotation)-[:HAS_TYPE]->(:AnnotationType {name: 'segmentation'})
MATCH (seg_ann)-[:ANNOTATION_OF]->(m)
MATCH (seg:Segment)-[:SEGMENTATION_OF]->(seg_ann)
WHERE seg.span_start < input_seg.span_end 
  AND seg.span_end > input_seg.span_start
WITH input_segment_id,
     input_seg.span_start as input_span_start,
     input_seg.span_end as input_span_end,
     collect({
       segment_id: seg.id,
       span_start: seg.span_start,
       span_end: seg.span_end
     }) as overlapping_segments
RETURN input_segment_id,
       input_span_start,
       input_span_end,
       overlapping_segments
ORDER BY input_segment_id
""",
}