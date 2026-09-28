"""Reviewed source assertions and indexed memberships for static research views."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from bisect import bisect_right
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo
from importlib.resources import files
import re
import html

import pycountry
import yaml
from pydantic import Field, model_validator, create_model

from . import __version__
from .metrics import MetricsExport
from .models import StrictModel, TextValue, DateValue
from .util import canonical_url, digest, read_json, stamp, uid, utcnow, write_json

SITE_VERSION = '1.5.0'


class Eligibility(StrictModel):
    rule: Literal['all_supporting_records_in_window'] = 'all_supporting_records_in_window'
    record_ids: list[str] = Field(min_length=1)
    partial: Literal['hide_relationship_keep_visible_assertions'] = 'hide_relationship_keep_visible_assertions'


def eligible(rule, records, since, until, basis='publication', knowledge_cutoff=None):
    """Reference implementation for the static site's generic date filtering."""
    rule=Eligibility.model_validate(rule) if isinstance(rule,dict) else rule
    date.fromisoformat(since);date.fromisoformat(until)
    if since>until or basis not in {'publication','capture'}:raise ValueError('Invalid reporting window')
    cutoff=stamp(knowledge_cutoff) if knowledge_cutoff else None
    return all(since<=records[i][basis][:10]<=until and
               (cutoff is None or (stamp(records[i]['capture'])<=cutoff and records[i]['publication'][:10]<=cutoff[:10]))
               for i in rule.record_ids)


class EvidenceInput(StrictModel):
    record_id: str
    claim_index: int | None = Field(default=None,ge=0)
    quote_index: int | None = Field(default=None,ge=0)
    quote: str | None = None
    section: str = Field(min_length=1)
    occurrence: int = Field(default=0,ge=0)

    @model_validator(mode='after')
    def reference(self):
        if self.quote_index is not None and self.claim_index is None:raise ValueError('Quote index requires a claim')
        if (self.quote_index is None)==(self.quote is None):raise ValueError('Use a quote index or a captured source span')
        return self


class EvidenceSpan(StrictModel):
    id: str
    document_id: str
    record_id: str
    claim_index: int | None
    quote_index: int | None
    section: str
    quote: str
    source_text_sha256: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    page: int | None
    quote_sha256: str
    offset_basis: Literal['unicode_code_points_half_open'] = 'unicode_code_points_half_open'


class Assertion(StrictModel):
    id: str
    record_id: str
    document_id: str
    claim_index: int
    kind: Literal['finding','measure','statement','date']
    text: str
    value: TextValue = Field(default_factory=lambda:TextValue(status='not_extracted'))
    measure_id: str | None = None
    observation_date: DateValue = Field(default_factory=lambda:DateValue(status='not_extracted'))
    evidence_ids: list[str] = Field(min_length=1)
    eligibility: Eligibility
    review_state: Literal['extracted_draft','source_checked_draft']
    quoted_authority_status: Literal['not_extracted'] = 'not_extracted'


class RevisionEdge(StrictModel):
    from_assertion_id: str
    to_assertion_id: str
    evidence_ids: list[str] = Field(min_length=1)


class Comparison(StrictModel):
    id: str
    kind: Literal['contradiction','correction','supersession','corroboration','republication','different_scope','unresolved_association']
    status: Literal['unresolved','documented']
    participant_ids: list[str] = Field(min_length=2)
    participant_labels: dict[str,str]
    reason: str = Field(min_length=12)
    scope_review: str = Field(min_length=12)
    evidence_ids: list[str] = Field(min_length=1)
    eligibility: Eligibility
    reviewed_at: str
    reviewed_by: str
    review_state: Literal['source_checked_draft']
    lineage: list[RevisionEdge] = Field(default_factory=list)
    independence: str | None = None

    @model_validator(mode='after')
    def semantics(self):
        stamp(self.reviewed_at)
        if len(set(self.participant_ids))!=len(self.participant_ids):raise ValueError('Distinct comparison participants required')
        if set(self.participant_labels)!=set(self.participant_ids) or any(not v.strip() for v in self.participant_labels.values()):raise ValueError('Each comparison participant requires its source section label')
        revision=self.kind in {'correction','supersession'}
        if revision!=bool(self.lineage):raise ValueError('Only explicit revisions carry lineage')
        if self.kind in {'contradiction','unresolved_association'} and self.status!='unresolved':raise ValueError('Unresolved comparisons retain their branches')
        if self.kind not in {'contradiction','unresolved_association'} and self.status!='documented':raise ValueError('Relationship status must describe the documented relationship')
        if self.kind=='corroboration' and not self.independence:raise ValueError('Corroboration requires an independence review')
        for edge in self.lineage:
            if edge.from_assertion_id==edge.to_assertion_id or not {edge.from_assertion_id,edge.to_assertion_id}<=set(self.participant_ids):raise ValueError('Revision endpoints must be distinct participants')
        return self


class AssertionInput(StrictModel):
    key: str
    record_id: str
    claim_index: int = Field(ge=0)
    kind: Literal['statement','date']
    text: str
    value: TextValue = Field(default_factory=TextValue)
    observation_date: DateValue = Field(default_factory=DateValue)
    evidence: list[EvidenceInput] = Field(min_length=1)


class ComparisonInput(StrictModel):
    key: str
    kind: str
    status: str
    participants: list[str] = Field(min_length=2)
    participant_labels: list[str] = Field(min_length=2)
    reason: str
    scope_review: str
    evidence: list[EvidenceInput] = Field(min_length=1)
    lineage: list[tuple[str,str]] = Field(default_factory=list)
    independence: str | None = None


class Organization(StrictModel):
    id: str
    name: str


class Channel(StrictModel):
    id: str
    name: str
    organization_id: str
    snapshot_source: str
    acquisition_source: str


class Area(StrictModel):
    code: str
    label: str
    code_system: Literal['ISO_3166_1_alpha_2'] = 'ISO_3166_1_alpha_2'
    meaning: Literal['reporting_location_identifier'] = 'reporting_location_identifier'

    @model_validator(mode='after')
    def code_valid(self):
        if pycountry.countries.get(alpha_2=self.code) is None:raise ValueError('Unknown geographic code')
        return self


class LocationInput(StrictModel):
    record_id: str
    claim_index: int | None = Field(default=None,ge=0)
    area_code: str
    role: Literal['occurrence','travel_origin','travel_destination','exposure','context','reporting_scope']
    evidence: list[EvidenceInput] = Field(min_length=1)
    reason: str


class LocationMembership(StrictModel):
    id: str
    record_id: str
    document_id: str
    claim_index: int | None
    area_code: str
    role: Literal['occurrence','travel_origin','travel_destination','exposure','context','reporting_scope']
    evidence_ids: list[str] = Field(min_length=1)
    reason: str
    review_state: Literal['source_checked_draft'] = 'source_checked_draft'
    eligibility: Eligibility


class PlaceInput(StrictModel):
    id: str
    label: str
    longitude: float = Field(ge=-180,le=180,allow_inf_nan=False)
    latitude: float = Field(ge=-90,le=90,allow_inf_nan=False)
    precision: str
    area_codes: list[str]
    topic_ids: list[str]


class Place(PlaceInput):
    record_ids: list[str]
    relationship_ids: list[str]
    location_membership_ids: list[str]
    geographic_review: Literal['source_reference_available','pending']
    appearance: Literal['any_member_record_or_eligible_relationship'] = 'any_member_record_or_eligible_relationship'


class DisplayGroup(StrictModel):
    id: str
    place_ids: list[str]
    longitude: float
    latitude: float
    meaning: Literal['coincident_reference_points'] = 'coincident_reference_points'


class EndpointInput(StrictModel):
    relationship_id: str
    from_place_id: str
    to_place_id: str


class Topic(StrictModel):
    id: str
    label: str
    kind: str
    disease_group: str | None
    place_ids: list[str]
    record_ids: list[str]


class SiteRecord(StrictModel):
    id: str
    document_id: str
    topic_id: str
    channel_id: str
    title: str
    publication: str
    publication_basis: str
    capture: str
    claim_indexes: list[int]
    assertion_ids: list[str]
    comparison_ids: list[str]
    location_membership_ids: list[str]
    geographic_review: Literal['source_checked_draft','pending']
    flagged_issue_review: Literal['reviewed','not_flagged']


