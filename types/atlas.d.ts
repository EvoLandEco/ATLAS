/** ATLAS data 1.5.0, metrics 0.2.0 and compact figures 1.0.0. Validate JSON before use. */
export type AtlasValueStatus = 'reported' | 'not_reported' | 'unknown' | 'not_applicable' | 'not_extracted' | 'conflicting' | 'pending_verification' | 'not_comparable' | 'access_restricted';
export interface AtlasValue { value: string | null; status: AtlasValueStatus }
export interface AtlasEligibility { rule: 'all_supporting_records_in_window'; record_ids: string[]; partial: 'hide_relationship_keep_visible_assertions' }
export interface AtlasClaimReference { record_id: string; document_id: string; claim_index: number; quote_indexes: number[] }
export interface AtlasMetricEvidence extends AtlasClaimReference { quotes: string[]; quote_sha256: string[] }
export interface AtlasMeasure {
  annotation_key: string; measure_id: string; context_id: string; track_id: string; source_id: string;
  label: string; metric: string; value: number | null; value_status: AtlasValueStatus; unit: string;
  count_kind: string; case_class: string; date_basis: string; period_start: AtlasValue; period_end: AtlasValue;
  case_definition: AtlasValue; population: AtlasValue; stratum: AtlasValue; denominator: number | null;
  denominator_status: AtlasValueStatus; qualifier: string; origin_authority: AtlasValue;
  disease: AtlasValue; pathogen: AtlasValue; host: AtlasValue; geography: AtlasValue;
  acquisition: string; transmission_role: string; as_of: AtlasValue; period_label: string;
  denominator_population: AtlasValue; ratio_basis: string; cumulative_baseline: AtlasValue;
  source_reference: AtlasClaimReference; context_references: AtlasClaimReference[];
  evidence: { field: string; quote: string; locator: string }; evidence_references: AtlasMetricEvidence[];
  numeric_evidence_review: string | null; semantic_note: string; priority: number; conflict_set: string | null;
  proposal_candidates: string[]; supersedes: string[]; revision_reason: string | null;
  publication: string; publication_basis: string; capture: string; source_url: string;
  review_status: 'source_checked_draft'; observation_date: string | null;
  observation_date_status: 'reported' | 'not_reported'; source_date_warning: boolean; superseded: boolean;
}
export interface AtlasCardGroup { context_id: string; observation_date: string | null; measure_ids: string[]; priority: number }
export interface AtlasCompactGroup {
  id: string; label: string; metric: string; value: number | null; value_status: AtlasValueStatus;
  unit: string; observation_date: string | null; priority: number; measure_ids: string[];
  context_ids: string[]; source_ids: string[]; basis: 'matching_recorded_scope_and_value'; comparability_status: 'not_established';
}
export type AtlasPanelKind = 'record' | 'topic' | 'geographic_link' | 'assessment' | 'assessment_update';
export interface AtlasPanel {
  kind: AtlasPanelKind; id: string; support: [string, number][]; measure_ids: string[];
  card_groups: AtlasCardGroup[]; finding_ids: string[];
}
export interface AtlasSelectedPanel {
  kind: AtlasPanelKind; id: string; measure_ids: string[]; card_groups: AtlasCardGroup[];
  compact_groups: AtlasCompactGroup[]; compact_group_count: number;
}
export interface AtlasSiteRecord {
  id: string; document_id: string; topic_id: string; channel_id: string; title: string;
  publication: string; publication_basis: string; capture: string; claim_indexes: number[];
  assertion_ids: string[]; comparison_ids: string[]; location_membership_ids: string[];
  geographic_review: string; flagged_issue_review: string;
}
export interface AtlasDocument {
  id: string; title: string; url: string; content_url: string; publication: string; publication_precision: string;
  publication_basis: string; capture: string; channel_id: string; record_ids: string[];
  location_membership_ids: string[]; raw_sha256: string; text_sha256: string; authority_review: string;
}
export interface AtlasAssertion {
  id: string; record_id: string; document_id: string; claim_index: number; kind: 'finding' | 'measure' | 'statement' | 'date';
  text: string; measure_id: string | null; observation_date: AtlasValue; evidence_ids: string[];
  eligibility: AtlasEligibility; review_state: string; value: AtlasValue; quoted_authority_status: string;
}
export interface AtlasEvidence {
  id: string; record_id: string; document_id: string; claim_index: number | null; quote_index: number | null;
  start: number; end: number; page: number | null; quote: string; section: string;
  source_text_sha256: string; quote_sha256: string; offset_basis: 'unicode_code_points_half_open';
}
export interface AtlasComparison {
  id: string; kind: 'contradiction' | 'correction' | 'supersession' | 'corroboration' | 'republication' | 'different_scope' | 'unresolved_association';
  status: 'unresolved' | 'documented'; participant_ids: string[]; participant_labels: Record<string, string>;
  reason: string; scope_review: string; evidence_ids: string[]; eligibility: AtlasEligibility;
  lineage: { from_assertion_id: string; to_assertion_id: string; evidence_ids: string[] }[];
  reviewed_at: string; reviewed_by: string; review_state: string; independence: string | null;
}
export interface AtlasRelationship {
  id: string; category: 'geographic_link' | 'assessment' | 'assessment_update'; kind: string; label: string;
  from_label: string | null; to_label: string | null; from_place_id: string | null; to_place_id: string | null;
  directed: boolean; topic_ids: string[]; basis: string; limit: string; assertion_ids: string[];
  eligibility: AtlasEligibility; parent_id: string | null; metric_panel_id: string; review_state: string;
}
export interface AtlasLocationMembership {
  id: string; record_id: string; document_id: string; claim_index: number | null; area_code: string;
  role: 'occurrence' | 'travel_origin' | 'travel_destination' | 'exposure' | 'context' | 'reporting_scope';
  evidence_ids: string[]; reason: string; review_state: string; eligibility: AtlasEligibility;
}
export interface AtlasPlace {
  id: string; label: string; longitude: number; latitude: number; precision: string; area_codes: string[];
  topic_ids: string[]; record_ids: string[]; relationship_ids: string[]; location_membership_ids: string[];
  geographic_review: string; appearance: string;
}
export interface AtlasSeriesEvidence {
  key: string; id: string; record_id: string; document_id: string; quote: string; section: string;
  start: number; end: number; page: number | null; source_text_sha256: string; quote_sha256: string;
}
export interface AtlasSeriesMember { measure_id: string; evidence_ids: string[]; eligibility: AtlasEligibility }
export interface AtlasSeriesConnection {
  id: string; from_measure_id: string; to_measure_id: string; evidence_ids: string[]; eligibility: AtlasEligibility;
}
export interface AtlasReviewedSeries {
  series_id: string; label: string; operation: 'reported_interval_counts' | 'cumulative_reporting_totals';
  scope: string; reason: string; limitations: string[]; reviewed_by: string; reviewed_at: string;
  review_status: 'source_checked_draft'; comparability_status: 'reviewed_for_reported_counts';
  members: AtlasSeriesMember[]; connections: AtlasSeriesConnection[]; evidence: AtlasSeriesEvidence[];
}
export interface AtlasMetrics {
  contract_version: '0.2.0'; software_version: string; release_status: 'research_preview';
  source_snapshot_sha256: string; records_sha256: string; input_sha256: string; annotations_sha256: string;
  measures: AtlasMeasure[]; panels: AtlasPanel[]; reviewed_series: AtlasReviewedSeries[];
  records: { record_id: string; document_id: string; track_id: string; publication: string; publication_basis: string; capture: string; url: string }[];
  findings: { finding_id: string; text: string; review_status: string; evidence: AtlasMetricEvidence }[];
  series: { context_id: string; context: Record<string, unknown>; measure_ids: string[]; connect_points: false; comparability_status: 'not_established'; reason: string }[];
  conflicts: { conflict_id: string; measure_ids: string[]; resolution: 'unresolved' }[];
  window: { since: string; until: string; basis: 'publication' | 'capture'; inclusive: true; knowledge_cutoff: string | null; mode: string };
  coverage: { records_in_window: number; records_with_measures: number; measure_count: number; finding_count: number; pending_candidate_count: number };
  review: { review_status: string; reviewed_by: string; reviewed_at: string; scope: string; pending_candidate_count: number };
}
export type AtlasChainKind = 'established_transmission' | 'contact_exposure' | 'travel_itinerary' | 'reporting_sequence';
export interface AtlasChainSupport {
  record_ids: string[]; document_ids: string[]; assertion_ids: string[]; evidence_ids: string[]; eligibility: AtlasEligibility;
}
export interface AtlasChainNode extends AtlasChainSupport {
  id: string; key: string; label: string; entity_kind: 'person' | 'case' | 'case_group' | 'contact_group' | 'travel_stop' | 'report';
  place_id: string | null; coordinate_precision: string | null; location_note: string; topic_ids: string[];
  event_date: AtlasValue; date_basis: 'onset' | 'travel' | 'observation' | 'unknown'; date_note: string;
  membership_basis: string; uncertainty: string;
}
export interface AtlasChainEdge extends AtlasChainSupport {
  id: string; key: string; label: string; kind: AtlasChainKind; from_node_id: string; to_node_id: string;
  directed: boolean; direction_basis: 'source_reported' | 'reviewed_publication_order' | 'not_reported';
  certainty: 'established_by_source' | 'reported' | 'uncertain'; basis: string; uncertainty: string;
}
export interface AtlasReviewedChain {
  id: string; key: string; kind: AtlasChainKind; label: string; scope: string; membership_review: string; uncertainty: string;
  reviewed_at: string; reviewed_by: string; review_state: 'source_checked_draft'; nodes: AtlasChainNode[]; edges: AtlasChainEdge[];
}
export interface AtlasSelectedChain extends AtlasReviewedChain { selection_complete: boolean; drawable_edge_ids: string[] }

