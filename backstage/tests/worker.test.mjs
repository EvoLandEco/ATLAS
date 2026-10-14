import {test, before} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {generateKeyPair, SignJWT, exportJWK} from 'jose';
import worker, {route, canonical, sha256, makeDecision, identityFromClaims, boundedBody, authenticate} from '../src/worker.mjs';

const origin='https://qtj.me', base='/atlas/review/';
class D1 {
  constructor(){this.db=new DatabaseSync(':memory:');this.db.exec(readFileSync(new URL('../migrations/0001_inbox.sql',import.meta.url),'utf8'));}
  withSession(){return this;}
  prepare(sql){const db=this.db;let args=[];return {bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return {results:db.prepare(sql).all(...args)};},async run(){return db.prepare(sql).run(...args);}};}
  async batch(statements){this.db.exec('BEGIN');try{const results=[];for(const statement of statements)results.push(await statement.run());this.db.exec('COMMIT');return results;}catch(error){this.db.exec('ROLLBACK');throw error;}}
}
class R2 {
  objects=new Map();
  async put(key,bytes,options={}){const body=typeof bytes==='string'?new TextEncoder().encode(bytes):bytes;this.objects.set(key,{body,size:body.byteLength,...options});}
  async head(key){return this.objects.get(key)||null;}
  async get(key){return this.objects.get(key)||null;}
}
function env(){return {DB:new D1(),EVIDENCE:new R2(),ASSETS:{fetch:async()=>new Response('interface')},INBOX_ORIGIN:origin,INBOX_PATH:base,ATLAS_ARCHIVE_ID:'atlas',REVIEWER_EMAILS:'tianjian.qin@wur.nl',ACCESS_ISSUER:'https://atlas-test.cloudflareaccess.com',ACCESS_AUD:'review-app',SYNC_SERVICE_TOKEN_ID:'sync-service'};}
function request(path,body,method=body?'POST':'GET'){return new Request(origin+base+path,{method,headers:body?{'Content-Type':'application/json',Origin:origin,'X-Atlas-Review':'1'}:{},body:body?JSON.stringify(body):undefined});}
const reviewer={service:false,email:'tianjian.qin@wur.nl'}, service={service:true};
test('only ATLAS can frame the inbox and embedding does not bypass sign-in', async()=>{
  const response=await worker.fetch(new Request(origin+base,{headers:{Origin:'https://another.example'}}),env());
  assert.equal(response.status,401);
  assert.equal(response.headers.get('Cache-Control'),'private, no-store');
  assert.equal(response.headers.get('X-Frame-Options'),null);
  assert.match(response.headers.get('Content-Security-Policy'),/frame-ancestors https:\/\/qtj\.me;/);
  assert.doesNotMatch(response.headers.get('Content-Security-Policy'),/another\.example/);
});
async function seed(e){
  const text='The source reports twelve cases.', hash=await sha256(text);
  await e.EVIDENCE.put(`evidence/${hash}.txt`,text,{customMetadata:{sha256:hash}});
  const packet={inbox_version:'1.0.0',archive_id:'atlas',snapshot_id:'a'.repeat(64),sequence:1,generated_at:'2026-10-14T12:00:00Z',ledger_head:'b'.repeat(64),issues:[{
    issue_id:'issue-1',revision:'c'.repeat(64),kind:'registry',title:'A captured finding',question:'Does the evidence establish this event?',impact:'Event identity remains pending.',priority:'normal',first_seen:'2026-10-01T12:00:00Z',changed_at:'2026-10-01T12:00:00Z',candidate_id:'candidate-1',affected_ids:['candidate-1'],dependencies:{'candidate-1':'d'.repeat(64)},context:{validation_errors:[],suggested_matches:[]},evidence:[{document_id:'doc-1',source_id:'source-1',title:'Captured report',url:'https://example.org/report',published_at:'2026-10-01',captured_at:'2026-10-01T12:00:00Z',sha256:hash,bytes:new TextEncoder().encode(text).length,quotes:[text]}]}]};
  const response=await route(request('api/sync/snapshot',packet),e,service);assert.equal(response.status,200);return packet;
}
function input(packet,id='decision-1'){return {decision_id:id,snapshot_id:packet.snapshot_id,issue_id:'issue-1',revision:packet.issues[0].revision,action:'defer',rationale:'The source context requires further review.'};}
async function submit(e,p,id){return (await route(request('api/decisions',input(p,id)),e,reviewer)).json();}
function receipt(decision,status='applied'){return {inbox_version:'1.0.0',archive_id:'atlas',decision_id:decision.decision_id,decision_sha256:'',issue_id:decision.issue_id,revision:decision.revision,status,recorded_at:'2026-10-14T13:00:00Z',ledger_record_ids:['review-1'],validation:'pending',export_id:null,detail:'Applied to ledger; output validation remains pending.'};}