class Document(StrictModel):
    id: str
    title: str
    url: str
    content_url: str
    publication: str
    publication_basis: str
    publication_precision: str
    capture: str
    channel_id: str
    record_ids: list[str]
    location_membership_ids: list[str]
    raw_sha256: str
    text_sha256: str
    authority_review: Literal['not_extracted'] = 'not_extracted'


class SourceRelation(StrictModel):
    id: str
    category: Literal['geographic_link','assessment','assessment_update']
    kind: str
    label: str
    from_label: str | None = None
    to_label: str | None = None
    from_place_id: str | None = None
    to_place_id: str | None = None
    directed: bool
    topic_ids: list[str]
    basis: str
    limit: str
    assertion_ids: list[str] = Field(min_length=1)
    eligibility: Eligibility
    parent_id: str | None = None
    metric_panel_id: str
    review_state: Literal['source_checked_draft'] = 'source_checked_draft'


class CoverageEdge(StrictModel):
    id: str
    channel_id: str
    topic_id: str
    document_ids: list[str]
    record_ids: list[str]
    meaning: Literal['reporting_coverage'] = 'reporting_coverage'


ChainKind = Literal['established_transmission', 'contact_exposure', 'travel_itinerary', 'reporting_sequence']


class ChainNodeDetails(StrictModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    entity_kind: Literal['person', 'case', 'case_group', 'contact_group', 'travel_stop', 'report']
    place_id: str | None
    location_note: str = Field(min_length=1)
    event_date: DateValue = Field(default_factory=DateValue)
    date_basis: Literal['onset', 'travel', 'observation', 'unknown']
    date_note: str = Field(min_length=1)
    membership_basis: str = Field(min_length=12)
    uncertainty: str = Field(min_length=1)


class ChainNodeInput(ChainNodeDetails):
    evidence: list[EvidenceInput] = Field(min_length=1)


class ChainSupport(StrictModel):
    record_ids: list[str] = Field(min_length=1)
    document_ids: list[str] = Field(min_length=1)
    assertion_ids: list[str]
    evidence_ids: list[str] = Field(min_length=1)
    eligibility: Eligibility


class ChainNode(ChainNodeDetails, ChainSupport):
    id: str
    topic_ids: list[str] = Field(min_length=1)
    coordinate_precision: str | None


class ChainEdgeDetails(StrictModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    kind: ChainKind
    directed: bool
    direction_basis: Literal['source_reported', 'reviewed_publication_order', 'not_reported']
    certainty: Literal['established_by_source', 'reported', 'uncertain']
    basis: str = Field(min_length=12)
    uncertainty: str = Field(min_length=1)

    @model_validator(mode='after')
    def semantics(self):
        if self.directed != (self.direction_basis != 'not_reported'):
            raise ValueError('Chain direction requires an explicit basis')
        if self.kind == 'established_transmission' and self.certainty != 'established_by_source':
            raise ValueError('Transmission chains require source-established transmission')
        if self.kind != 'established_transmission' and self.certainty == 'established_by_source':
            raise ValueError('Other chain types retain their reported or uncertain basis')
        if self.kind == 'reporting_sequence' and self.direction_basis != 'reviewed_publication_order':
            raise ValueError('Reporting sequences require reviewed publication order')
        if self.kind != 'reporting_sequence' and self.direction_basis == 'reviewed_publication_order':
            raise ValueError('Publication order does not establish epidemiological direction')
        if self.kind == 'travel_itinerary' and self.direction_basis != 'source_reported':
            raise ValueError('Travel itineraries require source-reported order')
        return self


class ChainEdgeInput(ChainEdgeDetails):
    from_node: str
    to_node: str
    evidence: list[EvidenceInput] = Field(min_length=1)


class ChainEdge(ChainEdgeDetails, ChainSupport):
    id: str
    from_node_id: str
    to_node_id: str


class ChainDescription(StrictModel):
    key: str = Field(min_length=1)
    kind: ChainKind
    label: str = Field(min_length=1)
    scope: str = Field(min_length=12)
    membership_review: str = Field(min_length=12)
    uncertainty: str = Field(min_length=1)
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)
    review_state: Literal['source_checked_draft'] = 'source_checked_draft'

    @model_validator(mode='after')
    def review_time(self):
        stamp(self.reviewed_at)
        return self


class ChainInput(ChainDescription):
    nodes: list[ChainNodeInput] = Field(min_length=2)
    edges: list[ChainEdgeInput] = Field(min_length=1)


class ReviewedChain(ChainDescription):
    id: str
    nodes: list[ChainNode] = Field(min_length=2)
    edges: list[ChainEdge] = Field(min_length=1)


class Disease(StrictModel):
    id: str = Field(pattern=r'^disease:[a-z0-9]+(?:-[a-z0-9]+)*$')
    label: str = Field(min_length=1)


class DiseaseReviewDetails(StrictModel):
    record_id: str
    kind: Literal['single_disease', 'multiple_diseases', 'not_disease_specific', 'unresolved']
    disease_ids: list[str]
    reason: str = Field(min_length=1)
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)
    review_status: Literal['source_checked_draft'] = 'source_checked_draft'

    @model_validator(mode='after')
    def partition(self):
        n = len(self.disease_ids)
        if n != len(set(self.disease_ids)):
            raise ValueError('Duplicate reviewed disease')
        if (self.kind == 'single_disease' and n != 1 or
            self.kind == 'multiple_diseases' and n < 2 or
            self.kind in {'not_disease_specific', 'unresolved'} and n):
            raise ValueError('Disease review kind and membership disagree')
        stamp(self.reviewed_at)
        return self


class DiseaseReviewInput(DiseaseReviewDetails):
    evidence: list[EvidenceInput] = Field(min_length=1)


class DiseaseReview(DiseaseReviewDetails):
    id: str
    evidence_ids: list[str] = Field(min_length=1)
    eligibility: Eligibility


class OneHealthDates(StrictModel):
    observation_date: DateValue
    period_start: DateValue
    period_end: DateValue
    date_basis: Literal['onset','diagnosis','sample_collection','test_result','notification','shipment','reporting_cutoff','unknown']
    period_label: TextValue
    date_note: str = Field(min_length=1)

    @model_validator(mode='after')
    def dates(self):
        if any(v.value for v in (self.observation_date, self.period_start, self.period_end)) and self.date_basis == 'unknown':
            raise ValueError('One Health observation date requires a basis')
        if self.period_start.value and self.period_end.value and self.period_start.value > self.period_end.value:
            raise ValueError('One Health period is reversed')
        return self


class OneHealthSampling(StrictModel):
    sample_unit: TextValue
    frame: TextValue
    collection_method: TextValue
    test_method: TextValue


class OneHealthReviewDetails(StrictModel):
    record_id: str
    outcome: Literal['reviewed','no_relevant_observation','partial','unresolved']
    scope: str = Field(min_length=1)
    reviewed_sections: list[str] = Field(min_length=1)
    reason: str = Field(min_length=1)
    pending_items: list[str]
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)
    review_state: Literal['source_checked_draft'] = 'source_checked_draft'

    @model_validator(mode='after')
    def review(self):
        stamp(self.reviewed_at)
        if self.outcome in {'partial','unresolved'} and not self.pending_items:
            raise ValueError('Incomplete One Health review requires pending work')
        return self


class OneHealthReviewInput(OneHealthReviewDetails):
    evidence: list[EvidenceInput] = Field(min_length=1)


class OneHealthReview(OneHealthReviewDetails):
    id: str
    evidence_ids: list[str] = Field(min_length=1)
    eligibility: Eligibility


