"""Source-linked measurements for research previews and website integration."""
from __future__ import annotations
import html
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from . import __version__
from .models import StrictModel, Observation, TextValue, DateValue
from .longitudinal import SeriesReview, ReviewedSeries, prepare_series, validate_series
from .semantics import norm
from .util import digest, uid, read_json, write_json, stamp

METRICS_VERSION = '0.2.0'


class ClaimRef(StrictModel):
    record_id: str
    document_id: str = Field(pattern=r'^doc_[a-f0-9]{24}$')
    claim_index: int = Field(ge=0)
    quote_indexes: list[int] = Field(min_length=1)

    @model_validator(mode='after')
    def indexes(self):
        if any(i < 0 for i in self.quote_indexes) or len(set(self.quote_indexes)) != len(self.quote_indexes):
            raise ValueError('Quote indexes must be distinct and nonnegative')
        return self


class CardMeasure(Observation):
    annotation_key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    disease: TextValue
    pathogen: TextValue
    host: TextValue
    geography: TextValue
    acquisition: Literal['imported','local','mixed','unknown'] = 'unknown'
    transmission_role: Literal['index','secondary','import_linked','unknown'] = 'unknown'
    as_of: DateValue = Field(default_factory=DateValue)
    period_label: str = Field(min_length=1)
    denominator_population: TextValue = Field(default_factory=TextValue)
    ratio_basis: Literal['source_reported','not_applicable'] = 'not_applicable'
    source_reference: ClaimRef
    context_references: list[ClaimRef] = Field(default_factory=list)
    numeric_evidence_review: str | None = Field(default=None,min_length=20)
    semantic_note: str = Field(min_length=12)
    priority: int = Field(default=2, ge=1, le=3)
    conflict_set: str | None = None
    cumulative_baseline: TextValue = Field(default_factory=TextValue)
    proposal_candidates: list[str] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    revision_reason: str | None = None

    @model_validator(mode='after')
    def measure_contract(self):
        if self.unit in {'percent','proportion'} and self.ratio_basis != 'source_reported':
            raise ValueError('Ratios must be explicitly reported by the source')
        if self.denominator is not None and self.denominator_population.value is None:
            raise ValueError('A denominator needs its population definition')
        if bool(self.supersedes) != bool(self.revision_reason):
            raise ValueError('A revision needs replaced annotations and an explanation')
        if self.value is not None and self.value_status.value != 'reported':
            raise ValueError('Present values are source-reported assertions; conflicts retain separate assertions')
        return self


class MetricAnnotations(StrictModel):
    contract_version: Literal['0.1.0','0.2.0']
    series_reviews: list[SeriesReview] = Field(default_factory=list)
    records_sha256: str
    review_status: Literal['source_checked_draft']
    reviewed_by: str
    reviewed_at: str
    scope: str
    measures: list[CardMeasure]
    pending_candidate_count: int = Field(ge=0)


def refs(measure):
    return [measure.source_reference, *measure.context_references]


def ref_pair(ref):
    return ref.record_id, ref.claim_index