export interface AtlasDiseaseReview {
  id: string; record_id: string;
  kind: 'single_disease' | 'multiple_diseases' | 'not_disease_specific' | 'unresolved';
  disease_ids: string[]; reason: string; reviewed_at: string; reviewed_by: string;
  review_status: 'source_checked_draft'; evidence_ids: string[]; eligibility: AtlasEligibility;
}
export interface AtlasDiseaseComposition {
  version: '1.0.0'; meaning: 'reporting_attention'; counting_unit: 'report_entry';
  denominator: number; denominator_basis: 'all_selected_report_entries'; partition: true;
  partition_rule: 'single_disease_or_multiple_or_not_specific_or_unclassified'; chart: 'ring' | 'empty';
  reviewed_record_count: number; unclassified_record_count: number;
  categories: {id: string; label: string; kind: string; count: number; proportion: number | null; record_ids: string[]}[];
  unknown_reasons: {not_reviewed: string[]; unresolved: string[]; support_outside_selection: string[]};
  overlapping_diseases: {partition: false; chart: 'bar'; categories: {id: string; label: string; count: number; record_ids: string[]}[]};
}
export type AtlasOneHealthDomain = 'human' | 'animal' | 'environment' | 'food' | 'unknown';
export interface AtlasOneHealthDates {
  observation_date: AtlasValue; period_start: AtlasValue; period_end: AtlasValue;
  date_basis: 'onset' | 'diagnosis' | 'sample_collection' | 'test_result' | 'notification' | 'shipment' | 'reporting_cutoff' | 'unknown';
  period_label: AtlasValue; date_note: string;
}
export interface AtlasOneHealthReview {
  id: string; record_id: string; outcome: 'reviewed' | 'no_relevant_observation' | 'partial' | 'unresolved';
  scope: string; reviewed_sections: string[]; reason: string; pending_items: string[];
  reviewed_at: string; reviewed_by: string; review_state: 'source_checked_draft';
  evidence_ids: string[]; eligibility: AtlasEligibility;
}
export interface AtlasOneHealthNode extends AtlasChainSupport, AtlasOneHealthDates {
  id: string; key: string; record_id: string; label: string; domain: AtlasOneHealthDomain;
  entity_kind: 'person' | 'population' | 'animal_group' | 'sample' | 'food_product' | 'commodity_lot' | 'environmental_setting';
  roles: ('host' | 'reservoir' | 'vector' | 'exposed_population' | 'exposure_source' | 'food_vehicle' | 'commodity' | 'sampled_matrix' | 'ecological_context')[];
  scope: 'episode' | 'surveillance' | 'background'; taxon: AtlasValue; material: AtlasValue; agent: AtlasValue;
  agent_kind: 'pathogen' | 'toxin' | 'other' | 'unknown';
  finding: 'infection_reported' | 'illness_reported' | 'agent_detected' | 'agent_not_detected' | 'exposure_reported' | 'movement_reported' | 'context' | 'unresolved';
  sampling: {sample_unit: AtlasValue; frame: AtlasValue; collection_method: AtlasValue; test_method: AtlasValue};
  place_ids: string[]; location_note: string; uncertainty: string; topic_ids: string[]; measure_ids: string[];
}
export interface AtlasOneHealthRelation extends AtlasChainSupport, AtlasOneHealthDates {
  id: string; key: string; label: string;
  kind: 'cross_species_transmission' | 'exposure' | 'commodity_movement' | 'genomic_association' | 'vector_involvement' | 'environmental_association';
  basis: 'source_reported' | 'source_hypothesis';
  evidence_types: ('epidemiological_investigation' | 'human_testing' | 'animal_testing' | 'environmental_testing' | 'food_testing' | 'genomic_analysis' | 'traceback' | 'experimental_study' | 'ecological_analysis' | 'source_assessment')[];
  directed: boolean; direction_basis: 'source_reported' | 'not_reported'; source_certainty: AtlasValue;
  scope: string; reason: string; uncertainty: string; reviewed_at: string; reviewed_by: string;
  review_state: 'source_checked_draft'; from_node_id: string; to_node_id: string; source_assertion_id: string;
}
export interface AtlasObservationTime {
  kind: 'onset' | 'diagnosis' | 'detection' | 'sample_collection' | 'test_result' | 'notification' | 'shipment' | 'exposure' | 'intervention' | 'reporting_cutoff' | 'unknown';
  extent: "point" | "closed_interval" | "open_interval" | "unknown";
  start: AtlasValue; end: AtlasValue; precision: 'day' | 'month' | 'year' | 'unknown';
  certainty: 'exact' | 'approximately' | 'uncertain' | 'unknown'; label: string; reason: string;
}
export interface AtlasOneHealthPanelReview extends AtlasChainSupport {
  id: string; key: string; record_id: string; reason: string; reviewed_at: string; reviewed_by: string; source_assertion_id: string;
  review_state: 'source_checked_draft'; time: AtlasObservationTime;
}
export interface AtlasOneHealthTiming extends AtlasOneHealthPanelReview { node_id: string }
export interface AtlasOneHealthSamplingAssessment extends AtlasOneHealthPanelReview {
  node_id: string; positive_measure_id: string | null; tested_measure_id: string | null;
  pair_status: 'matched' | 'unresolved' | 'not_applicable';
  unit: AtlasValue; frame: AtlasValue; population: AtlasValue; target: AtlasValue; method: AtlasValue;
  pooling: AtlasValue; clustering: AtlasValue; repeated_sampling: AtlasValue;
  display: 'proportion' | 'counts_only'; proportion: number | null; display_reason: string;
}
export interface AtlasOneHealthContext extends AtlasOneHealthPanelReview {
  label: string; kind: 'measured_covariate' | 'reported_condition' | 'source_hypothesis' | 'reported_intervention' | 'evaluated_effect';
  variable: AtlasValue; method: AtlasValue; place_ids: string[]; linkage_note: string; node_ids: string[]; measure_ids: string[];
}