class OneHealthNodeDetails(OneHealthDates):
    key: str = Field(min_length=1)
    record_id: str
    label: str = Field(min_length=1)
    domain: Literal['human','animal','environment','food','unknown']
    entity_kind: Literal['person','population','animal_group','sample','food_product','commodity_lot','environmental_setting']
    roles: list[Literal['host','reservoir','vector','exposed_population','exposure_source','food_vehicle','commodity','sampled_matrix','ecological_context']]
    scope: Literal['episode','surveillance','background']
    taxon: TextValue
    material: TextValue
    agent: TextValue
    agent_kind: Literal['pathogen','toxin','other','unknown']
    finding: Literal['infection_reported','illness_reported','agent_detected','agent_not_detected','exposure_reported','movement_reported','context','unresolved']
    sampling: OneHealthSampling
    place_ids: list[str]
    location_note: str = Field(min_length=1)
    uncertainty: str = Field(min_length=1)

    @model_validator(mode='after')
    def domains(self):
        if len(self.roles)!=len(set(self.roles)) or len(self.place_ids)!=len(set(self.place_ids)):
            raise ValueError('Duplicate One Health role or place')
        if 'vector' in self.roles and self.domain!='animal':raise ValueError('Vectors are animal observations')
        if {'host','reservoir'} & set(self.roles) and self.domain not in {'human','animal'}:
            raise ValueError('Host and reservoir roles require a host domain')
        if 'food_vehicle' in self.roles and self.domain!='food':raise ValueError('Food vehicle requires food domain')
        kinds={'person':{'human'},'animal_group':{'animal'},'food_product':{'food'},'environmental_setting':{'environment'}}
        if self.entity_kind in kinds and self.domain not in kinds[self.entity_kind]:raise ValueError('One Health entity domain differs')
        if self.finding=='infection_reported' and (self.domain not in {'human','animal'} or self.agent_kind!='pathogen'):
            raise ValueError('Infection requires a host and pathogen')
        return self


class OneHealthNodeInput(OneHealthNodeDetails):
    measure_keys: list[str]
    evidence: list[EvidenceInput] = Field(min_length=1)


class OneHealthNode(OneHealthNodeDetails, ChainSupport):
    id: str
    topic_ids: list[str] = Field(min_length=1)
    measure_ids: list[str]


class OneHealthNodeRef(StrictModel):
    record_id: str
    key: str


class OneHealthRelationDetails(OneHealthDates):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    kind: Literal['cross_species_transmission','exposure','commodity_movement','genomic_association','vector_involvement','environmental_association']
    basis: Literal['source_reported','source_hypothesis']
    evidence_types: list[Literal['epidemiological_investigation','human_testing','animal_testing','environmental_testing','food_testing','genomic_analysis','traceback','experimental_study','ecological_analysis','source_assessment']] = Field(min_length=1)
    directed: bool
    direction_basis: Literal['source_reported','not_reported']
    source_certainty: TextValue
    scope: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    uncertainty: str = Field(min_length=1)
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)
    review_state: Literal['source_checked_draft'] = 'source_checked_draft'

    @model_validator(mode='after')
    def semantics(self):
        stamp(self.reviewed_at)
        if self.directed != (self.direction_basis=='source_reported'):raise ValueError('One Health direction requires source support')
        if self.kind=='genomic_association' and (self.directed or 'genomic_analysis' not in self.evidence_types):
            raise ValueError('Genomic association is undirected and requires genomic evidence')
        if self.kind=='commodity_movement' and (not self.directed or 'traceback' not in self.evidence_types):
            raise ValueError('Commodity movement requires reviewed direction and tracing')
        if len(set(self.evidence_types))!=len(self.evidence_types):raise ValueError('Duplicate evidence type')
        return self


class OneHealthRelationInput(OneHealthRelationDetails):
    from_node: OneHealthNodeRef
    to_node: OneHealthNodeRef
    source_assertion_key: str
    evidence: list[EvidenceInput] = Field(min_length=1)


class OneHealthRelation(OneHealthRelationDetails, ChainSupport):
    id: str
    from_node_id: str
    to_node_id: str
    source_assertion_id: str


class ObservationTime(StrictModel):
    kind: Literal['onset','diagnosis','detection','sample_collection','test_result','notification','shipment','exposure','intervention','reporting_cutoff','unknown']
    extent: Literal['point','closed_interval','open_interval','unknown'] = 'unknown'
    start: TextValue
    end: TextValue
    precision: Literal['day','month','year','unknown']
    certainty: Literal['exact','approximately','uncertain','unknown']
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    @model_validator(mode='after')
    def temporal_scope(self):
        values=[x.value for x in (self.start,self.end) if x.value is not None]
        if self.extent=='unknown' and values:raise ValueError('A panel date needs its temporal extent')
        if self.extent=='point' and (not self.start.value or (self.end.value and self.end.value!=self.start.value)):raise ValueError('A point requires one reported date')
        if self.extent=='closed_interval' and (not self.start.value or not self.end.value):raise ValueError('A closed interval requires both bounds')
        if self.extent=='open_interval' and len(values)!=1:raise ValueError('An open interval requires one known bound')
        if values and self.precision=='unknown':
            raise ValueError('A panel date needs its precision')
        for value in values:
            pattern={'day':r'\d{4}-\d{2}-\d{2}','month':r'\d{4}-\d{2}','year':r'\d{4}'}[self.precision]
            if not re.fullmatch(pattern,value):raise ValueError('Panel date precision differs')
            date.fromisoformat(value+{'day':'','month':'-01','year':'-01-01'}[self.precision])
        if self.start.value and self.end.value and self.start.value>self.end.value:
            raise ValueError('Panel date interval is reversed')
        return self


class OneHealthPanelReview(StrictModel):
    key: str = Field(min_length=1)
    record_id: str
    reason: str = Field(min_length=1)
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)
    review_state: Literal['source_checked_draft'] = 'source_checked_draft'
    time: ObservationTime

    @model_validator(mode='after')
    def review_stamp(self):
        stamp(self.reviewed_at)
        return self


class OneHealthTimingInput(OneHealthPanelReview):
    source_assertion_key: str
    node: OneHealthNodeRef
    evidence: list[EvidenceInput] = Field(min_length=1)


class OneHealthTiming(OneHealthPanelReview, ChainSupport):
    source_assertion_id: str
    id: str
    node_id: str


class SamplingDetails(OneHealthPanelReview):
    pair_status: Literal['matched','unresolved','not_applicable']
    unit: TextValue
    frame: TextValue
    population: TextValue
    target: TextValue
    method: TextValue
    pooling: TextValue
    clustering: TextValue
    repeated_sampling: TextValue


class OneHealthSamplingInput(SamplingDetails):
    source_assertion_key: str
    node: OneHealthNodeRef
    positive_measure_key: str | None
    tested_measure_key: str | None
    evidence: list[EvidenceInput] = Field(min_length=1)


class OneHealthSamplingAssessment(SamplingDetails, ChainSupport):
    source_assertion_id: str
    id: str
    node_id: str
    positive_measure_id: str | None
    tested_measure_id: str | None
    display: Literal['proportion','counts_only']
    proportion: float | None = Field(ge=0,le=1)
    display_reason: str


class ContextDetails(OneHealthPanelReview):
    label: str = Field(min_length=1)
    kind: Literal['measured_covariate','reported_condition','source_hypothesis','reported_intervention','evaluated_effect']
    variable: TextValue
    method: TextValue
    place_ids: list[str]
    linkage_note: str = Field(min_length=1)


class OneHealthContextInput(ContextDetails):
    source_assertion_key: str
    node_refs: list[OneHealthNodeRef]
    measure_keys: list[str]
    evidence: list[EvidenceInput] = Field(min_length=1)


class OneHealthContext(ContextDetails, ChainSupport):
    source_assertion_id: str
    id: str
    node_ids: list[str]
    measure_ids: list[str]


