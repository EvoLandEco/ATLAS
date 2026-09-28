"""Source-specific One Health observations and explicit evidence relationships."""
from .util import uid


def identity(kind, row, evidence):
    content = {k:v for k,v in row.items() if k not in {'id','reviewed_at','reviewed_by','review_state'}}
    sources = sorted({(evidence[e]['source_text_sha256'], evidence[e]['quote_sha256']) for e in row['evidence_ids']})
    return uid('one_health_'+kind, content, sources)


def support(ids, evidence, records, claim_ids, dependencies=()):
    rows=[evidence[e] for e in ids]
    rids={e['record_id'] for e in rows}
    aids={claim_ids[e['record_id'],e['claim_index']] for e in rows if e['claim_index'] is not None}
    for item in dependencies:
        rids.update(item['eligibility']['record_ids'])
        aids.update(item.get('assertion_ids', []))
        if item.get('kind') in {'finding','statement','date','measure'}:aids.add(item['id'])
    return dict(evidence_ids=sorted(set(ids)),assertion_ids=sorted(aids),record_ids=sorted(rids),
                document_ids=sorted({records[r]['document_id'] for r in rids}),eligibility=dict(record_ids=sorted(rids),rule='all_supporting_records_in_window',partial='hide_relationship_keep_visible_assertions'))


def prepare_one_health(ann, evrefs, evidence, records, keys, assertions, measures):
    claim_ids={(a['record_id'],a['claim_index']):a['id'] for a in assertions.values() if a['kind']=='finding'}
    by_metric={m['annotation_key']:m for m in measures}
    metric_assertions={a['measure_id']:a for a in assertions.values() if a.get('measure_id')}
    nodes=[];refs={};reviews=[];relations=[]
    for review in ann.one_health_reviews:
        ids=evrefs(review.evidence)
        reviews.append(dict(review.model_dump(mode='json',exclude={'evidence'}),id=uid('one_health_review',review.record_id),
            evidence_ids=sorted(set(ids)),eligibility=dict(record_ids=sorted({evidence[e]['record_id'] for e in ids}))))
    for node in ann.one_health_nodes:
        row=node.model_dump(mode='json',exclude={'evidence','measure_keys'})
        mids=sorted({by_metric[k]['measure_id'] for k in node.measure_keys})
        if len(mids)!=len(node.measure_keys):raise ValueError('Duplicate One Health measure')
        ids=evrefs(node.evidence)
        for mid in mids:ids.extend(metric_assertions[mid]['evidence_ids'])
        row.update(support(ids,evidence,records,claim_ids),measure_ids=mids,
            topic_ids=sorted({records[evidence[e]['record_id']]['track'] for e in ids}))
        row['roles']=sorted(row['roles']);row['place_ids']=sorted(row['place_ids'])
        row['id']=identity('node',row,evidence)
        key=(node.record_id,node.key)
        if key in refs:raise ValueError('Duplicate One Health node key')
        refs[key]=row;nodes.append(row)
    for relation in ann.one_health_relations:
        row=relation.model_dump(mode='json',exclude={'from_node','to_node','source_assertion_key','evidence'})
        a=refs[relation.from_node.record_id,relation.from_node.key];b=refs[relation.to_node.record_id,relation.to_node.key]
        assertion=assertions[keys[relation.source_assertion_key]]
        row.update(support(evrefs(relation.evidence),evidence,records,claim_ids,(a,b,assertion)),
            from_node_id=a['id'],to_node_id=b['id'],source_assertion_id=assertion['id'])
        row['assertion_ids']=sorted(set(row['assertion_ids'])|{assertion['id']})
        row['evidence_types']=sorted(row['evidence_types']);row['id']=identity('relation',row,evidence)
        relations.append(row)
    return dict(one_health_reviews=reviews,one_health_nodes=nodes,one_health_relations=relations,
                **prepare_panels(ann,evrefs,evidence,records,keys,assertions,measures,nodes))