export type AtlasSelectedOneHealthPanel<T> = T & {contested: boolean; comparison_ids: string[]};
export interface AtlasOneHealthOptions {
  domains?: AtlasOneHealthDomain[]; observation_from?: string; observation_until?: string;
}
export interface AtlasSelectedOneHealth {
  timings: AtlasSelectedOneHealthPanel<AtlasOneHealthTiming>[]; reporting_cutoffs: AtlasSelectedOneHealthPanel<AtlasOneHealthTiming>[]; undated_timings: AtlasSelectedOneHealthPanel<AtlasOneHealthTiming>[];
  sampling_assessments: AtlasSelectedOneHealthPanel<AtlasOneHealthSamplingAssessment>[]; undated_sampling_assessments: AtlasSelectedOneHealthPanel<AtlasOneHealthSamplingAssessment>[];
  contexts: AtlasSelectedOneHealthPanel<AtlasOneHealthContext>[]; undated_contexts: AtlasSelectedOneHealthPanel<AtlasOneHealthContext>[];
  nodes: AtlasOneHealthNode[];
  relations: (AtlasOneHealthRelation & {contested: boolean; comparison_ids: string[]})[];
  reviews: AtlasOneHealthReview[]; undated_nodes: AtlasOneHealthNode[];
  observation_window: {from: string; until: string} | null;
  geographic_projection: 'reviewed_places_only_no_inferred_arcs';
  counting_unit: 'source_observation'; comparability: 'no_cross_domain_aggregation';
  coverage: {selected_records: number; reviewed: number; partial: number; unresolved: number;
    no_relevant_observation: number; not_reviewed: number; support_outside_selection: number;
    pending_record_ids: string[]; observations_by_domain: Partial<Record<AtlasOneHealthDomain, number>>;
    records_by_domain: Partial<Record<AtlasOneHealthDomain, number>>;
    relationships_by_kind: Record<string, number>; relationships_by_basis: Record<string, number>};
}