class SiteAnnotations(StrictModel):
    contract_version: Literal['1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0']
    records_sha256: str
    reviewed_at: str
    reviewed_by: str
    organizations: list[Organization]
    channels: list[Channel]
    areas: list[Area]
    places: list[PlaceInput]
    endpoints: list[EndpointInput]
    locations: list[LocationInput]
    assertions: list[AssertionInput]
    comparisons: list[ComparisonInput]
    limitations: list[str]
    reviewed_chains: list[ChainInput] = Field(default_factory=list)
    diseases: list[Disease] = Field(default_factory=list)
    disease_reviews: list[DiseaseReviewInput] = Field(default_factory=list)

    one_health_reviews: list[OneHealthReviewInput] = Field(default_factory=list)
    one_health_nodes: list[OneHealthNodeInput] = Field(default_factory=list)
    one_health_relations: list[OneHealthRelationInput] = Field(default_factory=list)
    one_health_timings: list[OneHealthTimingInput] = Field(default_factory=list)
    one_health_sampling_assessments: list[OneHealthSamplingInput] = Field(default_factory=list)
    one_health_contexts: list[OneHealthContextInput] = Field(default_factory=list)

    @model_validator(mode='after')
    def chain_version(self):
        if self.reviewed_chains and self.contract_version == '1.0.0':
            raise ValueError('Chain annotations require contract 1.1.0 or 1.2.0')
        if (self.diseases or self.disease_reviews) and self.contract_version not in {'1.2.0','1.3.0','1.4.0'}:
            raise ValueError('Disease annotations require contract 1.2.0')
        if (self.one_health_reviews or self.one_health_nodes or self.one_health_relations) and self.contract_version not in {'1.3.0','1.4.0'}:
            raise ValueError('One Health annotations require contract 1.3.0 or 1.4.0')
        if (self.one_health_timings or self.one_health_sampling_assessments or self.one_health_contexts) and self.contract_version!='1.4.0':
            raise ValueError('One Health panel annotations require contract 1.4.0')
        return self


class Snapshot(StrictModel):
    generated_at: str
    publication_from: str
    publication_until: str
    capture_from: str
    capture_until: str
    captured_at: str
    next_update_date: str
    next_update_status: Literal['planned'] = 'planned'
    schedule_timezone: str
    schedule_local_time: str
    schedule_source_sha256: str
    schedule_activation: Literal['not_verified'] = 'not_verified'
    corpus_document_count: int
    selected_document_count: int
    selected_record_count: int
    selected_topic_count: int
    source_snapshot_sha256: str
    records_sha256: str
    acquisition_results_sha256: str
    annotations_sha256: str
    metrics_sha256: str
    source_text_hashes: dict[str,str]
    geographic_policy: Literal['neutral_reporting_locations_no_sovereignty_inference'] = 'neutral_reporting_locations_no_sovereignty_inference'
    replay: Literal['retrospective_source_dates_not_historical_editorial_state'] = 'retrospective_source_dates_not_historical_editorial_state'


class SiteBundle(StrictModel):
    contract_version: Literal['1.5.0']
    software_version: str
    release_status: Literal['research_preview']
    snapshot: Snapshot
    organizations: list[Organization]
    channels: list[Channel]
    areas: list[Area]
    places: list[Place]
    display_groups: list[DisplayGroup]
    topics: list[Topic]
    documents: list[Document]
    records: list[SiteRecord]
    assertions: list[Assertion]
    evidence: list[EvidenceSpan]
    comparisons: list[Comparison]
    location_memberships: list[LocationMembership]
    relationships: list[SourceRelation]
    diseases: list[Disease]
    disease_reviews: list[DiseaseReview]
    reviewed_chains: list[ReviewedChain]
    one_health_reviews: list[OneHealthReview]
    one_health_nodes: list[OneHealthNode]
    one_health_relations: list[OneHealthRelation]
    one_health_timings: list[OneHealthTiming]
    one_health_sampling_assessments: list[OneHealthSamplingAssessment]
    one_health_contexts: list[OneHealthContext]
    source_coverage: list[CoverageEdge]
    metrics: MetricsExport
    limitations: list[str]


# Contract 1.2 shares the scientific models and excludes disease reviews.
# The released schema digest prevents shared model changes from altering it.
SiteBundleV12 = create_model('SiteBundle', __base__=StrictModel,
    contract_version=(Literal['1.2.0'], ...),
    **{name: (field.annotation, deepcopy(field)) for name, field in SiteBundle.model_fields.items()
       if name not in {'contract_version', 'diseases', 'disease_reviews', 'one_health_reviews', 'one_health_nodes', 'one_health_relations','one_health_timings','one_health_sampling_assessments','one_health_contexts'}})
SiteBundleV13 = create_model('SiteBundle', __base__=StrictModel,
    contract_version=(Literal['1.3.0'], ...),
    **{name: (field.annotation, deepcopy(field)) for name, field in SiteBundle.model_fields.items()
       if name not in {'contract_version','one_health_reviews','one_health_nodes','one_health_relations','one_health_timings','one_health_sampling_assessments','one_health_contexts'}})
SiteBundleV14 = create_model('SiteBundle', __base__=StrictModel,
    contract_version=(Literal['1.4.0'], ...),
    **{name: (field.annotation, deepcopy(field)) for name, field in SiteBundle.model_fields.items()
       if name not in {'contract_version','one_health_timings','one_health_sampling_assessments','one_health_contexts'}})
SITE_MODELS = {'1.2.0': SiteBundleV12, '1.3.0': SiteBundleV13, '1.4.0': SiteBundleV14, SITE_VERSION: SiteBundle}
V14_SCHEMA_SHA256 = 'a902b28d61bd3a23567136f97b7fb9613866c5ffea793e33de7e2c70e0534824'
V14_ANNOTATIONS_SHA256 = '12aa5226c3c8c7d91f3e9d6312447cab6e069c3160876bf047da20aadbc691d0'
V13_SCHEMA_SHA256 = '28496cbe0699c432d703a8b752bc09106f253ae17e8f40f0242cedbd4384a867'
V13_ANNOTATIONS_SHA256 = '3eb4c5cf2a7d0cd9446891955e7e70b4f5e5dcdef5d62d43f68d45cfe0f6c71a'
V12_SCHEMA_SHA256 = '3bac561d88ebe8481507cc996580f1bd817e3bd9496b087597dd748a540622ba'
V12_ANNOTATIONS_SHA256 = '257487e1d3b7e3a9f2642bcd627e52df0aff6e3b5755955bcbd679fe3693989a'


def site_model(version):
    if version not in SITE_MODELS:
        raise ValueError('Unsupported site contract: ' + str(version))
    model = SITE_MODELS[version]
    if version == '1.2.0' and digest(model.model_json_schema()) != V12_SCHEMA_SHA256:
        raise ValueError('Contract 1.2 validation model differs from its released schema')
    if version == '1.3.0' and digest(model.model_json_schema()) != V13_SCHEMA_SHA256:
        raise ValueError('Contract 1.3 validation model differs from its sealed schema')
    if version == '1.4.0' and digest(model.model_json_schema()) != V14_SCHEMA_SHA256:
        raise ValueError('Contract 1.4 validation model differs from its sealed schema')
    return model


def _index(rows, key='id'):
    index={r[key]:r for r in rows}
    if len(index)!=len(rows):raise ValueError('Duplicate entity ID')
    return index


def _group_by(rows, key):
    groups=defaultdict(list)
    for row in rows:groups[key(row)].append(row)
    return groups


def _comparisons_by_record(comparisons, assertions):
    groups=defaultdict(list)
    for comparison in comparisons:
        for rid in {assertions[aid]['record_id'] for aid in comparison['participant_ids']}:
            groups[rid].append(comparison)
    return groups


