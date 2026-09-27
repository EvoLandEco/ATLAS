"""Reviewed comparisons of reported observations with explicit evidence support."""
from datetime import date, timedelta
from pathlib import Path
import re
from typing import Literal
from pydantic import Field
from .models import StrictModel
from .util import digest, uid, stamp


class Support(StrictModel):
    record_ids: list[str] = Field(min_length=1)
    rule: Literal['all_supporting_records_in_window'] = 'all_supporting_records_in_window'
    partial: Literal['hide_relationship_keep_visible_assertions'] = 'hide_relationship_keep_visible_assertions'


class MethodEvidence(StrictModel):
    key: str = Field(min_length=1)
    record_id: str
    document_id: str = Field(pattern=r'^doc_[a-f0-9]{24}$')
    quote: str = Field(min_length=1)
    section: str = Field(min_length=1)


class ReviewMember(StrictModel):
    annotation_key: str
    evidence_keys: list[str] = Field(min_length=1)


class ReviewConnection(StrictModel):
    from_key: str
    to_key: str
    evidence_keys: list[str] = Field(default_factory=list)


class SeriesReview(StrictModel):
    series_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    operation: Literal['reported_interval_counts','cumulative_reporting_totals']
    scope: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    reviewed_at: str
    members: list[ReviewMember] = Field(min_length=1)
    connections: list[ReviewConnection]
    evidence: list[MethodEvidence] = Field(min_length=1)


class SeriesEvidence(MethodEvidence):
    id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    page: int | None
    source_text_sha256: str
    quote_sha256: str


class SeriesMember(StrictModel):
    measure_id: str
    evidence_ids: list[str] = Field(min_length=1)
    eligibility: Support


class SeriesConnection(StrictModel):
    id: str
    from_measure_id: str
    to_measure_id: str
    evidence_ids: list[str] = Field(min_length=1)
    eligibility: Support


class ReviewedSeries(StrictModel):
    series_id: str
    label: str
    operation: Literal['reported_interval_counts','cumulative_reporting_totals']
    scope: str
    reason: str
    limitations: list[str]
    reviewed_by: str
    reviewed_at: str
    review_status: Literal['source_checked_draft'] = 'source_checked_draft'
    comparability_status: Literal['reviewed_for_reported_counts'] = 'reviewed_for_reported_counts'
    members: list[SeriesMember]
    connections: list[SeriesConnection]
    evidence: list[SeriesEvidence]


def unique(rows, key):
    result={r[key]:r for r in rows}
    if len(result)!=len(rows):raise ValueError('Duplicate longitudinal '+key)
    return result


def validate_series(series, measures, records, source_hashes=None):
    """Validate identities, periods and complete support for reviewed connections."""
    unique(series,'series_id')
    for s in series:
        ReviewedSeries.model_validate(s);stamp(s['reviewed_at'])
        evidence=unique(s['evidence'],'id');members=unique(s['members'],'measure_id')
        unique(s['connections'],'id')
        for e in evidence.values():
            if e['record_id'] not in records or records[e['record_id']]['document_id']!=e['document_id']:
                raise ValueError('Longitudinal method evidence document differs')
            if e['end']-e['start']!=len(e['quote']) or digest(e['quote'].encode())!=e['quote_sha256']:
                raise ValueError('Longitudinal method evidence span differs')
            if source_hashes is not None and source_hashes.get(e['document_id'])!=e['source_text_sha256']:
                raise ValueError('Longitudinal source hash differs')
        def support(mids,eids):
            if len(eids)!=len(set(eids)) or not set(eids)<=evidence.keys():raise ValueError('Unknown longitudinal evidence')
            rids={evidence[e]['record_id'] for e in eids}
            for mid in mids:
                if mid not in measures:raise ValueError('Unknown longitudinal measure')
                rids.update(r['record_id'] for r in measures[mid]['evidence_references'])
            return rids
        ordered=[]
        for mid,member in members.items():
            expected=support([mid],member['evidence_ids'])
            if set(member['eligibility']['record_ids'])!=expected or len(member['eligibility']['record_ids'])!=len(expected):
                raise ValueError('Longitudinal member support differs')
            m=measures[mid]
            if m['value'] is None or m['value_status']!='reported' or not m['observation_date']:
                raise ValueError('Longitudinal member needs a reported dated value')
            if m['unit']!='people' or m['metric'] not in {'cases','deaths'}:
                raise ValueError('Reported-count review requires case or death counts')
            expected_kind='interval' if s['operation']=='reported_interval_counts' else 'cumulative'
            if m['count_kind']!=expected_kind:raise ValueError('Longitudinal count basis differs')
            if expected_kind=='cumulative' and not m['cumulative_baseline']['value']:
                raise ValueError('Cumulative comparison needs a baseline')
            if expected_kind=='interval':
                start=m['period_start']['value'];end=m['period_end']['value']
                if not start or not end or date.fromisoformat(start)>date.fromisoformat(end):
                    raise ValueError('Interval comparison needs ordered period bounds')
            ordered.append((m['observation_date'],mid))
        if ordered!=sorted(ordered):raise ValueError('Longitudinal members must be date ordered')
        positions={mid:i for i,(_,mid) in enumerate(ordered)}
        pairs=set()
        for edge in s['connections']:
            a,b=edge['from_measure_id'],edge['to_measure_id']
            if a not in members or b not in members or a==b or (a,b) in pairs:raise ValueError('Invalid longitudinal connection')
            pairs.add((a,b));left,right=measures[a],measures[b]
            if left['observation_date']>=right['observation_date']:raise ValueError('Longitudinal dates must increase')
            if positions[b]!=positions[a]+1:
                raise ValueError('Longitudinal connection skips a reviewed observation')
            for field in ['metric','unit','case_class','count_kind','date_basis','qualifier','disease','pathogen','host','geography','population','stratum','origin_authority','acquisition','transmission_role','cumulative_baseline']:
                if left[field]!=right[field]:raise ValueError('Longitudinal scope differs: '+field)
            if left['conflict_set'] or right['conflict_set'] or left['superseded'] or right['superseded']:
                raise ValueError('Longitudinal connection contains an unresolved or superseded value')
            if s['operation']=='reported_interval_counts':
                if date.fromisoformat(left['period_end']['value'])+timedelta(days=1)!=date.fromisoformat(right['period_start']['value']):
                    raise ValueError('Longitudinal interval gap or overlap')
                if date.fromisoformat(left['period_end']['value'])-date.fromisoformat(left['period_start']['value'])!=date.fromisoformat(right['period_end']['value'])-date.fromisoformat(right['period_start']['value']):
                    raise ValueError('Longitudinal interval durations differ')
            required=set(members[a]['evidence_ids'])|set(members[b]['evidence_ids'])
            if not required<=set(edge['evidence_ids']):raise ValueError('Connection omits member method evidence')
            expected=support([a,b],edge['evidence_ids'])
            if set(edge['eligibility']['record_ids'])!=expected or len(edge['eligibility']['record_ids'])!=len(expected):
                raise ValueError('Longitudinal connection support differs')


