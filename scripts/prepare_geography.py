"""Apply assessed geographic evidence to a snapshot and its export annotations."""
import argparse
import copy
from pathlib import Path
import yaml
from atlas.config import assets
from atlas.geography import validate_review, validate_coverage, REVIEW_VERSION, review_fingerprint
from atlas.util import read_json, write_json, digest, uid, utcnow


def prepare(snapshot, annotations, reviews, source_dir, review_prompt=None):
    data=copy.deepcopy(snapshot); ann=copy.deepcopy(annotations)
    if ann['records_sha256'] != digest(data['records']):
        raise ValueError('Annotations differ from records')
    reference=yaml.safe_load(assets('map_locations.yaml'))
    points=reference['locations']; tracks={t['id']:t for t in data['tracks']}
    existing={l['record_id'] for l in ann['locations']}
    reviewed={r['review']['record_id']:r for r in reviews}
    if len(reviewed)!=len(reviews):raise ValueError('Duplicate assessed record')
    coverage=[]; areas={a['code'] for a in ann['areas']}
    places={p['id']:p for p in ann['places']}
    def place(code, track=None):
        if code not in points:raise ValueError('Missing map reference point: '+code)
        p=points[code]; key='place:'+code+(':'+track if track else ':context')
        if code not in areas:
            ann['areas'].append(dict(code=code,label=p['label'])); areas.add(code)
        if key not in places:
            places[key]=dict(id=key,label=p['label'],longitude=p['longitude'],latitude=p['latitude'],
                precision=reference['precision'],area_codes=[code],topic_ids=[track] if track else [])
        return places[key]
    for record in data['records']:
        rid=record['id']; track=tracks[record['track']]
        if rid in existing:
            coverage.append(dict(record_id=rid,status='retained_review',reason='Retained source geographic assignments and relationship assessments.'))
            continue
        if rid not in reviewed:raise ValueError('Missing geographic assessment: '+rid)
        saved=reviewed[rid]
        source=(source_dir/(record['document_id']+'.txt')).read_text()
        if saved['input_sha256'] != review_fingerprint(record,source,review_prompt):raise ValueError('Stale geographic review: '+rid)
        review=validate_review(saved['review'],record,source)
        coverage.append(dict(record_id=rid,status=review.status,reason=review.reason,input_sha256=saved['input_sha256']))
        for loc in review.locations:
            p=place(loc.area_code,track['id'] if loc.role in {'occurrence','reporting_scope','travel_destination','travel_origin','exposure'} else None)
            ann['locations'].append(dict(record_id=rid,claim_index=loc.claim_index,area_code=loc.area_code,role=loc.role,
                reason=loc.reason,evidence=[dict(record_id=rid,claim_index=loc.claim_index,quote_index=loc.quote_index,section='Geographic scope and relationship assessment')]))
        if review.primary_area_code is not None and 'lat' not in track:
            p=place(review.primary_area_code,track['id'])
            track.update(lat=p['latitude'],lon=p['longitude'],location_note=p['label']+'. '+p['precision'])
        for index,link in enumerate(review.links):
            a=place(link.from_code,track['id'] if review.primary_area_code==link.from_code else None)
            b=place(link.to_code,track['id'] if review.primary_area_code==link.to_code else None)
            key=uid('geographic',rid,index,link.model_dump())
            def endpoint(p):return dict(label=p['label'],lon=p['longitude'],lat=p['latitude'],precision=p['precision'],track=track['id'] if p['topic_ids'] else None)
            support=sorted({link.claim_index}|{loc.claim_index for loc in review.locations if loc.area_code in {link.from_code,link.to_code}})
            data['map_links'].append(dict(id=key,type=link.type,label=link.label,basis=link.basis,limit=link.limit,directed=link.directed,
                support=[[rid,ci] for ci in support],**{'from':endpoint(a),'to':endpoint(b)}))
            ann['endpoints'].append(dict(relationship_id=key,from_place_id=a['id'],to_place_id=b['id']))
        for index,a in enumerate(review.assessments):
            data['relationships'].append(dict(id=uid('assessment',rid,index,a.model_dump()),track=track['id'],type=a.type,status=a.label,
                support=[[rid,a.claim_index]],basis=a.basis,limit=a.limit,**{'from':a.from_label,'to':a.to_label}))
    ann['places']=list(places.values())
    ann['limitations']=[
        'Findings and source relationship assessments are research drafts. Event identity acceptance remains an editorial decision.',
        'Every report entry has a geographic assessment outcome. Broad regional scope, unclear locations and unresolved evidence retain explicit reasons in the map snapshot.',
        'Coordinates are geographic reference points with stated precision. They do not locate individual infections or reconstruct travel routes.',
        'Reviewed measurements and comparisons cover a subset of findings. Geographic assessment does not normalize additional measurements or establish statistical comparability.',
        'Collection gaps and incomplete source access are documented in the coverage report. Publication, capture and observation times retain distinct meanings.'
    ]
    data['geographic_review']=dict(version=REVIEW_VERSION,records_sha256=digest(data['records']),reviewed_at=utcnow(),records=coverage)
    mapped_topics={tid for p in ann['places'] for tid in p['topic_ids']}
    data['mapped_documents']=len({r['document_id'] for r in data['records'] if r['track'] in mapped_topics})
    record_topics={r['id']:r['track'] for r in data['records']}
    data['map_places']=[]
    for p in ann['places']:
        if not p['topic_ids']:continue
        members=[loc for loc in ann['locations'] if loc['area_code'] in p['area_codes'] and record_topics[loc['record_id']] in p['topic_ids']]
        rules=sorted({tuple(sorted({loc['record_id']}|{e['record_id'] for e in loc['evidence']})) for loc in members})
        data['map_places'].append(dict(id=p['id'],label=p['label'],lat=p['latitude'],lon=p['longitude'],precision=p['precision'],topic_ids=p['topic_ids'],
            eligibility=[dict(record_ids=list(ids),rule='all_supporting_records_in_window',partial='hide_relationship_keep_visible_assertions') for ids in rules]))
    data['basis']='Captured report findings with source-assessed geographic scope and relationships. Reporting topics retain separate identities.'
    validate_coverage(data)
    return data,ann


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['snapshot','annotations','reviews','source-dir','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists() and any(a.out.iterdir()):raise ValueError('Output directory must be empty')
    data,ann=prepare(read_json(a.snapshot),read_json(a.annotations),read_json(a.reviews),a.source_dir,(a.reviews.parent/'prompt.md').read_text())
    a.out.mkdir(parents=True,exist_ok=True)
    write_json(a.out/'snapshot.json',data);write_json(a.out/'annotations.json',ann)
    write_json(a.out/'geographic-review.json',data['geographic_review'])
    print(len(data['records']),'assessed entries;',len(data['map_places']),'topic locations;',len(data['map_links']),'geographic links')


if __name__=='__main__':main()