def export_metrics(snapshot: Path, annotations: Path, source_dir: Path, out: Path,
                   since: str, until: str, basis: str = 'publication', knowledge_cutoff: str | None = None):
    date.fromisoformat(since); date.fromisoformat(until)
    if since > until or basis not in {'publication','capture'}:
        raise ValueError('Use an inclusive ordered reporting window and a supported date basis')
    if snapshot.stat().st_size > 32_000_000 or annotations.stat().st_size > 16_000_000:
        raise ValueError('Metric input exceeds the file budget')
    data=read_json(snapshot); batch=MetricAnnotations.model_validate(read_json(annotations))
    if digest(data['records']) != batch.records_sha256:
        raise ValueError('Annotations belong to a different record snapshot')
    stamp(batch.reviewed_at)
    cutoff=stamp(knowledge_cutoff) if knowledge_cutoff else None
    records={r['id']:r for r in data['records']}
    if len(records)!=len(data['records']):raise ValueError('Duplicate record ID')
    claims={}
    for r in records.values():
        for c in r['claims']:
            key=(r['id'],c['claim_index'])
            if key in claims:raise ValueError('Duplicate claim index')
            claims[key]=c
    sources={}
    def resolve(ref):
        r=records.get(ref.record_id); c=claims.get(ref_pair(ref))
        if not r or not c or r['document_id']!=ref.document_id:
            raise ValueError('Evidence reference does not resolve to its document and claim')
        if ref.document_id not in sources:
            path=source_dir/(ref.document_id+'.txt')
            if path.stat().st_size>4_000_000:raise ValueError('Source text exceeds the evidence budget')
            sources[ref.document_id]=norm(path.read_text())
        try:quotes=[c['quotes'][i] for i in ref.quote_indexes]
        except IndexError:raise ValueError('Quote index does not exist') from None
        if any(not q.strip() or norm(q) not in sources[ref.document_id] for q in quotes):
            raise ValueError('Quotation does not match the captured source text')
        return {'record_id':ref.record_id,'document_id':ref.document_id,'claim_index':ref.claim_index,
                'quote_indexes':ref.quote_indexes,'quotes':quotes,'quote_sha256':[digest(q.encode()) for q in quotes]}
    keys={m.annotation_key:m for m in batch.measures}
    if len(keys)!=len(batch.measures):raise ValueError('Duplicate annotation key')
    def visit(key, path):
        if key in path:raise ValueError('Cyclic revision')
        for previous in keys[key].supersedes:
            if previous not in keys:raise ValueError('Unknown revision target')
            visit(previous,path|{key})
    for key in keys:visit(key,set())
    eligible={rid:r for rid,r in records.items() if since<=r[basis][:10]<=until and
              (cutoff is None or stamp(r['capture'])<=cutoff) and
              (cutoff is None or r['publication'][:10]<=cutoff[:10])}
    measures=[]
    for m in batch.measures:
        evidence=[resolve(ref) for ref in refs(m)]
        joined=' '.join(q for e in evidence for q in e['quotes'])
        if norm(m.evidence.quote) not in norm(joined):raise ValueError('Measurement evidence is outside its referenced quotations')
        # Numeric anchoring is a check after source review, not a semantic decision.
        for value in [m.value,m.denominator]:
            if value is not None:
                token=format(value,'.15g')
                integer, dot, fraction=token.partition('.')
                grouped=r'(?:,|\s+)'.join(f'{int(integer):,}'.split(','))
                number=r'(?:'+re.escape(integer)+'|'+grouped+')'+(r'\.'+fraction if dot else r'(?:\.0+)?')
                words={0:['zero','no'],1:['one','a single'],2:['two'],3:['three'],4:['four'],5:['five'],6:['six'],7:['seven'],8:['eight'],9:['nine'],10:['ten']}
                anchored=re.search(r'(?<![\d.,])'+number+r'(?!\d|[.,]\d)',joined)
                if not anchored and not m.numeric_evidence_review and not any(re.search(r'\b'+w+r'\b',joined.lower()) for w in words.get(value,[])):
                    raise ValueError('Numeric anchor missing: '+m.annotation_key)
        for previous in m.supersedes:
            if previous not in keys or previous==m.annotation_key:raise ValueError('Revision target must exist and differ')
            if keys[previous].supersedes and m.annotation_key in keys[previous].supersedes:raise ValueError('Cyclic revision')
        row=m.model_dump(mode='json');r=records[m.source_reference.record_id]
        row.update(measure_id=uid('metric',m.annotation_key,row),track_id=r['track'],source_id=r['source'],
                   publication=r['publication'],publication_basis=r['date_basis'],capture=r['capture'],source_url=r['url'],
                   evidence_references=evidence,review_status=batch.review_status)
        row['observation_date']=m.as_of.value or m.period_end.value
        row['observation_date_status']='reported' if row['observation_date'] else 'not_reported'
        row['source_date_warning']=bool(row['observation_date'] and row['observation_date']>r['publication'][:10])
        row['superseded']=False
        measures.append(row)
    reviewed_series=prepare_series(batch.series_reviews,measures,records,source_dir)
    measures=[m for m in measures if all(e['record_id'] in eligible for e in m['evidence_references'])]
    selected_series=[]
    for s in reviewed_series:
        s['members']=[m for m in s['members'] if all(r in eligible for r in m['eligibility']['record_ids'])]
        mids={m['measure_id'] for m in s['members']}
        s['connections']=[e for e in s['connections'] if e['from_measure_id'] in mids and e['to_measure_id'] in mids and all(r in eligible for r in e['eligibility']['record_ids'])]
        used={e for m in s['members'] for e in m['evidence_ids']}|{e for c in s['connections'] for e in c['evidence_ids']}
        s['evidence']=[e for e in s['evidence'] if e['id'] in used]
        if s['members']:selected_series.append(s)
    visible_keys={m['annotation_key']:m for m in measures}
    for m in measures:
        for key in m['supersedes']:
            if key in visible_keys:visible_keys[key]['superseded']=True
    # Each point remains an assertion. No totals, rates or changes are calculated.
    def context(m):
        fields=['label','metric','unit','count_kind','case_class','case_definition','disease','pathogen','host','geography',
                'population','stratum','acquisition','transmission_role','date_basis','origin_authority',
                'qualifier','denominator_population','ratio_basis','source_id','cumulative_baseline']
        value={k:m[k] for k in fields}
        if m['count_kind']=='interval':
            a,b=m['period_start']['value'],m['period_end']['value']
            value['interval_days']=(date.fromisoformat(b)-date.fromisoformat(a)).days+1 if a and b else None
            if not a or not b:value['period_label']=m['period_label']
        return value
    groups=defaultdict(list)
    for m in measures:groups[uid('context',context(m))].append(m)
    series=[]
    for gid,items in sorted(groups.items()):
        ordered=sorted(items,key=lambda m:(m['observation_date'] or '9999',m['measure_id']))
        series.append({'context_id':gid,'context':context(items[0]),'measure_ids':[m['measure_id'] for m in ordered],
            'connect_points':False,'comparability_status':'not_established',
            'reason':'Source assertions are shown separately. Case definitions and observation completeness require review before trend analysis.'})
        for m in items:m['context_id']=gid
    claim_entries=[]
    for r in eligible.values():
        for c in r['claims']:
            ref=ClaimRef(record_id=r['id'],document_id=r['document_id'],claim_index=c['claim_index'],quote_indexes=list(range(len(c['quotes']))))
            claim_entries.append({'finding_id':uid('finding',r['id'],c['claim_index']), 'text':c['text'],
                                  'review_status':'extracted_draft','evidence':resolve(ref)})
    measure_support=[];measures_by_claim=defaultdict(list);findings_by_claim=defaultdict(list)
    for index,m in enumerate(measures):
        pairs=[(e['record_id'],e['claim_index']) for e in m['evidence_references']]
        measure_support.append(set(pairs))
        measures_by_claim[pairs[0]].append(index)
    for index,f in enumerate(claim_entries):
        findings_by_claim[f['evidence']['record_id'],f['evidence']['claim_index']].append(index)
    def panel(kind,id,support):
        support_set={tuple(pair) for pair in support}
        candidates=sorted({i for pair in support_set for i in measures_by_claim[pair]})
        allowed=[measures[i] for i in candidates if measure_support[i]<=support_set]
        contexts=defaultdict(list)
        for m in allowed:
            if not m['superseded']:contexts[m['context_id']].append(m)
        cards=[]
        for gid,items in contexts.items():
            dated=[m['observation_date'] for m in items if m['observation_date']]
            latest=max(dated) if dated else None
            current=[m for m in items if m['observation_date']==latest] if latest else items
            cards.append({'context_id':gid,'observation_date':latest,'measure_ids':[m['measure_id'] for m in current],
                          'priority':min(m['priority'] for m in current)})
        cards.sort(key=lambda c:(c['priority'],c['observation_date'] is None,
                    -date.fromisoformat(c['observation_date']).toordinal() if c['observation_date'] else 0,c['context_id']))
        return {'kind':kind,'id':id,'support':support,'measure_ids':[m['measure_id'] for m in allowed],
            'card_groups':cards[:3],
            'finding_ids':[claim_entries[i]['finding_id'] for i in sorted({i for pair in support_set for i in findings_by_claim[pair]})]}
    panels=[panel('record',r['id'],[[r['id'],c['claim_index']] for c in r['claims']]) for r in eligible.values()]
    topic_support=defaultdict(list)
    for r in eligible.values():topic_support[r['track']].extend([r['id'],c['claim_index']] for c in r['claims'])
    for t in data['tracks']:
        support=topic_support[t['id']]
        if support:panels.append(panel('topic',t['id'],support))
    for kind,field in [('geographic_link','map_links'),('assessment','relationships')]:
        for relation in data.get(field,[]):
            if all(rid in eligible for rid,_ in relation['support']):
                panels.append(panel(kind,relation['id'],relation['support']))
                for index,update in enumerate(relation.get('updates',[])):
                    if all(rid in eligible for rid,_ in update['support']):
                        panels.append(panel('assessment_update',relation['id']+':'+str(index),update['support']))
    conflict_sets=defaultdict(list)
    for m in measures:
        if m['conflict_set']:conflict_sets[m['conflict_set']].append(m['measure_id'])
    result={'contract_version':METRICS_VERSION,'software_version':__version__,'release_status':'research_preview',
        'source_snapshot_sha256':digest(snapshot.read_bytes()),'records_sha256':digest(data['records']),
        'input_sha256':data['input_sha256'],'annotations_sha256':digest(annotations.read_bytes()),
        'review':batch.model_dump(exclude={'measures','records_sha256','contract_version','series_reviews'}),
        'window':{'since':since,'until':until,'basis':basis,'inclusive':True,'knowledge_cutoff':cutoff,
                  'mode':'sources_known_at_cutoff' if cutoff else 'retrospective_reporting_window'},
        'records':[{'record_id':r['id'],'document_id':r['document_id'],'track_id':r['track'],'publication':r['publication'],
                    'publication_basis':r['date_basis'],'capture':r['capture'],'url':r['url']} for r in eligible.values()],
        'conflicts':[{'conflict_id':k,'measure_ids':v,'resolution':'unresolved'} for k,v in sorted(conflict_sets.items())],
        'measures':measures,'findings':claim_entries,'series':series,'reviewed_series':selected_series,'panels':panels,
        'coverage':{'records_in_window':len(eligible),'records_with_measures':len({m['source_reference']['record_id'] for m in measures}),
                    'measure_count':len(measures),'finding_count':len(claim_entries),'pending_candidate_count':batch.pending_candidate_count}}
    if out.exists() and any(out.iterdir()):raise ValueError('Metric export target must be empty')
    out.mkdir(parents=True,exist_ok=True)
    MetricsExport.model_validate(result)
    validate_series(selected_series,{m['measure_id']:m for m in measures},eligible)
    write_json(out/'metrics.json',result)
    write_json(out/'metrics.schema.json',MetricsExport.model_json_schema())
    write_json(out/'annotations.schema.json',MetricAnnotations.model_json_schema())
    write_json(out/'source-snapshot.json',data)
    (out/'index.html').write_text(render_preview(result),encoding='utf-8')
    write_json(out/'manifest.json',{'contract_version':METRICS_VERSION,'files':{p.name:digest(p.read_bytes()) for p in sorted(out.iterdir())}})
    return result