def validate_bundle(data):
    """Validate schema and graph integrity at export and website build time."""
    site_model(data.get('contract_version')).model_validate(data)
    names=['organizations','channels','places','display_groups','topics','documents','records','assertions','evidence','comparisons','location_memberships','relationships','source_coverage']
    ix={name:_index(data[name]) for name in names};ix['areas']=_index(data['areas'],'code')
    topic_records=_group_by(data['records'],lambda r:r['topic_id'])
    document_records=_group_by(data['records'],lambda r:r['document_id'])
    coverage_records=_group_by(data['records'],lambda r:(r['channel_id'],r['topic_id']))
    record_assertions=_group_by(data['assertions'],lambda a:a['record_id'])
    record_locations=_group_by(data['location_memberships'],lambda m:m['record_id'])
    document_locations=_group_by(data['location_memberships'],lambda m:m['document_id'])
    record_comparisons=_comparisons_by_record(data['comparisons'],ix['assertions'])
    metric_panels={(p['kind'],p['id']) for p in data['metrics']['panels']}
    def require(name,ids):
        if len(ids)!=len(set(ids)) or not set(ids)<=ix[name].keys():raise ValueError('Invalid '+name+' reference')
    def rule(item, expected):
        require('records',item['eligibility']['record_ids'])
        if set(item['eligibility']['record_ids'])!=set(expected):raise ValueError('Temporal support must match all evidence')
    diseases = _index(data.get('diseases', []))
    disease_reviews = data.get('disease_reviews', [])
    _index(disease_reviews)
    if len({r['record_id'] for r in disease_reviews}) != len(disease_reviews):
        raise ValueError('Multiple disease reviews for one record')
    for review in disease_reviews:
        require('records', [review['record_id']]); require('evidence', review['evidence_ids'])
        if not set(review['disease_ids']) <= diseases.keys(): raise ValueError('Unknown disease reference')
        evidence_records = {ix['evidence'][eid]['record_id'] for eid in review['evidence_ids']}
        if review['record_id'] not in evidence_records: raise ValueError('Disease review needs evidence from its record')
        rule(review, evidence_records)
    for c in data['channels']:require('organizations',[c['organization_id']])
    for r in data['records']:
        require('documents',[r['document_id']]);require('topics',[r['topic_id']]);require('channels',[r['channel_id']])
        date.fromisoformat(r['publication'][:10]);stamp(r['capture'])
        for name,key in [('assertions','assertion_ids'),('comparisons','comparison_ids'),('location_memberships','location_membership_ids')]:require(name,r[key])
        if r['flagged_issue_review']=='reviewed' and not r['comparison_ids']:raise ValueError('Flag review requires a comparison')
    for e in data['evidence']:
        require('records',[e['record_id']]);require('documents',[e['document_id']])
        if ix['records'][e['record_id']]['document_id']!=e['document_id']:raise ValueError('Evidence document mismatch')
        if e['claim_index'] is not None and e['claim_index'] not in ix['records'][e['record_id']]['claim_indexes']:raise ValueError('Unknown evidence claim')
        if e['end']-e['start']!=len(e['quote']) or digest(e['quote'].encode())!=e['quote_sha256']:raise ValueError('Invalid evidence span')
        if e['source_text_sha256']!=data['snapshot']['source_text_hashes'][e['document_id']]:raise ValueError('Source hash mismatch')
    measures=_index(data['metrics']['measures'],'measure_id')
    from .longitudinal import validate_series
    validate_series(data['metrics']['reviewed_series'],measures,ix['records'],data['snapshot']['source_text_hashes'])
    metric_assertions={a['measure_id']:a for a in data['assertions'] if a['measure_id'] is not None}
    if set(measures)!=set(metric_assertions):raise ValueError('Every measure requires one assertion')
    for a in data['assertions']:
        require('records',[a['record_id']]);require('evidence',a['evidence_ids'])
        r=ix['records'][a['record_id']]
        if a['claim_index'] not in r['claim_indexes']:raise ValueError('Unknown assertion claim')
        if r['document_id']!=a['document_id'] or a['id'] not in r['assertion_ids']:raise ValueError('Assertion membership mismatch')
        rule(a,{ix['evidence'][e]['record_id'] for e in a['evidence_ids']})
        if a['measure_id'] is not None and a['measure_id'] not in measures:raise ValueError('Unknown measure')
        if (a['kind']=='measure')!=(a['measure_id'] is not None):raise ValueError('Measure assertion requires its measure')
        if a['measure_id']:
            m=measures[a['measure_id']];ref=m['source_reference']
            if (a['record_id'],a['document_id'],a['claim_index'])!=(ref['record_id'],ref['document_id'],ref['claim_index']):raise ValueError('Metric assertion source mismatch')
            expected={(e['record_id'],e['claim_index'],q) for e in m['evidence_references'] for q in e['quote_indexes']}
            actual={(ix['evidence'][e]['record_id'],ix['evidence'][e]['claim_index'],ix['evidence'][e]['quote_index']) for e in a['evidence_ids']}
            if expected!=actual:raise ValueError('Metric evidence reference mismatch')
    edges=defaultdict(list)
    for c in data['comparisons']:
        require('assertions',c['participant_ids']);require('evidence',c['evidence_ids'])
        expected={ix['evidence'][e]['record_id'] for e in c['evidence_ids']}
        for a in c['participant_ids']:expected.update(ix['assertions'][a]['eligibility']['record_ids'])
        rule(c,expected)
        for line in c['lineage']:
            require('evidence',line['evidence_ids'])
            if not set(line['evidence_ids'])<=set(c['evidence_ids']):raise ValueError('Revision evidence outside comparison')
            before=ix['assertions'][line['from_assertion_id']];after=ix['assertions'][line['to_assertion_id']]
            if ix['records'][after['record_id']]['publication']<ix['records'][before['record_id']]['publication']:raise ValueError('Revision publication precedes original assertion')
            edges[before['id']].append(after['id'])
    def visit(node,path):
        if node in path:raise ValueError('Cyclic revision lineage')
        for nxt in edges[node]:visit(nxt,path|{node})
    for node in list(edges):visit(node,set())
    for m in data['location_memberships']:
        require('areas',[m['area_code']]);require('records',[m['record_id']]);require('evidence',m['evidence_ids'])
        if m['document_id']!=ix['records'][m['record_id']]['document_id']:raise ValueError('Location document mismatch')
        if m['claim_index'] is not None and m['claim_index'] not in ix['records'][m['record_id']]['claim_indexes']:raise ValueError('Unknown location claim')
        rule(m,{ix['evidence'][e]['record_id'] for e in m['evidence_ids']})
    for p in data['places']:
        require('areas',p['area_codes']);require('topics',p['topic_ids']);require('records',p['record_ids']);require('relationships',p['relationship_ids']);require('location_memberships',p['location_membership_ids'])
        if set(p['record_ids'])!={r['id'] for tid in p['topic_ids'] for r in topic_records[tid]}:raise ValueError('Place record membership mismatch')
    for g in data['display_groups']:
        require('places',g['place_ids'])
        if any((ix['places'][p]['longitude'],ix['places'][p]['latitude'])!=(g['longitude'],g['latitude']) for p in g['place_ids']):raise ValueError('Display group combines different reference points')
    for t in data['topics']:
        require('records',t['record_ids']);require('places',t['place_ids'])
        if set(t['record_ids'])!={r['id'] for r in topic_records[t['id']]}:raise ValueError('Topic membership mismatch')
    for d in data['documents']:
        require('records',d['record_ids']);require('channels',[d['channel_id']]);require('location_memberships',d['location_membership_ids'])
        for url in [d['url'],d['content_url']]:
            if not canonical_url(url).startswith('https://'):raise ValueError('Source URLs require HTTPS')
        if set(d['record_ids'])!={r['id'] for r in document_records[d['id']]}:raise ValueError('Document membership mismatch')
        if set(d['location_membership_ids'])!={m['id'] for m in document_locations[d['id']]}:raise ValueError('Document location membership mismatch')
        for rid in d['record_ids']:
            r=ix['records'][rid]
            if (d['publication'],d['capture'],d['channel_id'])!=(r['publication'],r['capture'],r['channel_id']):raise ValueError('Canonical document dates or channel mismatch')
    for r in data['relationships']:
        require('assertions',r['assertion_ids']);require('topics',r['topic_ids'])
        if (r['category'],r['metric_panel_id']) not in metric_panels:raise ValueError('Missing relationship metric panel')
        support={rid for a in r['assertion_ids'] for rid in ix['assertions'][a]['eligibility']['record_ids']}
        if r['parent_id']:
            require('relationships',[r['parent_id']]);support.update(ix['relationships'][r['parent_id']]['eligibility']['record_ids'])
        rule(r,support)
        if r['category']=='geographic_link':
            require('places',[r['from_place_id'],r['to_place_id']])
            if r['kind'] not in {'movement','shared_event','hypothesis'} or (r['directed'] and r['kind']!='movement'):raise ValueError('Unsupported geographic link')
    for e in data['source_coverage']:
        require('channels',[e['channel_id']]);require('topics',[e['topic_id']]);require('records',e['record_ids']);require('documents',e['document_ids'])
        expected={r['id'] for r in coverage_records[e['channel_id'],e['topic_id']]}
        if set(e['record_ids'])!=expected or set(e['document_ids'])!={ix['records'][r]['document_id'] for r in expected}:raise ValueError('Coverage membership mismatch')
    if set(ix['records'])!={r['record_id'] for r in data['metrics']['records']}:raise ValueError('Metrics and site records differ')
    findings=_index(data['metrics']['findings'],'finding_id')
    for panel in data['metrics']['panels']:
        support={tuple(pair) for pair in panel['support']}
        for rid,ci in support:
            require('records',[rid])
            if ci not in ix['records'][rid]['claim_indexes']:raise ValueError('Metric panel claim is missing')
        for mid in panel['measure_ids']:
            if mid not in measures or not all((e['record_id'],e['claim_index']) in support for e in measures[mid]['evidence_references']):raise ValueError('Metric panel includes unrelated claim evidence')
        for card in panel['card_groups']:
            if not set(card['measure_ids'])<=set(panel['measure_ids']):raise ValueError('Card includes unrelated measure')
        for fid in panel['finding_ids']:
            if fid not in findings or (findings[fid]['evidence']['record_id'],findings[fid]['evidence']['claim_index']) not in support:raise ValueError('Metric panel includes unrelated finding')
    for r in data['records']:
        if set(r['assertion_ids'])!={a['id'] for a in record_assertions[r['id']]}:raise ValueError('Record assertion membership mismatch')
        if set(r['comparison_ids'])!={c['id'] for c in record_comparisons[r['id']]}:raise ValueError('Record comparison membership mismatch')
        if set(r['location_membership_ids'])!={m['id'] for m in record_locations[r['id']]}:raise ValueError('Record location membership mismatch')
    from .chains import validate_chains
    validate_chains(data['reviewed_chains'], ix)
    from .one_health import validate_one_health
    validate_one_health(data, ix)
    counts=data['snapshot']
    if (counts['selected_record_count'],counts['selected_document_count'],counts['selected_topic_count'])!=(len(data['records']),len(data['documents']),len(data['topics'])):raise ValueError('Snapshot counts differ from entity memberships')
    if counts['captured_at']!=max(r['capture'] for r in data['records']) or counts['capture_until']!=counts['captured_at']:raise ValueError('Snapshot capture timestamp mismatch')
    if counts['records_sha256']!=data['metrics']['records_sha256']:raise ValueError('Metric snapshot identity mismatch')
    return data