def validate_one_health(data, ix):
    nodes=data.get('one_health_nodes',[]);relations=data.get('one_health_relations',[]);reviews=data.get('one_health_reviews',[])
    claim_ids={(a['record_id'],a['claim_index']):a['id'] for a in ix['assertions'].values() if a['kind']=='finding'}
    measures={m['measure_id']:m for m in data['metrics']['measures']}
    metric_assertions={a['measure_id']:a for a in ix['assertions'].values() if a['measure_id']}
    seen=set();node_keys=set();review_records=set();node_index={n['id']:n for n in nodes}
    reviewed={r['record_id']:r for r in reviews};relation_keys=set();pairs=set()
    def unique(ident):
        if ident in seen:raise ValueError('Duplicate One Health identity')
        seen.add(ident)
    def require(name,ids):
        if len(ids)!=len(set(ids)) or not set(ids)<=ix[name].keys():raise ValueError('Invalid One Health '+name+' reference')
    def checked_support(row,dependencies=()):
        require('evidence',row['evidence_ids'])
        if any(not ix['evidence'][e]['quote'].strip() for e in row['evidence_ids']):raise ValueError('One Health evidence cannot be empty')
        expected=support(row['evidence_ids'],ix['evidence'],ix['records'],claim_ids,dependencies)
        expected['assertion_ids']=sorted(set(expected['assertion_ids'])|{d['id'] for d in dependencies if d['id'] in ix['assertions']})
        for field in ['record_ids','document_ids','assertion_ids']:
            if row[field]!=expected[field]:raise ValueError('One Health support differs from evidence and dependencies')
        if row['eligibility']['record_ids']!=expected['eligibility']['record_ids']:raise ValueError('One Health temporal support differs')
    for review in reviews:
        unique(review['id']);require('records',[review['record_id']]);require('evidence',review['evidence_ids'])
        rids=sorted({ix['evidence'][e]['record_id'] for e in review['evidence_ids']})
        if review['record_id'] in review_records or review['record_id'] not in rids:raise ValueError('One Health review record differs')
        review_records.add(review['record_id'])
        if review['id']!=uid('one_health_review',review['record_id']) or review['eligibility']['record_ids']!=rids:
            raise ValueError('One Health review support differs')
    for node in nodes:
        unique(node['id']);checked_support(node);require('places',node['place_ids'])
        key=node['record_id'],node['key']
        if key in node_keys:raise ValueError('Duplicate One Health source node')
        node_keys.add(key)
        review=reviewed.get(node['record_id'])
        if not review or review['outcome']=='no_relevant_observation':raise ValueError('One Health observation needs a compatible review')
        if node['record_id'] not in node['record_ids']:raise ValueError('One Health node lacks its source')
        if node['id']!=identity('node',node,ix['evidence']):raise ValueError('One Health node content ID differs')
        if node['topic_ids']!=sorted({ix['records'][r]['topic_id'] for r in node['record_ids']}):raise ValueError('One Health topics differ')
        if len(node['measure_ids'])!=len(set(node['measure_ids'])):raise ValueError('Duplicate One Health measurement')
        for mid in node['measure_ids']:
            if mid not in measures or measures[mid]['source_reference']['record_id']!=node['record_id']:
                raise ValueError('One Health measurement source differs')
            assertion=metric_assertions[mid]
            if not set(assertion['evidence_ids'])<=set(node['evidence_ids']):raise ValueError('One Health measure evidence omitted')
        for pid in node['place_ids']:
            p=ix['places'][pid]
            memberships=[ix['location_memberships'][m] for m in p['location_membership_ids'] if ix['location_memberships'][m]['record_id']==node['record_id']]
            geo=[ix['evidence'][e] for m in memberships for e in m['evidence_ids']]
            if not any(a['document_id']==b['document_id'] and max(a['start'],b['start'])<min(a['end'],b['end'])
                       for a in geo for b in (ix['evidence'][e] for e in node['evidence_ids'])):
                raise ValueError('One Health place lacks node-specific geographic evidence')
    for relation in relations:
        unique(relation['id']);require('assertions',[relation['source_assertion_id']])
        a=node_index.get(relation['from_node_id']);b=node_index.get(relation['to_node_id'])
        if not a or not b or a['id']==b['id']:raise ValueError('Invalid One Health endpoints')
        assertion=ix['assertions'][relation['source_assertion_id']]
        checked_support(relation,(a,b,assertion))
        if relation['id']!=identity('relation',relation,ix['evidence']):raise ValueError('One Health relation content ID differs')
        key=relation['source_assertion_id'],relation['key']
        pair=(a['id'],b['id']) if relation['directed'] else tuple(sorted((a['id'],b['id'])))
        proposition=pair,relation['kind'],relation['source_assertion_id']
        if key in relation_keys or proposition in pairs:raise ValueError('Duplicate One Health proposition')
        relation_keys.add(key);pairs.add(proposition)
        if assertion['kind'] not in {'finding','statement'}:raise ValueError('One Health relation needs a source proposition')
        if 'background' in {a['scope'],b['scope']}:raise ValueError('Background cannot supply an episode relation')
        kind=relation['kind']
        if kind=='cross_species_transmission':
            if any(n['domain'] not in {'human','animal'} or n['agent_kind']!='pathogen' or 'host' not in n['roles'] or not n['taxon']['value'] for n in (a,b)):
                raise ValueError('Cross-species transmission needs identified pathogen hosts')
            if a['taxon']['value'].casefold()==b['taxon']['value'].casefold():raise ValueError('Cross-species hosts must differ')
            if any(n['finding']=='agent_not_detected' for n in (a,b)):raise ValueError('Negative detection does not establish transmission')
        if kind=='vector_involvement' and not any('vector' in n['roles'] for n in (a,b)):
            raise ValueError('Vector involvement requires a reviewed vector')
        if kind=='environmental_association' and not any(n['domain']=='environment' for n in (a,b)):
            raise ValueError('Environmental association requires an environmental endpoint')
        if kind=='genomic_association' and any(n['finding']!='agent_detected' for n in (a,b)):
            raise ValueError('Genomic association requires detected isolate evidence')
        if kind=='commodity_movement' and any(n['entity_kind'] not in {'commodity_lot','food_product'} for n in (a,b)):
            raise ValueError('Commodity movement requires identified products or lots')


    panel_keys=set()
    for field,kind in [('one_health_timings','timing'),('one_health_sampling_assessments','sampling'),('one_health_contexts','context')]:
        for row in data.get(field,[]):
            unique(row['id']);require('records',[row['record_id']])
            key=(kind,row['record_id'],row['key'])
            if key in panel_keys:raise ValueError('Duplicate panel review key')
            panel_keys.add(key)
            nids=row['node_ids'] if kind=='context' else [row['node_id']]
            if len(nids)!=len(set(nids)) or any(n not in node_index for n in nids):raise ValueError('Invalid panel observation reference')
            dependencies=[node_index[n] for n in nids]
            if any(n['record_id']!=row['record_id'] for n in dependencies):raise ValueError('Panel observation source differs')
            mids=row['measure_ids'] if kind=='context' else [row[k] for k in ['positive_measure_id','tested_measure_id'] if row[k]] if kind=='sampling' else []
            if len(mids)!=len(set(mids)) or any(mid not in measures for mid in mids):raise ValueError('Invalid panel measurement reference')
            if any(measures[mid]['source_reference']['record_id']!=row['record_id'] for mid in mids):raise ValueError('Panel measurement source differs')
            dependencies.extend(metric_assertions[mid] for mid in mids)
            require('assertions',[row['source_assertion_id']]);proposition=ix['assertions'][row['source_assertion_id']]
            if proposition['record_id']!=row['record_id'] or proposition['kind'] not in {'finding','statement','date'}:raise ValueError('Panel source proposition differs')
            dependencies.append(proposition);checked_support(row,dependencies)
            if row['record_id'] not in {ix['evidence'][e]['record_id'] for e in row['evidence_ids']}:raise ValueError('Panel lacks its own source evidence')
            if any(not set(metric_assertions[mid]['evidence_ids'])<=set(row['evidence_ids']) for mid in mids):raise ValueError('Panel lacks measurement evidence')
            if row['id']!=identity(kind,row,ix['evidence']):raise ValueError('Panel content identity differs')
            if kind=='sampling':
                expected=sampling_display(row,measures)
                if (row['display'],row['proportion'],row['display_reason'])!=expected:raise ValueError('Sampling display differs from reviewed counts')
            if kind=='context':
                require('places',row['place_ids'])
                if row['kind'] in {'measured_covariate','evaluated_effect'} and (not mids or row['variable']['value'] is None or row['method']['value'] is None):
                    raise ValueError('Measured context and effects require measures, variable and method')
                for pid in row['place_ids']:
                    memberships=[ix['location_memberships'][m] for m in ix['places'][pid]['location_membership_ids'] if ix['location_memberships'][m]['record_id']==row['record_id']]
                    geographic=[ix['evidence'][e] for m in memberships for e in m['evidence_ids']]
                    if not any(a['document_id']==b['document_id'] and max(a['start'],b['start'])<min(a['end'],b['end']) for a in geographic for b in (ix['evidence'][e] for e in row['evidence_ids'])):
                        raise ValueError('Context place lacks its own geographic evidence')