class ExportEvidence(ClaimRef):
    quotes: list[str]
    quote_sha256: list[str]


class ExportMeasure(CardMeasure):
    measure_id: str
    track_id: str
    source_id: str
    publication: str
    publication_basis: str
    capture: str
    source_url: str
    evidence_references: list[ExportEvidence]
    review_status: Literal['source_checked_draft']
    observation_date: str | None
    observation_date_status: Literal['reported','not_reported']
    source_date_warning: bool
    superseded: bool
    context_id: str


class ExportRecord(StrictModel):
    record_id: str
    document_id: str
    track_id: str
    publication: str
    publication_basis: str
    capture: str
    url: str


class ExportFinding(StrictModel):
    finding_id: str
    text: str
    review_status: Literal['extracted_draft']
    evidence: ExportEvidence


class CardGroup(StrictModel):
    context_id: str
    observation_date: str | None
    measure_ids: list[str]
    priority: int


class ExportPanel(StrictModel):
    kind: Literal['record','topic','geographic_link','assessment','assessment_update']
    id: str
    support: list[tuple[str,int]]
    measure_ids: list[str]
    card_groups: list[CardGroup]
    finding_ids: list[str]


class ExportSeries(StrictModel):
    context_id: str
    context: dict
    measure_ids: list[str]
    connect_points: Literal[False]
    comparability_status: Literal['not_established']
    reason: str