export interface AtlasSiteBundle {
  one_health_timings: AtlasOneHealthTiming[]; one_health_sampling_assessments: AtlasOneHealthSamplingAssessment[]; one_health_contexts: AtlasOneHealthContext[];
  one_health_reviews: AtlasOneHealthReview[]; one_health_nodes: AtlasOneHealthNode[]; one_health_relations: AtlasOneHealthRelation[];
  diseases: {id: string; label: string}[]; disease_reviews: AtlasDiseaseReview[];
  contract_version: '1.5.0'; software_version: string; release_status: 'research_preview';
  snapshot: { generated_at: string; captured_at: string; next_update_date: string; next_update_status: string;
    schedule_timezone: string; schedule_local_time: string; schedule_activation: string;
    publication_from: string; publication_until: string; capture_from: string; capture_until: string;
    corpus_document_count: number; selected_document_count: number; selected_record_count: number; selected_topic_count: number;
    source_snapshot_sha256: string; records_sha256: string; acquisition_results_sha256: string;
    annotations_sha256: string; metrics_sha256: string; source_text_hashes: Record<string, string>; schedule_source_sha256: string;
    geographic_policy: 'neutral_reporting_locations_no_sovereignty_inference'; replay: 'retrospective_source_dates_not_historical_editorial_state' };
  organizations: { id: string; name: string }[];
  channels: { id: string; name: string; organization_id: string; snapshot_source: string; acquisition_source: string }[];
  areas: { code: string; label: string; code_system: string; meaning: string }[];
  places: AtlasPlace[];
  display_groups: { id: string; place_ids: string[]; longitude: number; latitude: number; meaning: string }[];
  topics: { id: string; label: string; kind: string; disease_group: string | null; place_ids: string[]; record_ids: string[] }[];
  documents: AtlasDocument[]; records: AtlasSiteRecord[]; assertions: AtlasAssertion[]; evidence: AtlasEvidence[];
  comparisons: AtlasComparison[]; location_memberships: AtlasLocationMembership[]; relationships: AtlasRelationship[];
  source_coverage: { id: string; channel_id: string; topic_id: string; document_ids: string[]; record_ids: string[]; meaning: string }[];
  metrics: AtlasMetrics; reviewed_chains: AtlasReviewedChain[]; limitations: string[];
}
export interface AtlasMapRecord {
  id: string; document_id: string; item_index: number; track: string; source: string; title: string; url: string;
  publication: string; date_basis: string; capture: string; conflict: boolean;
  claims: { claim_index: number; text: string; quotes: string[] }[];
}
export interface AtlasMapEndpoint { label: string; lat: number; lon: number; precision: string; track: string }
export interface AtlasMapLink {
  id: string; type: 'movement' | 'shared_event' | 'hypothesis'; label: string; directed: boolean;
  from: AtlasMapEndpoint; to: AtlasMapEndpoint; basis: string; limit: string; support: [string, number][];
}
export interface AtlasMapRelationship {
  id: string; type: string; track: string; from: string; to: string; status: string; basis: string; limit: string;
  support: [string, number][]; updates?: { text: string; support: [string, number][] }[];
  origin_track?: string; destination_track?: string;
}
export interface AtlasMapSnapshot {
  basis: string; corpus_documents: number; mapped_documents: number; input_sha256: string; land_source: string;
  records: AtlasMapRecord[]; map_links: AtlasMapLink[]; relationships: AtlasMapRelationship[];
  map_places?: { id: string; label: string; lat: number; lon: number; precision: string; topic_ids: string[]; eligibility: AtlasEligibility[] }[];
  geographic_review?: { version: '1.0.0'; records_sha256: string; reviewed_at: string; records: { record_id: string; status: 'assessed' | 'no_specific_location' | 'unresolved' | 'retained_review'; reason: string; input_sha256?: string }[] };
  tracks: { id: string; label: string; kind: string; disease_group: string | null; lat?: number | null; lon?: number | null; location_note?: string }[];
}
export interface AtlasSelectionView {
  one_health: AtlasSelectedOneHealth;
  disease_composition: AtlasDiseaseComposition;
  reviewed_chains: AtlasSelectedChain[];
  reviewed_series: AtlasReviewedSeries[];
  numeric_coverage: {record_count: number; records_with_measures: number; records_without_reviewed_measures: number;
    reviewed_series_count: number; reviewed_connection_count: number};
  compact_grouping_version: '1.0.0'; record_ids: string[]; document_ids: string[]; assertion_ids: string[];
  comparison_ids: string[]; superseded_assertion_ids: string[]; relationship_ids: string[]; place_ids: string[];
  location_membership_ids: string[]; panels: AtlasSelectedPanel[];
  source_coverage: { id: string; record_ids: string[]; document_ids: string[] }[];
}
export declare const COMPACT_GROUPING_VERSION: '1.0.0';
export declare function selectView(data: AtlasSiteBundle, from: string, until: string,
  basis?: 'publication' | 'capture', knowledgeCutoff?: string | null, recordSelection?: string[] | null, oneHealthOptions?: AtlasOneHealthOptions | null): AtlasSelectionView;