def sampling_display(row, measures):
    positive=measures.get(row['positive_measure_id']);tested=measures.get(row['tested_measure_id'])
    for measure,kind in [(positive,'positive_samples'),(tested,'samples_tested')]:
        if measure and measure['metric']!=kind:raise ValueError('Sampling measure has a different outcome')
        if measure and measure['value'] is not None and measure['value']<0:raise ValueError('Sampling counts cannot be negative')
    if row['pair_status']!='matched':return 'counts_only',None,'The tested and positive quantities have no completed scope match.'
    if not positive or not tested:raise ValueError('Matched sampling requires both count references')
    if any(row[k]['value'] is None for k in ['unit','frame','population','target']):
        raise ValueError('Matched sampling requires a defined unit, frame, population and target')
    if positive['unit']!=tested['unit'] or positive['unit']=='unknown':raise ValueError('Sampling counting units differ')
    p,t=positive['value'],tested['value']
    if p is None or t is None:return 'counts_only',None,'A bound count is not reported.'
    if p>t:raise ValueError('Positive samples exceed tested samples')
    if positive['denominator'] is not None and positive['denominator']!=t:raise ValueError('Sampling denominator differs from its bound count')
    if t==0:return 'counts_only',None,'The reported tested count is zero.'
    return 'proportion',p/t,'Fraction positive among the explicitly matched tested units; no population prevalence or confidence interval is inferred.'