class ExportConflict(StrictModel):
    conflict_id: str
    measure_ids: list[str]
    resolution: Literal['unresolved']


class ExportWindow(StrictModel):
    since: str
    until: str
    basis: Literal['publication','capture']
    inclusive: Literal[True]
    knowledge_cutoff: str | None
    mode: Literal['sources_known_at_cutoff','retrospective_reporting_window']


class ExportReview(StrictModel):
    review_status: Literal['source_checked_draft']
    reviewed_by: str
    reviewed_at: str
    scope: str
    pending_candidate_count: int


class ExportCoverage(StrictModel):
    records_in_window: int
    records_with_measures: int
    measure_count: int
    finding_count: int
    pending_candidate_count: int


class MetricsExport(StrictModel):
    contract_version: Literal['0.2.0']
    software_version: str
    release_status: Literal['research_preview']
    source_snapshot_sha256: str
    records_sha256: str
    input_sha256: str
    annotations_sha256: str
    review: ExportReview
    window: ExportWindow
    records: list[ExportRecord]
    measures: list[ExportMeasure]
    findings: list[ExportFinding]
    conflicts: list[ExportConflict]
    series: list[ExportSeries]
    reviewed_series: list[ReviewedSeries]
    panels: list[ExportPanel]
    coverage: ExportCoverage