def planned_update(captured_at: str, schedule: Path):
    config=yaml.load(schedule.read_text(),Loader=yaml.BaseLoader)['on']['schedule']
    if len(config)!=1:raise ValueError('One weekly schedule is required')
    entry=config[0]; match=re.fullmatch(r'(\d+) (\d+) \* \* ([0-6])',entry['cron'])
    if not match:raise ValueError('Expected a weekly collection schedule')
    minute,hour,weekday=map(int,match.groups());zone=ZoneInfo(entry['timezone'])
    captured=datetime.fromisoformat(stamp(captured_at)).astimezone(zone)
    target=captured.replace(hour=hour,minute=minute,second=0,microsecond=0)
    target+=timedelta(days=((weekday-1)%7-captured.weekday())%7)
    if target<=captured:target+=timedelta(days=7)
    return dict(captured_at=captured_at,next_update_date=target.date().isoformat(),next_update_status='planned',
                schedule_timezone=entry['timezone'],schedule_local_time=f'{hour:02}:{minute:02}',
                schedule_source_sha256=digest(schedule.read_bytes()),schedule_activation='not_verified')


def export_site(snapshot: Path, results: Path, metrics_path: Path, annotations: Path, source_dir: Path, out: Path, schedule: Path, *, max_input_bytes: int = 64_000_000):
    if type(max_input_bytes) is not int or not 0 < max_input_bytes <= 128_000_000:
        raise ValueError('Site input budget must be an integer from 1 to 128000000 bytes')
    if out.exists() and any(out.iterdir()):raise ValueError('Site export target must be empty')
    for path in [snapshot,results,metrics_path,annotations]:
        if path.stat().st_size>max_input_bytes:raise ValueError('Site export input exceeds the file budget')
    data=read_json(snapshot);metrics=MetricsExport.model_validate(read_json(metrics_path)).model_dump(mode='json')
    if 'geographic_review' in data:
        from .geography import validate_coverage
        validate_coverage(data)
    ann=SiteAnnotations.model_validate(read_json(annotations));stamp(ann.reviewed_at)
    if ann.records_sha256!=digest(data['records']) or metrics['records_sha256']!=ann.records_sha256:raise ValueError('Inputs refer to different record snapshots')
    if metrics['source_snapshot_sha256']!=digest(snapshot.read_bytes()):raise ValueError('Metrics snapshot hash mismatch')
    rs=_index(data['records']);ts=_index(data['tracks']);acquired=_index(read_json(results),'document_id')
    texts={};hashes={};page_ends={};page_numbers={}
    for did in {r['document_id'] for r in rs.values()}:
        path=source_dir/(did+'.txt')
        if not re.fullmatch(r'doc_[a-f0-9]{24}',did) or path.stat().st_size>4_000_000:raise ValueError('Invalid source document or size')
        texts[did]=path.read_text();hashes[did]=digest(path.read_bytes())
        if hashes[did]!=acquired[did]['document']['text_sha256']:raise ValueError('Captured source hash differs from acquisition metadata')
        pages=list(re.finditer(r'\[\[PAGE (\d+)\]\]',texts[did]))
        page_ends[did]=[p.end() for p in pages];page_numbers[did]=[int(p[1]) for p in pages]
    for series in metrics['reviewed_series']:
        for e in series['evidence']:
            if texts[e['document_id']][e['start']:e['end']]!=e['quote']:
                raise ValueError('Longitudinal method span differs from captured source')
    evidence={};quote_spans={}
    def ev(ref):
        r=rs[ref.record_id];did=r['document_id'];text=texts[did]
        if ref.claim_index is not None:
            claim=next(c for c in r['claims'] if c['claim_index']==ref.claim_index)
        quote=claim['quotes'][ref.quote_index] if ref.quote_index is not None else ref.quote
        # Whitespace is represented verbatim in the emitted source span.
        words=tuple(quote.split());key=(did,words)
        if key not in quote_spans:
            quote_spans[key]=list(re.finditer(r'\s+'.join(re.escape(w) for w in words),text))
        matches=quote_spans[key]
        if not matches or ref.occurrence>=len(matches):raise ValueError('Evidence span not found in captured source: '+ref.record_id)
        m=matches[ref.occurrence];raw=text[m.start():m.end()]
        page_index=bisect_right(page_ends[did],m.start())-1
        row=dict(id=uid('evidence',did,ref.record_id,ref.claim_index,ref.quote_index,m.start(),m.end(),ref.section),document_id=did,
                 record_id=r['id'],claim_index=ref.claim_index,quote_index=ref.quote_index,section=ref.section,quote=raw,
                 source_text_sha256=hashes[did],start=m.start(),end=m.end(),page=page_numbers[did][page_index] if page_index>=0 else None,quote_sha256=digest(raw.encode()),offset_basis='unicode_code_points_half_open')
        evidence[row['id']]=row;return row['id']
    def evrefs(refs):return list(dict.fromkeys(ev(EvidenceInput.model_validate(r)) if isinstance(r,dict) else ev(r) for r in refs))
    def evidence_rule(ids):return Eligibility(record_ids=sorted({evidence[i]['record_id'] for i in ids})).model_dump()
    assertions=[];keys={}
    def add_assertion(key,row):
        if key in keys:raise ValueError('Duplicate assertion key')
        row['id']=uid('assertion',key,row);keys[key]=row['id'];assertions.append(row)
    for r in rs.values():
        for c in r['claims']:
            refs=[EvidenceInput(record_id=r['id'],claim_index=c['claim_index'],quote_index=i,section='Extracted claim quotation') for i in range(len(c['quotes']))]
            ids=evrefs(refs)
            add_assertion('claim:'+r['id']+':'+str(c['claim_index']),dict(record_id=r['id'],document_id=r['document_id'],claim_index=c['claim_index'],kind='finding',text=c['text'],evidence_ids=ids,eligibility=evidence_rule(ids),review_state='extracted_draft'))
    for m in metrics['measures']:
        for e in m['evidence_references']:
            r=rs[e['record_id']];claim=next(c for c in r['claims'] if c['claim_index']==e['claim_index'])
            if e['document_id']!=r['document_id'] or e['quotes']!=[claim['quotes'][q] for q in e['quote_indexes']]:raise ValueError('Metric quotations differ from the source snapshot')
        ids=evrefs([dict(record_id=e['record_id'],claim_index=e['claim_index'],quote_index=q,section=m['label']+' · '+m['period_label']) for e in m['evidence_references'] for q in e['quote_indexes']])
        ref=m['source_reference'];value=m['observation_date']
        add_assertion('metric:'+m['annotation_key'],dict(record_id=ref['record_id'],document_id=ref['document_id'],claim_index=ref['claim_index'],kind='measure',text=m['label'],measure_id=m['measure_id'],observation_date={'value':value,'status':'reported' if value else 'not_reported'},evidence_ids=ids,eligibility=evidence_rule(ids),review_state='source_checked_draft'))
    for a in ann.assertions:
        r=rs[a.record_id]
        if a.claim_index not in [c['claim_index'] for c in r['claims']]:raise ValueError('Assertion claim does not exist')
        ids=evrefs(a.evidence)
        add_assertion(a.key,dict(record_id=r['id'],document_id=r['document_id'],claim_index=a.claim_index,kind=a.kind,text=a.text,value=a.value.model_dump(mode='json'),observation_date=a.observation_date.model_dump(mode='json'),evidence_ids=ids,eligibility=evidence_rule(ids),review_state='source_checked_draft'))
    ai=_index(assertions);comparisons=[]
    for c in ann.comparisons:
        ids=evrefs(c.evidence);participants=[keys[k] for k in c.participants]
        if len(c.participant_labels)!=len(participants):raise ValueError('Comparison label count differs from participants')
        support={evidence[e]['record_id'] for e in ids}
        for a in participants:support.update(ai[a]['eligibility']['record_ids'])
        comparisons.append(dict(id=uid('comparison',c.key),kind=c.kind,status=c.status,participant_ids=participants,participant_labels=dict(zip(participants,c.participant_labels)),reason=c.reason,scope_review=c.scope_review,evidence_ids=ids,eligibility=Eligibility(record_ids=sorted(support)).model_dump(),reviewed_at=ann.reviewed_at,reviewed_by=ann.reviewed_by,review_state='source_checked_draft',independence=c.independence,lineage=[dict(from_assertion_id=keys[a],to_assertion_id=keys[b],evidence_ids=ids) for a,b in c.lineage]))
    memberships=[]
    for loc in ann.locations:
        ids=evrefs(loc.evidence);r=rs[loc.record_id]
        if loc.claim_index is not None and loc.claim_index not in [c['claim_index'] for c in r['claims']]:raise ValueError('Location claim does not exist')
        memberships.append(dict(id=uid('location',loc.record_id,loc.claim_index,loc.area_code,loc.role),record_id=r['id'],document_id=r['document_id'],claim_index=loc.claim_index,area_code=loc.area_code,role=loc.role,evidence_ids=ids,reason=loc.reason,review_state='source_checked_draft',eligibility=evidence_rule(ids)))
    endpoints={e.relationship_id:e for e in ann.endpoints};relations=[]
    for category,field in [('geographic_link','map_links'),('assessment','relationships')]:
        for r in data[field]:
            ids=[keys['claim:'+rid+':'+str(ci)] for rid,ci in r['support']]
            ep=endpoints.get(r['id']);geographic=category=='geographic_link'
            if geographic and not ep:raise ValueError('Geographic relation lacks reviewed endpoint places')
            topic_ids=sorted({rs[rid]['track'] for rid,ci in r['support']})
            row=dict(id=r['id'],category=category,kind=r['type'],label=r.get('label',r.get('status')),from_label=r['from']['label'] if geographic else r['from'],to_label=r['to']['label'] if geographic else r['to'],from_place_id=ep.from_place_id if ep else None,to_place_id=ep.to_place_id if ep else None,directed=r.get('directed',False),topic_ids=topic_ids,basis=r['basis'],limit=r['limit'],assertion_ids=ids,eligibility=Eligibility(record_ids=sorted({rid for rid,ci in r['support']})).model_dump(),parent_id=None,metric_panel_id=r['id'],review_state='source_checked_draft')
            relations.append(row)
            for update_index,update in enumerate(r.get('updates',[])):
                support=sorted(set(row['eligibility']['record_ids'])|{rid for rid,ci in update['support']})
                relations.append(dict(id=uid('assessment_update',r['id'],update),category='assessment_update',kind=r['type'],label='Later assessment',from_label=None,to_label=None,from_place_id=None,to_place_id=None,directed=False,topic_ids=topic_ids,basis=update['text'],limit=r['limit'],assertion_ids=[keys['claim:'+rid+':'+str(ci)] for rid,ci in update['support']],eligibility=Eligibility(record_ids=support).model_dump(),parent_id=r['id'],metric_panel_id=r['id']+':'+str(update_index),review_state='source_checked_draft'))
    channels={c.snapshot_source:c for c in ann.channels};records=[]
    record_assertions=_group_by(assertions,lambda a:a['record_id'])
    record_comparisons=_comparisons_by_record(comparisons,ai)
    record_locations=_group_by(memberships,lambda m:m['record_id'])
    document_locations=_group_by(memberships,lambda m:m['document_id'])
    for r in rs.values():
        comps=[c['id'] for c in record_comparisons[r['id']]]
        if r.get('conflict') and not comps:raise ValueError('Flagged record lacks an assertion comparison')
        locs=[m['id'] for m in record_locations[r['id']]]
        records.append(dict(id=r['id'],document_id=r['document_id'],topic_id=r['track'],channel_id=channels[r['source']].id,title=r['title'],publication=r['publication'],publication_basis=r['date_basis'],capture=r['capture'],claim_indexes=[c['claim_index'] for c in r['claims']],assertion_ids=[a['id'] for a in record_assertions[r['id']]],comparison_ids=comps,location_membership_ids=locs,geographic_review='source_checked_draft' if locs else 'pending',flagged_issue_review='reviewed' if r.get('conflict') else 'not_flagged'))
    document_records=_group_by(records,lambda r:r['document_id'])
    topic_records=_group_by(records,lambda r:r['topic_id'])
    coverage_records=_group_by(records,lambda r:(r['channel_id'],r['topic_id']))
    documents=[]
    for did in sorted(texts):
        d=acquired[did]['document'];members=document_records[did];r=members[0]
        channel=next(c for c in ann.channels if c.id==r['channel_id'])
        if channel.acquisition_source!=d['source_id']:raise ValueError('Reporting channel differs from acquisition metadata')
        documents.append(dict(id=did,title=d['title'],url=d['url'],content_url=d['content_url'],publication=d['published_at'],publication_precision=d['publication_precision'],publication_basis=r['publication_basis'],capture=r['capture'],channel_id=r['channel_id'],record_ids=[r['id'] for r in members],location_membership_ids=[m['id'] for m in document_locations[did]],raw_sha256=d['raw_sha256'],text_sha256=d['text_sha256'],authority_review='not_extracted'))
    record_order={r['id']:i for i,r in enumerate(records)}
    place_relations=defaultdict(list)
    for relation in relations:
        for pid in {relation['from_place_id'],relation['to_place_id']}:
            if pid is not None:place_relations[pid].append(relation)
    membership_order={m['id']:i for i,m in enumerate(memberships)}
    places=[]
    for p in ann.places:
        member_records={r['id'] for tid in p.topic_ids for r in topic_records[tid]}
        rids=sorted(member_records,key=record_order.__getitem__)
        linked=place_relations[p.id];relids=[r['id'] for r in linked]
        support=member_records|{rid for r in linked for rid in r['eligibility']['record_ids']}
        area_codes=set(p.area_codes)
        locs=sorted((m['id'] for rid in support for m in record_locations[rid] if m['area_code'] in area_codes),key=membership_order.__getitem__)
        places.append(dict(**p.model_dump(),record_ids=rids,relationship_ids=relids,location_membership_ids=locs,geographic_review='source_reference_available' if locs else 'pending',appearance='any_member_record_or_eligible_relationship'))
    groups=defaultdict(list)
    for p in places:groups[(p['longitude'],p['latitude'])].append(p['id'])
    display=[dict(id=uid('display',*xy),place_ids=sorted(ids),longitude=xy[0],latitude=xy[1],meaning='coincident_reference_points') for xy,ids in sorted(groups.items())]
    topic_places=defaultdict(list)
    for p in places:
        for tid in dict.fromkeys(p['topic_ids']):topic_places[tid].append(p['id'])
    topics=[dict(id=t['id'],label=t['label'],kind=t['kind'],disease_group=t['disease_group'],place_ids=topic_places[t['id']],record_ids=[r['id'] for r in topic_records[t['id']]]) for t in ts.values()]
    coverage=[]
    for ch,topic in sorted(coverage_records):
        members=coverage_records[ch,topic]
        coverage.append(dict(id=uid('coverage',ch,topic),channel_id=ch,topic_id=topic,document_ids=sorted({r['document_id'] for r in members}),record_ids=[r['id'] for r in members],meaning='reporting_coverage'))
    meta=dict(generated_at=utcnow(),publication_from=min(r['publication'][:10] for r in records),publication_until=max(r['publication'][:10] for r in records),capture_from=min(r['capture'] for r in records),capture_until=max(r['capture'] for r in records),corpus_document_count=len(acquired),selected_document_count=len(documents),selected_record_count=len(records),selected_topic_count=len(topics),source_snapshot_sha256=digest(snapshot.read_bytes()),records_sha256=ann.records_sha256,acquisition_results_sha256=digest(results.read_bytes()),annotations_sha256=digest(annotations.read_bytes()),metrics_sha256=digest(metrics_path.read_bytes()),source_text_hashes=hashes,
              **planned_update(max(r['capture'] for r in records),schedule))
    from .chains import prepare_chains
    chains=prepare_chains(ann.reviewed_chains, evrefs, evidence, rs, keys, {p['id']:p for p in places})
    disease_reviews=[]
    for review in ann.disease_reviews:
        ids=evrefs(review.evidence)
        disease_reviews.append(dict(**review.model_dump(exclude={'evidence'}), id=uid('disease-review', review.record_id),
            evidence_ids=ids, eligibility=dict(record_ids=sorted({evidence[e]['record_id'] for e in ids}))))
    from .one_health import prepare_one_health
    oh=prepare_one_health(ann, evrefs, evidence, rs, keys, ai, metrics['measures'])
    bundle=SiteBundle.model_validate(dict(contract_version=SITE_VERSION,software_version=__version__,release_status='research_preview',snapshot=meta,organizations=[o.model_dump() for o in ann.organizations],channels=[c.model_dump() for c in ann.channels],areas=[a.model_dump() for a in ann.areas],places=places,display_groups=display,topics=topics,documents=documents,records=records,assertions=assertions,evidence=list(evidence.values()),comparisons=comparisons,location_memberships=memberships,relationships=relations,source_coverage=coverage,metrics=metrics,reviewed_chains=chains,diseases=[d.model_dump() for d in ann.diseases],disease_reviews=disease_reviews,**oh,limitations=ann.limitations)).model_dump(mode='json')
    validate_bundle(bundle)
    out.mkdir(parents=True,exist_ok=True)
    write_json(out/'atlas-site.json',bundle);write_json(out/'atlas-site.schema.json',SiteBundle.model_json_schema())
    write_json(out/'annotations.schema.json',SiteAnnotations.model_json_schema())
    (out/'review.html').write_text(render_review(bundle),encoding='utf-8')
    (out/'view.mjs').write_text(files('atlas').joinpath('assets/site_view.js').read_text(),encoding='utf-8')
    write_json(out/'manifest.json',dict(contract_version=SITE_VERSION,files={p.name:digest(p.read_bytes()) for p in sorted(out.iterdir())}))
    return bundle