test('permissions distinguish reviewers and synchronization identity',()=>{
  const e=env();assert.deepEqual(identityFromClaims({email:reviewer.email,sub:'human'},e),reviewer);
  assert.deepEqual(identityFromClaims({common_name:'sync-service'},e),service);
  assert.throws(()=>identityFromClaims({email:'outsider@example.org',sub:'other'},e),/access/);
  assert.throws(()=>identityFromClaims({email:reviewer.email},e),/access/);
});
test('authenticated reviewer cannot use producer API; service cannot submit decisions',async()=>{
  const e=env();await assert.rejects(()=>route(request('api/sync/decisions'),e,reviewer),/service identity/);
  await assert.rejects(()=>route(request('api/decisions',{}),e,service),/synchronization API/);
  await assert.rejects(()=>route(request('sign-in'),e,service),/synchronization API/);
  assert.equal((await worker.fetch(request('sign-in'),e)).status,401);
  assert.equal((await route(request('sign-in'),e,reviewer)).status,200);
  const response=await worker.fetch(request(''),{...e,ACCESS_ISSUER:''});assert.equal(response.status,503);assert.match(response.headers.get('Cache-Control'),/no-store/);
});
test('body limit counts streamed bytes without trusting Content-Length',async()=>{
  await assert.rejects(()=>boundedBody(new Request('https://example.org',{method:'POST',body:'too large'}),3),/byte limit/);
});
test('reviewer identity comes from authentication and action fields are enforced',()=>{
  const e=env();assert.throws(()=>makeDecision({...input({snapshot_id:'a'.repeat(64),issues:[{revision:'b'.repeat(64)}]}),reviewer:'forged'},reviewer,e),/Unknown/);
  assert.throws(()=>makeDecision({...input({snapshot_id:'a'.repeat(64),issues:[{revision:'b'.repeat(64)}]}),action:'accept'},reviewer,e),/event key/);
});
test('snapshot evidence must exist, packet publication preserves history',async()=>{
  const e=env(),p=await seed(e);const issues=await (await route(request('api/issues'),e,reviewer)).json();assert.equal(issues.issues.length,1);
  p.snapshot_id='e'.repeat(64);p.sequence=2;p.issues[0].revision='f'.repeat(64);p.issues[0].evidence[0].sha256='0'.repeat(64);
  await assert.rejects(()=>route(request('api/sync/snapshot',p),e,service),/evidence/);
  assert.equal((await e.DB.prepare('SELECT COUNT(*) AS n FROM snapshots').first()).n,1);
});
test('twenty pending issues fit the D1 Free query allowance',async()=>{
  const e=env(),p=await seed(e),prepare=e.DB.prepare.bind(e.DB);let queries=0;
  e.DB.prepare=sql=>{queries++;return prepare(sql);};
  p.snapshot_id='e'.repeat(64);p.sequence=2;
  p.issues=Array.from({length:20},(_,i)=>({...p.issues[0],issue_id:`issue-${i+1}`}));
  assert.equal((await route(request('api/sync/snapshot',p),e,service)).status,200);
  assert.ok(queries<=50,`${queries} database queries exceed the Free allowance`);
  queries=0;
  const list=await (await route(request('api/issues'),e,reviewer)).json();
  assert.equal(list.issues.length,20);assert.ok(queries<=50);
  p.snapshot_id='f'.repeat(64);p.sequence=3;p.issues[0].title='Different content under the same revision';
  await assert.rejects(()=>route(request('api/sync/snapshot',p),e,service),/revision has different content/);
});
test('duplicate submission returns same decision and competing reviewers conflict',async()=>{
  const e=env(),p=await seed(e),first=await submit(e,p);
  const retry=await submit(e,p);assert.deepEqual(retry,first);
  await assert.rejects(()=>submit(e,p,'decision-2'),/changed/);
  assert.equal((await e.DB.prepare('SELECT COUNT(*) AS n FROM decisions').first()).n,1);
});
test('stale snapshot and revision cannot record a decision',async()=>{
  const e=env(),p=await seed(e),old=structuredClone(p);p.snapshot_id='e'.repeat(64);p.sequence=2;p.issues[0].revision='f'.repeat(64);
  await route(request('api/sync/snapshot',p),e,service);
  await assert.rejects(()=>submit(e,old),/changed/);
});
test('write requests require same origin and review header',async()=>{
  const e=env(),p=await seed(e);const r=new Request(origin+base+'api/decisions',{method:'POST',headers:{'Content-Type':'application/json',Origin:'https://another.example'},body:JSON.stringify(input(p))});
  await assert.rejects(()=>route(r,e,reviewer),/reviewer interface/);
});
test('receipts bind exact decisions, retain transitions, and retry safely',async()=>{
  const e=env(),p=await seed(e),decision=await submit(e,p),r=receipt(decision);r.decision_sha256=await sha256(canonical(decision));
  const send=values=>route(request('api/sync/receipts',{inbox_version:'1.0.0',receipts:values}),e,service);
  await assert.rejects(()=>send([{...r,decision_sha256:'0'.repeat(64)}]),/submitted decision/);
  await send([r]);await send([r]);
  const complete={...r,status:'completed',validation:'passed',export_id:'d'.repeat(64),recorded_at:'2026-10-14T14:00:00Z',detail:'Affected export passed validation.'};
  await send([complete]);await send([r,complete]);
  assert.equal((await e.DB.prepare('SELECT COUNT(*) AS n FROM receipts').first()).n,2);
  await assert.rejects(()=>send([{...r,detail:'A different earlier receipt'}]),/transition/);
  const history=await (await route(request('api/history'),e,reviewer)).json();assert.equal(history.entries[0].receipts.length,2);
  assert.equal((await (await route(request('api/sync/decisions'),e,service)).json()).decisions.length,0);
});
test('decision and receipt rows cannot be overwritten or deleted',async()=>{
  const e=env(),p=await seed(e);await submit(e,p);
  assert.throws(()=>e.DB.db.exec('DELETE FROM decisions'),/immutable/);
  assert.throws(()=>e.DB.db.exec("UPDATE issue_versions SET payload='{}'"),/immutable/);
});
test('JWT signature, audience, expiry and authenticated identity are checked',async()=>{
  const e=env(),pair=await generateKeyPair('RS256'),jwk=await exportJWK(pair.publicKey);jwk.kid='test-key';
  const original=globalThis.fetch;globalThis.fetch=async()=>Response.json({keys:[jwk]});
  try{
    const token=await new SignJWT({email:reviewer.email}).setProtectedHeader({alg:'RS256',kid:'test-key'}).setSubject('human').setIssuer(e.ACCESS_ISSUER).setAudience(e.ACCESS_AUD).setIssuedAt().setExpirationTime('5m').sign(pair.privateKey);
    const r=new Request(origin+base,{headers:{'Cf-Access-Jwt-Assertion':token}});
    assert.deepEqual(await authenticate(r,e),reviewer);
    await assert.rejects(()=>authenticate(r,{...e,ACCESS_AUD:'wrong-app'}),/invalid or expired/);
    const expired=await new SignJWT({email:reviewer.email}).setProtectedHeader({alg:'RS256',kid:'test-key'}).setSubject('human').setIssuer(e.ACCESS_ISSUER).setAudience(e.ACCESS_AUD).setIssuedAt().setExpirationTime(1).sign(pair.privateKey);
    await assert.rejects(()=>authenticate(new Request(origin+base,{headers:{'Cf-Access-Jwt-Assertion':expired}}),e),/invalid or expired/);
    const bad=token.slice(0,-10)+'abcdefghij';await assert.rejects(()=>authenticate(new Request(origin+base,{headers:{'Cf-Access-Jwt-Assertion':bad}}),e),/invalid or expired/);
  }finally{globalThis.fetch=original;}
});
