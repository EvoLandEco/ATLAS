import type {AtlasSiteBundle, AtlasMeasure, AtlasReviewedSeries, AtlasSelectionView, AtlasOneHealthOptions, AtlasFileReference, AtlasMapSnapshot} from './atlas.js';
export type AtlasBrowserMeasure = Pick<AtlasMeasure, 'measure_id'|'context_id'|'label'|'metric'|'value'|'value_status'|'unit'|'qualifier'|'observation_date'|'priority'|'source_id'|'track_id'|'superseded'|'conflict_set'|'geography'|'disease'|'count_kind'|'period_label'|'source_date_warning'|'publication'> & {
  source_record_id: string; evidence_record_ids: string[]; compact_figure_id: number | null;
};
export type AtlasBrowserSeries = Omit<AtlasReviewedSeries, 'evidence'> & {evidence_ids: string[]};
export type AtlasBrowserData = Pick<AtlasSiteBundle, 'contract_version'|'snapshot'|'report_assessments'|'reviewed_chains'|'places'|'display_groups'|'channels'|'organizations'|'documents'|'areas'|'diseases'|'source_coverage'|'one_health_reviews'|'one_health_nodes'|'one_health_relations'|'one_health_timings'|'one_health_sampling_assessments'|'one_health_contexts'> & {
  records: Pick<AtlasSiteBundle['records'][number], 'id'|'document_id'|'topic_id'|'channel_id'|'capture'|'publication'|'location_membership_ids'>[];
  topics: Pick<AtlasSiteBundle['topics'][number], 'id'|'label'|'place_ids'>[];
  assertions: Pick<AtlasSiteBundle['assertions'][number], 'id'|'record_id'|'measure_id'|'eligibility'>[];
  comparisons: Pick<AtlasSiteBundle['comparisons'][number], 'id'|'kind'|'status'|'participant_ids'|'lineage'|'eligibility'>[];
  relationships: Pick<AtlasSiteBundle['relationships'][number], 'id'|'from_place_id'|'to_place_id'|'eligibility'>[];
  location_memberships: Pick<AtlasSiteBundle['location_memberships'][number], 'id'|'record_id'|'area_code'|'role'|'eligibility'>[];
  disease_reviews: Pick<AtlasSiteBundle['disease_reviews'][number], 'record_id'|'disease_ids'|'kind'|'eligibility'>[];
  metrics: Pick<AtlasSiteBundle['metrics'], 'contract_version'|'coverage'> & {
    measures: AtlasBrowserMeasure[]; reviewed_series: AtlasBrowserSeries[];
    panels: Pick<AtlasSiteBundle['metrics']['panels'][number], 'kind'|'id'|'measure_ids'>[];
    series: Pick<AtlasSiteBundle['metrics']['series'][number], 'context_id'|'measure_ids'>[];
  };
};
export interface AtlasBrowserCore {
  transport_version: '0.4.0'; source_export_id: string;
  metadata: Pick<AtlasSiteBundle, 'contract_version'|'snapshot'|'reviewed_chains'> & {metrics: Pick<AtlasSiteBundle['metrics'],'contract_version'|'coverage'>};
  strings: string[]; eligibility_record_sets: number[][];
  tables: Record<string, {columns: string[]; encoding: ('string'|'strings'|'eligibility'|'json')[]; rows: unknown[][]}>;
}
export type AtlasBrowserSelection = Omit<AtlasSelectionView,'reviewed_series'> & {reviewed_series: AtlasBrowserSeries[]};
export type AtlasBrowserSelector = (from: string, until: string, basis?: 'publication'|'capture', knowledgeCutoff?: string|null, recordSelection?: string[]|null, oneHealthOptions?: AtlasOneHealthOptions|null) => AtlasBrowserSelection;
export type AtlasBrowserMap = Pick<AtlasMapSnapshot,'tracks'|'map_links'|'relationships'> & {transport_version:'0.4.0'; source_export_id:string; records: Omit<AtlasMapSnapshot['records'][number],'claims'>[]};
export interface AtlasBrowserManifest {
  transport_version: '0.4.0'; source_export_id: string;
  source: {manifest: AtlasFileReference; site: AtlasFileReference; map: AtlasFileReference; metrics_sha256: string; site_contract_version: string; selector: AtlasFileReference};
  core: string; map_core: string; detail_index: string; selector: string;
  assets: Record<string, {sha256: string; bytes: number; kind: string}>;
  partitions: {path: string; owner: string; rows: number}[];
  reconstruction: {metadata: {site: Record<string,unknown>; map: Record<string,unknown>}; collections: Record<string,number>};
}
export interface AtlasBrowserDetailRow {collection: string; ordinal: number; id: string|null; value: unknown}
export interface AtlasBrowserDetailPartition {transport_version:'0.4.0'; source_export_id:string; owner:string; rows:AtlasBrowserDetailRow[]}
/** Entries identify a single entity, not a recursively followed dependency graph. */
export interface AtlasBrowserDetailIndex {transport_version:'0.4.0'; source_export_id:string; partitions:string[]; collections:Record<string,[string|null,number][]>}
export declare function decodeBrowserCore(core: AtlasBrowserCore, exportId: string): AtlasBrowserData;
export declare function prepareBrowserView(core: AtlasBrowserCore, exportId: string): {data: AtlasBrowserData; select: AtlasBrowserSelector};
export declare function hydrateBrowserView(view: AtlasBrowserSelection, seriesById: Map<string,AtlasReviewedSeries>): AtlasSelectionView;
export declare const BROWSER_TRANSPORT_VERSION: '0.4.0';