def render_preview(bundle):
    esc=lambda value:html.escape(str(value))
    measures={m['measure_id']:m for m in bundle['measures']}
    findings={f['finding_id']:f for f in bundle['findings']}
    def tile(m):
        value='Not reported' if m['value'] is None else format(m['value'],'.15g')
        label=m['label']+' · '+m['unit']
        flag=' · conflicting source values' if m['conflict_set'] else ''
        return '<div class="tile"><b>'+esc(value)+'</b><span>'+esc(label+flag)+'</span><small>'+esc(m['period_label'])+'</small></div>'
    def evidence(m):
        return ''.join('<p>'+esc(e['record_id']+' · claim '+str(e['claim_index']))+'</p>'+''.join('<blockquote>'+esc(q)+'</blockquote>' for q in e['quotes']) for e in m['evidence_references'])
    sections=[]
    for kind,title in [('topic','Reporting topics'),('geographic_link','Geographic links'),('assessment','Source assessments'),('assessment_update','Later assessments'),('record','Report entries')]:
        cards=[]
        for panel in bundle['panels']:
            if panel['kind']!=kind:continue
            card_ids=list(dict.fromkeys(i for g in panel['card_groups'] for i in g['measure_ids']))
            text=''.join('<p>'+esc(findings[i]['text'])+'</p>' for i in panel['finding_ids'][:2])
            rows=''
            for id in panel['measure_ids']:
                m=measures[id]
                fields={k:m[k] for k in ['count_kind','case_class','case_definition','acquisition','transmission_role','disease','host','geography','population','stratum','period_start','period_end','as_of','date_basis','denominator','denominator_population','source_id','publication','publication_basis','capture','source_date_warning','semantic_note','superseded']}
                rows+='<details id="'+esc(id)+'"><summary>'+esc(m['label']+': '+format(m['value'],'.15g') if m['value'] is not None else m['label']+': missing')+'</summary><pre>'+esc(json.dumps(fields,ensure_ascii=False,indent=2))+'</pre>'+evidence(m)+'<a href="'+esc(m['source_url'])+'">Original source</a></details>'
            cards.append('<article><h3>'+esc(panel['id'])+'</h3><div class="tiles">'+''.join(tile(measures[i]) for i in card_ids)+'</div>'+text+'<details><summary>All measurements and evidence ('+str(len(panel['measure_ids']))+')</summary>'+rows+'</details></article>')
        sections.append('<details'+(' open' if kind in {'topic','geographic_link'} else '')+'><summary><h2>'+title+'</h2></summary>'+''.join(cards)+'</details>')
    charts=[]
    reviewed_ids={m['measure_id'] for series in bundle['reviewed_series'] for m in series['members']}
    for series in bundle['reviewed_series']:
        items=[measures[m['measure_id']] for m in series['members']]
        dates=[date.fromisoformat(m['observation_date']).toordinal() for m in items]
        lo,hi=min(dates),max(dates);top=max(m['value'] for m in items) or 1
        positions={m['measure_id']:(40+(d-lo)/max(1,hi-lo)*500,150-m['value']/top*115) for m,d in zip(items,dates)}
        lines=''.join('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#006c61" stroke-width="2"/>'%(*positions[e['from_measure_id']],*positions[e['to_measure_id']]) for e in series['connections'])
        dots=''.join('<a href="#'+esc(m['measure_id'])+'"><circle cx="%s" cy="%s" r="4"><title>'%positions[m['measure_id']]+esc(m['label']+' '+str(m['value'])+' · '+m['period_label'])+'</title></circle></a>' for m in items)
        method=''.join('<details><summary>'+esc(e['document_id']+' · page '+str(e['page']))+'</summary><blockquote>'+esc(e['quote'])+'</blockquote></details>' for e in series['evidence'])
        charts.append('<article><h3>'+esc(series['label'])+'</h3><p>'+esc(series['scope'])+'</p><svg viewBox="0 0 600 185" role="img" aria-label="'+esc(series['label'])+'"><path d="M40 25V150H550" fill="none" stroke="#536d74"/>'+lines+dots+'<text x="40" y="177">'+esc(date.fromordinal(lo))+'</text><text x="450" y="177">'+esc(date.fromordinal(hi))+'</text><text x="5" y="35">'+esc(top)+'</text><text x="15" y="150">0</text></svg><p>'+esc(series['reason'])+'</p><p>'+esc(' '.join(series['limitations']))+'</p><details><summary>Source methods and definitions</summary>'+method+'</details></article>')
    for group in bundle['series']:
        items=[measures[i] for i in group['measure_ids'] if i not in reviewed_ids and measures[i]['observation_date'] and measures[i]['value'] is not None and not measures[i]['superseded']]
        if len({m['observation_date'] for m in items})<2:continue
        dates=[date.fromisoformat(m['observation_date']).toordinal() for m in items];lo,hi=min(dates),max(dates);top=max(m['value'] for m in items) or 1
        dots=''.join('<circle cx="'+str(40+(d-lo)/(hi-lo)*500)+'" cy="'+str(150-m['value']/top*115)+'" r="5"><title>'+esc(m['label']+' '+str(m['value'])+' · '+m['observation_date']+' · '+m['source_reference']['record_id'])+'</title></circle>' for m,d in zip(items,dates))
        charts.append('<article><h3>'+esc(items[0]['label']+' · '+items[0]['geography']['value']+' · '+items[0]['count_kind'])+'</h3><svg viewBox="0 0 600 185" role="img" aria-label="Unconnected source observations"><path d="M40 25V150H550" fill="none" stroke="#536d74"/>'+dots+'<text x="40" y="177">'+esc(date.fromordinal(lo))+'</text><text x="450" y="177">'+esc(date.fromordinal(hi))+'</text><text x="5" y="35">'+esc(top)+'</text><text x="15" y="150">0</text></svg><p>Observation dates on the horizontal axis; reported values on the vertical axis. Points retain separate source assertions. Comparability for these observations has not been reviewed.</p></article>')
    coverage=bundle['coverage']
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ATLAS metric export preview</title><style>body{font:16px/1.5 system-ui;max-width:1050px;margin:35px auto;padding:0 20px;color:#193c45;background:#f4f7f3}a{color:#006c61}article{background:white;padding:18px;margin:14px 0;border:1px solid #cedbd9;border-radius:8px}.tiles{display:flex;gap:14px;flex-wrap:wrap}.tile{padding:12px;background:#e8f2eb;max-width:260px}.tile b,.tile span,.tile small{display:block}.tile b{font-size:26px}summary{cursor:pointer}summary h2{display:inline}pre{white-space:pre-wrap;overflow-wrap:anywhere}blockquote{border-left:3px solid #cedbd9;padding-left:12px}svg{width:100%;max-width:650px}circle{fill:#006c61}text{font:12px system-ui}h3{overflow-wrap:anywhere}</style><h1>ATLAS epidemiological figures</h1><p>Research preview · source-checked measurements awaiting editorial acceptance.</p><p>'+str(coverage['measure_count'])+' measurements across '+str(coverage['records_with_measures'])+' report entries; qualitative findings for '+str(coverage['records_in_window'])+' entries. '+str(coverage['pending_candidate_count'])+' proposal candidates await review.</p><p><a href="metrics.json">Metric export</a> · <a href="metrics.schema.json">JSON Schema</a> · <a href="manifest.json">Checksums</a></p><details><summary><h2>Source observation plots</h2></summary>'+''.join(charts)+'</details>'+''.join(sections)+'</html>'