def prepare_series(reviews, measures, records, source_dir):
    """Resolve review annotations against captured text and measurement identities."""
    by_key=unique(measures,'annotation_key');by_id=unique(measures,'measure_id');texts={};result=[]
    for review in reviews:
        s=review.model_dump(mode='json');stamp(s['reviewed_at'])
        evidence={}
        for ref in s['evidence']:
            if ref['key'] in evidence:raise ValueError('Duplicate method evidence key')
            if ref['record_id'] not in records or records[ref['record_id']]['document_id']!=ref['document_id']:
                raise ValueError('Method evidence does not resolve')
            did=ref['document_id']
            if did not in texts:
                path=source_dir/(did+'.txt')
                if path.stat().st_size>4_000_000:raise ValueError('Method source exceeds the evidence budget')
                texts[did]=path.read_text()
            text=texts[did];words=ref['quote'].split()
            matches=list(re.finditer(r'\s+'.join(re.escape(w) for w in words),text)) if words else []
            if len(matches)!=1:raise ValueError('Method quotation must have one source occurrence')
            m=matches[0];pages=list(re.finditer(r'\[\[PAGE (\d+)\]\]',text[:m.start()]))
            raw=text[m.start():m.end()]
            evidence[ref['key']]=dict(**{**ref,'quote':raw},id=uid('series_evidence',did,ref['record_id'],m.start(),m.end(),ref['section']),
                start=m.start(),end=m.end(),page=int(pages[-1][1]) if pages else None,source_text_sha256=digest(text.encode()),quote_sha256=digest(raw.encode()))
        def refs(keys,mkeys):
            if len(keys)!=len(set(keys)) or not set(keys)<=evidence.keys():raise ValueError('Unknown method evidence key')
            if not set(mkeys)<=by_key.keys():raise ValueError('Unknown reviewed annotation key')
            eids=[evidence[k]['id'] for k in keys]
            rids={evidence[k]['record_id'] for k in keys}|{e['record_id'] for k in mkeys for e in by_key[k]['evidence_references']}
            return eids,Support(record_ids=sorted(rids)).model_dump()
        members=[];member_keys={}
        for member in s['members']:
            key=member['annotation_key']
            if key in member_keys:raise ValueError('Duplicate longitudinal annotation key')
            eids,rule=refs(member['evidence_keys'],[key]);member_keys[key]=member['evidence_keys']
            members.append(dict(measure_id=by_key[key]['measure_id'],evidence_ids=eids,eligibility=rule))
        members.sort(key=lambda m:(by_id[m['measure_id']]['observation_date'] or '',m['measure_id']))
        edges=[]
        for edge in s['connections']:
            a,b=edge['from_key'],edge['to_key']
            if a not in member_keys or b not in member_keys:raise ValueError('Connection endpoint is outside the reviewed series')
            keys=sorted(set(member_keys[a]+member_keys[b]+edge['evidence_keys']));eids,rule=refs(keys,[a,b])
            left,right=by_key[a]['measure_id'],by_key[b]['measure_id']
            edges.append(dict(id=uid('series_connection',s['series_id'],left,right),from_measure_id=left,to_measure_id=right,evidence_ids=eids,eligibility=rule))
        result.append(ReviewedSeries(**{k:s[k] for k in ['series_id','label','operation','scope','reason','limitations','reviewed_by','reviewed_at']},members=members,connections=edges,evidence=list(evidence.values())).model_dump(mode='json'))
    validate_series(result,{m['measure_id']:m for m in measures},records)
    return result
