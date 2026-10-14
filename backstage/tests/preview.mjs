import {createServer} from 'node:http';
import {spawnSync} from 'node:child_process';
import {mkdtempSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {createRuntime} from './runtime.mjs';

const origin='http://127.0.0.1:8791', root=new URL('../../',import.meta.url).pathname;
const dir=mkdtempSync(join(tmpdir(),'atlas-inbox-preview-'));
const prepared=spawnSync(process.env.ATLAS_TEST_PYTHON||resolve(root,'.venv/bin/python'),['-c',`from pathlib import Path
import sys
from atlas.store import Store
from atlas.demo import demo_config,add_example,sample_mention
from atlas.inbox import export_inbox,registry_issues,register_supplement,SupplementalPacket
root=Path(sys.argv[1]);store=Store(root/'state');config=demo_config()
add_example(store,config,sample_mention(12),at='2026-10-07T06:00:00Z')
add_example(store,config,sample_mention(4,key='animal',disease='Example animal syndrome',host='pig',metric='affected_holdings',unit='holdings'),at='2026-10-08T06:00:00Z')
e=registry_issues(store)[0].evidence[0];raw=(store.home/'objects'/(e.sha256+'.txt')).read_text()
register_supplement(store,SupplementalPacket.model_validate(dict(inbox_version='1.0.0',sources=[dict(**e.model_dump(),text=raw)],issues=[dict(issue_id='period-review',kind='longitudinal',title='Confirm the reporting period',question='Do the two source totals describe the same observation period?',impact='The observations remain separate until their reporting periods are established.',first_seen=e.captured_at,changed_at=e.captured_at,affected_ids=['example-measurement'],dependencies={'example-measurement':e.sha256},evidence=[e.model_dump()])])),config)
export_inbox(store,'atlas',root/'packet',config=config)
store.close()`,dir],{cwd:root,env:{...process.env,PYTHONPATH:resolve(root,'src')},encoding:'utf8'});
if(prepared.status!==0)throw new Error(prepared.stderr);
const runtime=await createRuntime(origin),packet=JSON.parse(readFileSync(join(dir,'packet/inbox.json')));
for(const issue of packet.issues)for(const e of issue.evidence){const response=await runtime.request('api/sync/evidence/'+e.sha256,{service:true,method:'PUT',raw:readFileSync(join(dir,'packet/evidence',e.sha256+'.txt'))});if(!response.ok)throw new Error(await response.text());}
const posted=await runtime.request('api/sync/snapshot',{service:true,body:packet});if(!posted.ok)throw new Error(await posted.text());
const server=createServer(async(req,res)=>{
  try{const chunks=[];for await(const chunk of req)chunks.push(chunk);const headers={...req.headers,'Cf-Access-Jwt-Assertion':runtime.reviewerToken};delete headers.host;
    const response=await runtime.mf.dispatchFetch(origin+req.url,{method:req.method,headers,body:chunks.length?Buffer.concat(chunks):undefined});
    res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));
  }catch{res.writeHead(500);res.end('Preview failed.');}
});
server.listen(8791,'127.0.0.1',()=>console.log('Synthetic review preview: '+origin+'/atlas/review/'));
async function stop(){server.close();await runtime.mf.dispose();rmSync(dir,{recursive:true,force:true});process.exit(0);}
process.on('SIGINT',stop);process.on('SIGTERM',stop);
