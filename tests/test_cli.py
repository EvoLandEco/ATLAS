import json
from pathlib import Path
from atlas.cli import execute,parser
from atlas.util import write_json,read_json
from atlas.demo import sample_mention


def test_atlas_command_configuration(monkeypatch):
    monkeypatch.setenv('ATLAS_PROVIDER', 'codex')
    monkeypatch.setenv('ATLAS_MODEL', 'test-model')
    cli = parser()
    assert cli.prog == 'atlas'
    for command in ('run', 'extract'):
        args = cli.parse_args([command])
        assert args.config == Path('config/atlas.yaml')
        assert args.provider == 'codex'
        assert args.model == 'test-model'
    args = cli.parse_args(['extract', '--provider', 'none', '--model', 'explicit-model'])
    assert args.provider == 'none'
    assert args.model == 'explicit-model'


def test_cli_editorial_installation_path(tmp_path, monkeypatch):
    monkeypatch.setattr("atlas.config.utcnow",lambda:"2026-09-25T12:00:00Z")
    state=tmp_path/'state'
    def command(*args):return execute(parser().parse_args(['--state',str(state),*args]))
    assert command('init')['ledger']['records']==0
    assert command('doctor')['source_count']==19
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


def test_metrics_input_budget_arguments():
    args=parser().parse_args(['metrics','--snapshot','snapshot.json','--annotations','annotations.json','--source-dir','sources','--out','out','--since','2026-07-01','--until','2026-10-11','--max-snapshot-bytes','128000000','--max-annotation-bytes','512000000'])
    assert args.max_snapshot_bytes==128_000_000
    assert args.max_annotation_bytes==512_000_000
