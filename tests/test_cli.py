import json
from pathlib import Path
from epiweekly.cli import execute,parser
from epiweekly.util import write_json,read_json
from epiweekly.demo import sample_mention


def test_cli_editorial_installation_path(tmp_path, monkeypatch):
    monkeypatch.setattr("epiweekly.config.utcnow",lambda:"2026-09-25T12:00:00Z")
    state=tmp_path/'state'
    def command(*args):return execute(parser().parse_args(['--state',str(state),*args]))
    assert command('init')['ledger']['records']==0
    assert command('doctor')['source_count']==7
    doc=read_json(Path('examples/import/document.json'));m=sample_mention(12)
    doc['published_at']='2026-09-18'
    path=tmp_path/'document.json';write_json(path,doc)
    did=command('import-document',str(path))['document_id']
    extraction=tmp_path/'extraction.json';write_json(extraction,{'outcome':'extracted','mentions':[m]})
    cid=command('import-extraction',did,str(extraction),'--editor','Test editor')['candidate_ids'][0]
    assert command('review-export')['pending']==1
    decisions=tmp_path/'decisions.json';write_json(decisions,[{'candidate_id':cid,'action':'accept','event_key':'synthetic-test',
                'reviewer':'Test editor','rationale':'Synthetic installation acceptance.'}])
    assert command('review-apply',str(decisions))['review_ids']
    result=command('seal')
    assert Path(result['bundle'],'dataset.zip').exists()
    assert command('verify','--bundle',result['bundle'])['valid']
    approval=tmp_path/'approval.json'
    command('approve',result['bundle'],'--editor','Test editor','--note','Synthetic approval.','--out',str(approval))
    assert command('verify-approval',result['bundle'],str(approval))['approved']
    assert command('verify')['integrity']=='ok'
    schemas=tmp_path/'schemas';command('schemas','--out',str(schemas))
    assert (schemas/'report.schema.json').exists()