def prepare_panels(ann,evrefs,evidence,records,keys,assertions,measures,nodes):
    by_node={(n['record_id'],n['key']):n for n in nodes};by_measure={m['annotation_key']:m for m in measures}
    metric_assertions={a['measure_id']:a for a in assertions.values() if a.get('measure_id')}
    claim_ids={(a['record_id'],a['claim_index']):a['id'] for a in assertions.values() if a['kind']=='finding'}
    measure_index={m['measure_id']:m for m in measures}
    result={}
    for field,kind in [('one_health_timings','timing'),('one_health_sampling_assessments','sampling'),('one_health_contexts','context')]:
        rows=[]
        for item in getattr(ann,field):
            row=item.model_dump(mode='json',exclude={'evidence','node','node_refs','measure_keys','positive_measure_key','tested_measure_key','source_assertion_key'})
            refs=item.node_refs if kind=='context' else [item.node]
            dependencies=[by_node[(n.record_id,n.key)] for n in refs]
            if any(n['record_id']!=item.record_id for n in dependencies):raise ValueError('Panel observation belongs to a different entry')
            if kind=='context':row['node_ids']=sorted({n['id'] for n in dependencies})
            else:row['node_id']=dependencies[0]['id']
            mids=[]
            if kind=='sampling':
                for role in ['positive','tested']:
                    key=getattr(item,role+'_measure_key');mid=by_measure[key]['measure_id'] if key else None;row[role+'_measure_id']=mid
                    if mid:mids.append(mid)
                row['display'],row['proportion'],row['display_reason']=sampling_display(row,measure_index)
            elif kind=='context':
                mids=[by_measure[key]['measure_id'] for key in item.measure_keys];row['measure_ids']=sorted(set(mids))
            if len(mids)!=len(set(mids)):raise ValueError('Duplicate panel measure')
            proposition=assertions[keys[item.source_assertion_key]];row['source_assertion_id']=proposition['id'];dependencies.append(proposition)
            dependencies.extend(metric_assertions[mid] for mid in mids)
            ids=evrefs(item.evidence)
            for mid in mids:ids.extend(metric_assertions[mid]['evidence_ids'])
            row.update(support(ids,evidence,records,claim_ids,dependencies))
            row['id']=identity(kind,row,evidence);rows.append(row)
        result[field]=rows
    return result
