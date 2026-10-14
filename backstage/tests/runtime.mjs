import {build} from 'esbuild';
import {Miniflare} from 'miniflare';
import {generateKeyPair, exportJWK, SignJWT} from 'jose';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';

export async function createRuntime(origin='https://qtj.me') {
  const pair=await generateKeyPair('RS256'), jwk=await exportJWK(pair.publicKey);jwk.kid='local-test-key';
  const issuer='https://atlas-test.cloudflareaccess.com';
  const compiled=await build({entryPoints:[new URL('../src/worker.mjs',import.meta.url).pathname],bundle:true,write:false,format:'esm',platform:'browser',target:'es2022'});
  const values={INBOX_ORIGIN:origin,INBOX_PATH:'/atlas/review/',ATLAS_ARCHIVE_ID:'atlas',REVIEWER_EMAILS:'tianjian.qin@wur.nl',ACCESS_ISSUER:issuer,ACCESS_AUD:'test-inbox',SYNC_SERVICE_TOKEN_ID:'test-sync'};
  const mf=new Miniflare({telemetry:{enabled:false},workers:[{config:{name:'inbox-test',compatibilityDate:'2026-10-14',
    manifest:{mainModule:'worker.mjs',modules:{'worker.mjs':{type:'esm',contents:compiled.outputFiles[0].text}}},
    env:{...Object.fromEntries(Object.entries(values).map(([k,value])=>[k,{type:'text',value}])),DB:{type:'d1',id:'test-db'},EVIDENCE:{type:'r2',name:'test-evidence'},
      ASSETS:{type:'fetcher',handler:async request=>{const path=new URL(request.url).pathname;const name=path==='/'?'index.html':path.slice(1);const types={'index.html':'text/html','app.js':'text/javascript','style.css':'text/css','atlas-logo.svg':'image/svg+xml','geist-sans.woff2':'font/woff2','geist-mono.woff2':'font/woff2','FONT-LICENSE.txt':'text/plain'};if(!types[name])return new Response('Not found',{status:404});return new Response(readFileSync(new URL('../public/'+name,import.meta.url)),{headers:{'Content-Type':types[name]}});}}},
    },dev:{outboundService:{type:'fetcher',handler:async request=>new URL(request.url).href===issuer+'/cdn-cgi/access/certs'?Response.json({keys:[jwk]}):new Response('Unexpected outbound request',{status:403})}}}]});
  try {
  const db=await mf.getD1Database('DB');
  const sql=readFileSync(new URL('../migrations/0001_inbox.sql',import.meta.url),'utf8');
  const split=spawnSync(process.env.ATLAS_TEST_PYTHON||'python3',['-c',`import sqlite3,sys,json
statements=[];statement=''
for line in sys.stdin:
 statement+=line
 if sqlite3.complete_statement(statement):
  statements.append(statement);statement=''
assert not statement.strip()
print(json.dumps(statements))`],{input:sql,encoding:'utf8'});
  if(split.status!==0)throw new Error(split.stderr);
  const statements=JSON.parse(split.stdout);
  for(const statement of statements)await db.prepare(statement).run();
  const sign=claims=>new SignJWT(claims).setProtectedHeader({alg:'RS256',kid:jwk.kid}).setSubject(claims.email?'reviewer':'').setIssuer(issuer).setAudience('test-inbox').setIssuedAt().setExpirationTime('2h').sign(pair.privateKey);
  const reviewerToken=await sign({email:'tianjian.qin@wur.nl'}),serviceToken=await sign({common_name:'test-sync'});
  async function request(path,{service=false,body,raw,method=body?'POST':'GET',authenticated=true}={}){
    const headers=authenticated?{'Cf-Access-Jwt-Assertion':service?serviceToken:reviewerToken}:{};
    if(body){headers['Content-Type']='application/json';headers.Origin=origin;headers['X-Atlas-Review']='1';}
    return mf.dispatchFetch(origin+'/atlas/review/'+path,{method,headers,body:body?JSON.stringify(body):raw});
  }
  return {mf,request,reviewerToken};
  } catch(error) {await mf.dispose();throw error;}
}
