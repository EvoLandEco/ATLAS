import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {createRuntime} from './runtime.mjs';

const root=new URL('../../',import.meta.url).pathname;
function python(script,args=[]){const run=spawnSync(process.env.ATLAS_TEST_PYTHON||resolve(root,'.venv/bin/python'),['-c',script,...args],{cwd:root,env:{...process.env,PYTHONPATH:resolve(root,'src')},encoding:'utf8'});assert.equal(run.status,0,run.stderr);return run.stdout;}

test('Python packet → authenticated Worker → decision → ATLAS ledger → receipt',async()=>{
  const dir=mkdtempSync(join(tmpdir(),'atlas-inbox-integration-'));
  const runtime=await createRuntime();
  try{
    python(`from pathlib import Path
import sys
from atlas.store import Store
from atlas.demo import demo_config,add_example,sample_mention
from atlas.inbox import export_inbox
root=Path(sys.argv[1]);store=Store(root/'state');config=demo_config()
add_example(store,config,sample_mention(),at='2026-09-09T06:00:00Z')
export_inbox(store,'atlas',root/'packet',config=config)
store.close()`,[dir]);
    const packet=JSON.parse(readFileSync(join(dir,'packet/inbox.json'))),issue=packet.issues[0];
    assert.equal((await runtime.request('',{authenticated:false})).status,401);
    assert.equal((await runtime.request('')).status,200);
    for(const e of issue.evidence){const response=await runtime.request('api/sync/evidence/'+e.sha256,{service:true,method:'PUT',raw:readFileSync(join(dir,'packet/evidence',e.sha256+'.txt'))});assert.equal(response.status,200,await response.text());}
    const posted=await runtime.request('api/sync/snapshot',{service:true,body:packet});assert.equal(posted.status,200,await posted.text());
    const response=await runtime.request('api/decisions',{body:{decision_id:'integration-decision',snapshot_id:packet.snapshot_id,issue_id:issue.issue_id,revision:issue.revision,action:'accept',event_key:'synthetic-event',rationale:'The captured evidence supports the event assignment.'}});
    assert.equal(response.status,201,await response.text());
    const decisions=await (await runtime.request('api/sync/decisions',{service:true})).json();
    writeFileSync(join(dir,'decisions.json'),JSON.stringify(decisions));
    python(`from pathlib import Path
import sys
from atlas.store import Store
from atlas.inbox import Decisions,import_decisions
from atlas.util import read_json,write_json
root=Path(sys.argv[1]);store=Store(root/'state')
result=import_decisions(store,Decisions.model_validate(read_json(root/'decisions.json')))
assert result.receipts[0].status=='applied'
assert len(store.records('review'))==1
assert import_decisions(store,Decisions.model_validate(read_json(root/'decisions.json')))==result
write_json(root/'receipts.json',result.model_dump())
store.close()`,[dir]);
    const receipts=JSON.parse(readFileSync(join(dir,'receipts.json')));
    const ack=await runtime.request('api/sync/receipts',{service:true,body:receipts});assert.equal(ack.status,200,await ack.text());
    const history=await (await runtime.request('api/history')).json();assert.equal(history.entries[0].receipts[0].status,'applied');
    assert.equal(history.entries[0].decision.reviewer,'tianjian.qin@wur.nl');
    const pending=await (await runtime.request('api/sync/decisions',{service:true})).json();assert.equal(pending.decisions.length,0);
  }finally{await runtime.mf.dispose();rmSync(dir,{recursive:true,force:true});}
});