def verify_site(path: Path):
    manifest=read_json(path/'manifest.json')
    version=manifest['contract_version'];model=site_model(version)
    if set(manifest['files'])!={'atlas-site.json','atlas-site.schema.json','annotations.schema.json','review.html','view.mjs'}:raise ValueError('Unsupported site bundle')
    for name,sha in manifest['files'].items():
        if digest((path/name).read_bytes())!=sha:raise ValueError('Bundle checksum mismatch: '+name)
    if read_json(path/'atlas-site.schema.json')!=model.model_json_schema():raise ValueError('Unsupported site schema')
    expected_annotations={'1.2.0':V12_ANNOTATIONS_SHA256,'1.3.0':V13_ANNOTATIONS_SHA256,'1.4.0':V14_ANNOTATIONS_SHA256}.get(version,digest(SiteAnnotations.model_json_schema()))
    if digest(read_json(path/'annotations.schema.json'))!=expected_annotations:raise ValueError('Unsupported annotation schema')
    selector={'1.2.0':'assets/site_view_v1_2.js','1.3.0':'assets/site_view_v1_3.js','1.4.0':'assets/site_view_v1_4.js'}.get(version,'assets/site_view.js')
    if (path/'view.mjs').read_bytes()!=files('atlas').joinpath(selector).read_bytes():raise ValueError('Unsupported view rules')
    data=read_json(path/'atlas-site.json')
    if data.get('contract_version')!=version:raise ValueError('Manifest and data contract versions differ')
    validate_bundle(data)
    return dict(contract_version=version,records=len(data['records']),documents=len(data['documents']),assertions=len(data['assertions']),comparisons=len(data['comparisons']),status='valid')


