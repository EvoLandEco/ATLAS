import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,copyFileSync,existsSync,readFileSync,rmSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

test('deployment configuration requires real identifiers and stores no credentials',()=>{
  const dir=mkdtempSync(join(tmpdir(),'atlas-inbox-config-'));
  try{
    for(const file of ['configure.mjs','wrangler.jsonc'])copyFileSync(new URL('../'+file,import.meta.url),join(dir,file));
    const env={PATH:process.env.PATH,CLOUDFLARE_ACCOUNT_ID:'a'.repeat(32),ATLAS_INBOX_DATABASE_ID:'12345678-1234-1234-1234-123456789abc',INBOX_ORIGIN:'https://review.example.org',ACCESS_ISSUER:'https://test.cloudflareaccess.com',ACCESS_AUD:'test-audience',SYNC_SERVICE_TOKEN_ID:'test-service',CLOUDFLARE_API_TOKEN:'synthetic-secret'};
    let run=spawnSync(process.execPath,[join(dir,'configure.mjs')],{env:{...env,ACCESS_AUD:''},encoding:'utf8'});
    assert.notEqual(run.status,0);assert.equal(existsSync(join(dir,'wrangler.local.json')),false);
    for(const origin of ['', 'http://review.example.org', 'https://review.example.org/path', 'https://user:password@review.example.org', 'https://review.example.org?query=1', 'https://review.example.org#fragment']){
      run=spawnSync(process.execPath,[join(dir,'configure.mjs')],{env:{...env,INBOX_ORIGIN:origin},encoding:'utf8'});
      assert.notEqual(run.status,0);assert.equal(existsSync(join(dir,'wrangler.local.json')),false);
    }
    run=spawnSync(process.execPath,[join(dir,'configure.mjs')],{env,encoding:'utf8'});assert.equal(run.status,0,run.stderr);
    const text=readFileSync(join(dir,'wrangler.local.json'),'utf8'),config=JSON.parse(text);
    assert.equal(config.vars.REVIEWER_EMAILS,'tianjian.qin@wur.nl');assert.equal(config.workers_dev,true);assert.equal(config.preview_urls,false);assert.equal(config.assets.run_worker_first,true);
    assert.equal(config.vars.INBOX_ORIGIN,env.INBOX_ORIGIN);assert.deepEqual(config.routes,[]);
    assert.equal(text.includes('synthetic-secret'),false);assert.equal((run.stdout+run.stderr).includes('synthetic-secret'),false);
  }finally{rmSync(dir,{recursive:true,force:true});}
});
