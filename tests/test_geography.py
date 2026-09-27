import copy
import pytest
from atlas.geography import validate_review, validate_coverage
from atlas.util import digest


def test_geographic_assessment_covers_added_records_and_exact_evidence():
    record = dict(id='r', claims=[dict(claim_index=0, quotes=['A case travelled from Namibia to France.'])])
    review = dict(record_id='r',status='assessed',reason='The source describes return travel.',primary_area_code='FR',
                  locations=[dict(area_code=c,role=role,reason='Reported travel.',claim_index=0,quote_index=0) for c,role in [('NA','travel_origin'),('FR','travel_destination')]],
                  links=[dict(type='movement',from_code='NA',to_code='FR',label='Reported travel',basis='Reported journey.',limit='No infection location supplied.',directed=True,claim_index=0,quote_index=0)],assessments=[])
    validate_review(review,record,record['claims'][0]['quotes'][0])
    bad=copy.deepcopy(review);bad['links'][0]['quote_index']=1
    with pytest.raises(ValueError):validate_review(bad,record,'A case travelled from Namibia to France.')
    snapshot=dict(records=[record],geographic_review=dict(version='1.0.0',records_sha256=digest([record]),records=[]))
    with pytest.raises(ValueError,match='incomplete'):validate_coverage(snapshot)
    snapshot['geographic_review']['records']=[{k:review[k] for k in ['record_id','status','reason']}]
    validate_coverage(snapshot)
    snapshot['records'].append(dict(id='new',claims=[]))
    with pytest.raises(ValueError,match='differs'):validate_coverage(snapshot)


def test_preparation_preserves_records_and_requires_every_assessment(tmp_path):
    from scripts.prepare_geography import prepare
    from atlas.geography import review_fingerprint
    record=dict(id='r',document_id='d',track='topic',claims=[dict(claim_index=0,quotes=['A case returned from Namibia to France.'])])
    snapshot=dict(records=[record],tracks=[dict(id='topic',label='Imported case')],map_links=[],relationships=[])
    annotations=dict(records_sha256=digest(snapshot['records']),locations=[],areas=[],places=[],endpoints=[],limitations=[],reviewed_at="2026-09-25T12:00:00Z",reviewed_by="Source reviewer")
    text=record['claims'][0]['quotes'][0];(tmp_path/'d.txt').write_text(text)
    review=dict(record_id='r',status='assessed',reason='Explicit return journey.',primary_area_code='FR',
        locations=[dict(area_code=c,role=role,reason='Reported journey.',claim_index=0,quote_index=0) for c,role in [('NA','travel_origin'),('FR','travel_destination')]],
        links=[dict(type='movement',from_code='NA',to_code='FR',label='Imported case',basis='Reported return journey.',limit='Acquisition site unknown.',directed=True,claim_index=0,quote_index=0)],assessments=[])
    with pytest.raises(ValueError,match='Missing geographic assessment'):prepare(snapshot,annotations,[],tmp_path)
    rows=[dict(input_sha256=review_fingerprint(record,text),review=review)]
    data,ann=prepare(snapshot,annotations,rows,tmp_path)
    assert data['records']==snapshot['records']
    assert ann['reviewed_at']==annotations['reviewed_at']
    assert ann['reviewed_by']==annotations['reviewed_by']
    assert data['geographic_review']['reviewed_at']!=annotations['reviewed_at']
    assert len(data['map_links'])==1 and len(ann['locations'])==2
    assert data['tracks'][0]['location_note'].startswith('France.')
    assert 'NA' in {a['code'] for a in ann['areas']}
    assert data['map_places'][0]['topic_ids']==['topic']
    validate_coverage(data)
    rows[0]['input_sha256']='stale'
    with pytest.raises(ValueError,match='Stale'):prepare(snapshot,annotations,rows,tmp_path)


def test_reported_travel_origin_can_be_mapped_without_inventing_a_destination():
    record=dict(id='r',claims=[dict(claim_index=0,quotes=['Cases returned from the Maldives; destination countries were not named.'])])
    review=dict(record_id='r',status='assessed',reason='Named travel origin; destination unknown.',primary_area_code='MV',
        locations=[dict(area_code='MV',role='travel_origin',reason='Explicit return journey.',claim_index=0,quote_index=0)],links=[],assessments=[])
    validate_review(review,record,record['claims'][0]['quotes'][0])
    review['locations'][0]['role']='context'
    with pytest.raises(ValueError,match='Primary location'):validate_review(review,record,record['claims'][0]['quotes'][0])