def render_review(data):
    esc=lambda x:html.escape(str(x)); assertions=_index(data['assertions']);evidence=_index(data['evidence'])
    measures=_index(data['metrics']['measures'],'measure_id');records=_index(data['records'])
    sections=[]
    for c in data['comparisons']:
        branches=[]
        for aid in c['participant_ids']:
            a=assertions[aid];m=measures.get(a['measure_id']);r=records[a['record_id']]
            value=(str(m['value'])+' '+m['unit']) if m else (a['value']['value'] or a['text'])
            branches.append('<li><b>'+esc(c['participant_labels'][aid])+'</b><p>'+esc(value)+'</p><small>'+esc(r['publication'][:10]+' · '+a['record_id']+' · claim '+str(a['claim_index']))+'</small></li>')
        quotes=''.join('<details><summary>'+esc(evidence[e]['section']+' · page '+str(evidence[e]['page']))+'</summary><blockquote>'+esc(evidence[e]['quote'])+'</blockquote></details>' for e in c['evidence_ids'])
        sections.append('<article><h2>'+esc(c['kind'].replace('_',' ').title())+' · '+esc(c['status'])+'</h2><ul>'+''.join(branches)+'</ul><p>'+esc(c['reason'])+'</p><p>'+esc(c['scope_review'])+'</p>'+quotes+'</article>')
    meta=data['snapshot']
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ATLAS assertion review</title><style>body{font:16px/1.55 system-ui;max-width:1050px;margin:32px auto;padding:0 22px;color:#193c45}article{margin:30px 0;padding-top:20px;border-top:1px solid #cad8d5}li{margin:15px 0;overflow-wrap:anywhere}blockquote{border-left:3px solid #c8887c;padding-left:15px}summary{cursor:pointer}small{color:#536d74}</style><h1>ATLAS assertion comparisons</h1><p>Research preview · source review awaiting editorial acceptance.</p><p>Captured '+esc(meta['captured_at'])+' · Next planned collection '+esc(meta['next_update_date'])+' ('+esc(meta['schedule_timezone'])+').</p><p><a href="atlas-site.json">Export</a> · <a href="atlas-site.schema.json">Schema</a> · <a href="manifest.json">Checksums</a></p>'+''.join(sections)+'<h2>Review coverage</h2><ul>'+''.join('<li>'+esc(x)+'</li>' for x in data['limitations'])+'</ul></html>'
