import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from atlas import codex, extraction
from atlas.cli import parser
from atlas.models import Extraction
from atlas.sources import save_document


@pytest.mark.parametrize('failure', [None, 'exit', 'timeout', 'incomplete', 'invalid', 'oversized'])
def test_codex_process_contract(monkeypatch, failure):
    monkeypatch.setattr(codex.shutil, 'which', lambda name:'/usr/bin/codex')
    monkeypatch.setenv('OPENAI_API_KEY','secret')
    monkeypatch.setenv('CODEX_API_KEY','secret')
    def run(args, **kwargs):
        assert args[:2]==['/usr/bin/codex','exec']
        assert Path(args[args.index('--output-schema')+1]).is_absolute()
        assert '--ignore-user-config' in args and '--ephemeral' in args
        assert 'forced_login_method="chatgpt"' in args
        assert args[args.index('--sandbox')+1]=='read-only'
        assert not {'OPENAI_API_KEY','CODEX_API_KEY'} & kwargs['env'].keys()
        assert 'shell_tool' in args and 'plugins' in args and 'apps' in args
        assert json.loads(kwargs['input'])['captured_source_text']=='source'
        if failure=='timeout':raise subprocess.TimeoutExpired(args, 1)
        output=Path(args[args.index('--output-last-message')+1])
        output.write_text('x'*2000 if failure=='oversized' else '{}' if failure=='invalid' else
                          json.dumps({'outcome':'no_relevant_content','mentions':[],'notes':[]}))
        kwargs['stdout'].write(json.dumps({'type':'turn.failed' if failure=='incomplete' else 'turn.completed','usage':{'output_tokens':20}})+'\n')
        return SimpleNamespace(returncode=1 if failure=='exit' else 0)
    monkeypatch.setattr(codex.subprocess,'run',run)
    agent=codex.CodexExtractor('fixture',1000,2)
    if failure:
        with pytest.raises(ValueError):agent.extract('source',{'title':'Doc','published_at':None,'url':'https://example.org'})
    else:
        result,receipt=agent.extract('source',{'title':'Doc','published_at':None,'url':'https://example.org'})
        assert result.outcome=='no_relevant_content'
        assert receipt['provider']=='codex' and receipt['authentication']=='chatgpt'
        assert receipt['usage']==[{'output_tokens':20}]


def test_codex_provider_budget_cache_and_review(store, config, monkeypatch):
    calls=[]
    class Agent:
        def __init__(self,*args):pass
        def close(self):pass
        def extract(self,*args):
            calls.append(1)
            return Extraction(outcome='no_relevant_content'),{'provider':'codex'}
    monkeypatch.setattr(extraction,'CodexExtractor',Agent)
    monkeypatch.setattr(extraction,'OpenAIExtractor',Agent)
    config['limits']['max_model_calls']=1
    for i in range(2):
        save_document(store,config['sources'][0],text='Source '+str(i),raw=b'text',
                      url=f'https://example.org/{i}',content_url=f'https://example.org/{i}',
                      title='Document',at='2026-09-25T00:00:00Z')
    first=extraction.extract_pending(store,config,'codex','fixture')
    assert first['calls']==1 and first['queued_chunks']==1
    assert extraction.extract_pending(store,config,'codex','fixture')['calls']==1
    assert extraction.extract_pending(store,config,'codex','fixture')['calls']==0
    assert extraction.extract_pending(store,config,'openai','fixture')['calls']==1
    assert not store.records('review')
    for command in ['run','extract']:
        assert parser().parse_args([command,'--provider','codex']).provider=='codex'


def test_missing_codex_is_actionable(monkeypatch):
    monkeypatch.setattr(codex.shutil,'which',lambda _:None)
    with pytest.raises(ValueError,match='codex login'):codex.CodexExtractor('',1000)


def test_failed_attempt_retains_diagnostics_and_progress(store, config, monkeypatch):
    monkeypatch.setattr(codex.shutil,'which',lambda _: '/usr/bin/codex')
    def run(args,**kwargs):
        assert Path(args[args.index('--output-schema')+1]).is_absolute()
        kwargs['stdout'].write('{"type":"turn.failed","error":{"message":"test failure"}}\n')
        kwargs['stderr'].write('diagnostic failure\n')
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(codex.subprocess,'run',run)
    save_document(store,config['sources'][0],text='Captured source',raw=b'text',url='https://example.org/failure',
                  content_url='https://example.org/failure',title='Document',at='2026-09-25T00:00:00Z')
    result=extraction.extract_pending(store,config,'codex')
    assert result['failed_chunks']==1
    attempts=store.records('extraction_attempt')
    assert [r['payload']['state'] for r in attempts]==['started','failed']
    directory=store.home/attempts[0]['payload']['diagnostics']
    assert 'test failure' in (directory/'events.jsonl').read_text()
    progress=json.loads((store.home/'review/extraction_progress.json').read_text())
    assert progress['state']=='needs_review' and progress['active'] is None
    assert progress['failed_chunks']==1 and 'test failure' in progress['last_error']


def test_relative_diagnostics_paths_and_interruption(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(codex.shutil,'which',lambda _: '/usr/bin/codex')
    def run(args,**kwargs):
        schema=Path(args[args.index('--output-schema')+1])
        assert schema.is_absolute() and schema.is_file()
        kwargs['stderr'].write('Interrupted model call\n')
        raise KeyboardInterrupt()
    monkeypatch.setattr(codex.subprocess,'run',run)
    with pytest.raises(KeyboardInterrupt):
        codex.CodexExtractor('',1000).extract('source',{'title':'Doc','published_at':None,'url':'https://example.org'},Path('diagnostics'))
    assert (tmp_path/'diagnostics/stderr.txt').read_text()=='Interrupted model call\n'


def test_codex_uses_trial_contract_and_prompt(monkeypatch):
    from pydantic import BaseModel
    class Compact(BaseModel):
        summary: str
    monkeypatch.setattr(codex.shutil,'which',lambda _: '/usr/bin/codex')
    def run(args,**kwargs):
        assert args[-1]=='Digest instructions'
        schema=json.loads(Path(args[args.index('--output-schema')+1]).read_text())
        assert 'summary' in schema['properties'] and 'mentions' not in schema['properties']
        Path(args[args.index('--output-last-message')+1]).write_text('{"summary":"Source fact"}')
        kwargs['stdout'].write('{"type":"turn.completed","usage":{}}\n')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(codex.subprocess,'run',run)
    result,_=codex.CodexExtractor('',1000).extract('source',{'title':'Doc','published_at':None,'url':'https://example.org'},contract=Compact,prompt='Digest instructions')
    assert result.summary=='Source fact'
