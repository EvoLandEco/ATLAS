import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from epiweekly import codex, extraction
from epiweekly.cli import parser
from epiweekly.models import Extraction
from epiweekly.sources import save_document


@pytest.mark.parametrize('failure', [None, 'exit', 'timeout', 'incomplete', 'invalid', 'oversized'])
def test_codex_process_contract(monkeypatch, failure):
    monkeypatch.setattr(codex.shutil, 'which', lambda name:'/usr/bin/codex')
    monkeypatch.setenv('OPENAI_API_KEY','secret')
    monkeypatch.setenv('CODEX_API_KEY','secret')
    def run(args, **kwargs):
        assert args[:2]==['/usr/bin/codex','exec']
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