export interface AtlasFileReference { path: string; sha256: string; bytes: number }
export interface AtlasExportReference {
  export_id: string; bundle_path: string; map_snapshot_path: string; manifest_sha256: string; map_snapshot_sha256: string;
  manifest: AtlasFileReference; structured_data: AtlasFileReference; map_snapshot: AtlasFileReference; selector: AtlasFileReference;
  files: Record<string, AtlasFileReference>; contract_version: string; metric_contract_version: string;
  software_version: string; release_status: string; captured_at: string; publication_window: [string, string];
  integrity: { contract_version: string; records: number; documents: number; assertions: number; comparisons: number; status: 'valid' };
}
export interface AtlasPublicationHandoff {
  handoff_version: '1.0.0'; generated_at: string; cycle: string; timezone: 'Europe/Amsterdam'; weekly_ready: boolean;
  execution_status: 'completed' | 'not_ready';
  jobs: Record<'review' | 'production' | 'inbox', { status: 'missing' | 'invalid' | 'running' | 'completed' | 'partial' | 'blocked';
    receipt: AtlasFileReference | null; completed_at?: string | null; error?: string }>;
  blocking_reasons: string[]; ledger: { records: number; head_hash: string; integrity: 'ok' };
  current_export: AtlasExportReference | null;
  initial_candidate: (AtlasExportReference & { mode: 'initial_publication_candidate'; counts_as_weekly_completion: false }) | null;
  unresolved_issue_ids: string[]; unapplied_decision_ids: string[]; publication_approval: 'not_evaluated';
}
