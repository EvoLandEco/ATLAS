import assert from 'node:assert/strict';
import {parseJsonBytes} from './json-file.mjs';
import {createHash} from 'node:crypto';
import {readFile,stat,writeFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';
import {detailIdentity} from './export_browser_transport.mjs';
const runtimePaths = {'0.3.0':'../src/atlas/assets/browser_v0_3/', '0.4.0':'../src/atlas/assets/'};
const hash=value=>createHash('sha256').update(value).digest('hex');
export async function verifyTransport(directory,{sitePath,mapPath,everyRecord=false}={}) {
  const manifestPath=resolve(directory,'manifest.json'),manifestBytes=await readFile(manifestPath),manifest=JSON.parse(manifestBytes);
  const runtimePath = runtimePaths[manifest.transport_version];
  assert(runtimePath, 'Unsupported browser transport version');
  const {prepareBrowserView,hydrateBrowserView,BROWSER_TRANSPORT_VERSION} = await import(new URL(runtimePath+'browser_transport.js',import.meta.url));
  assert.equal(manifest.transport_version,BROWSER_TRANSPORT_VERSION);
  const read=async name=>{
    assert(/^[a-zA-Z0-9_-]+(?:\/[a-zA-Z0-9_-]+)*\.[a-zA-Z0-9.]+$/.test(name),'Unsafe asset path');
    const expected=manifest.assets[name];assert(expected,'Unlisted asset');
    assert.equal((await stat(join(directory,name))).size,expected.bytes,`Size mismatch ${name}`);
    const bytes=await readFile(join(directory,name));assert.equal(hash(bytes),expected.sha256,`Hash mismatch ${name}`);return bytes;
  };
  // Verify executable bytes against this installed implementation, never execute supplied code.
  for(const name of ['browser_transport.js','browser_tables.js','site_view.js'])assert.deepEqual(await read(name),await readFile(new URL(runtimePath+name,import.meta.url)));
  const json=async name=>{
    const value=JSON.parse(await read(name));assert.equal(value.source_export_id,manifest.source_export_id,'Mixed source release');assert.equal(value.transport_version,BROWSER_TRANSPORT_VERSION);return value;
  };
  const result=structuredClone(manifest.reconstruction.metadata),seen=new Map(),inventory=new Map();
  assert.equal(manifest.source_export_id,hash(JSON.stringify({manifest_sha256:manifest.source.manifest.sha256,map_snapshot_sha256:manifest.source.map.sha256})));
  for(const [name,count]of Object.entries(manifest.reconstruction.collections)) {
    assert(Number.isSafeInteger(count)&&count>=0);
    assert(/^site(?:\.metrics)?\.[a-z_]+$|^map\.[a-z_]+$/.test(name),'Unknown reconstruction path');
    const keys=name.split('.');assert(keys.every(k=>!['__proto__','constructor','prototype'].includes(k)),'Unsafe reconstruction key');const key=keys.pop(),parent=keys.reduce((v,k)=>v[k],result);
    assert(!Object.hasOwn(parent,key),'Duplicate reconstruction field');parent[key]=new Array(count);seen.set(name,new Set());
  }
  const indexed=new Map(),entityIds=new Map();
  for(let i=0;i<manifest.partitions.length;i++) {
    const descriptor=manifest.partitions[i],part=await json(descriptor.path);assert.equal(part.owner,descriptor.owner);assert.equal(part.rows.length,descriptor.rows);assert(!inventory.has(descriptor.path),'Duplicate partition');inventory.set(descriptor.path,true);
    for(const row of part.rows) {
      const positions=seen.get(row.collection);assert(positions,'Unknown collection');
      const expectedId=detailIdentity(row.value);
      assert.equal(row.id,expectedId,'Detail identity mismatch');
      if(row.id!==null){if(!entityIds.has(row.collection))entityIds.set(row.collection,new Set());const ids=entityIds.get(row.collection);assert(!ids.has(row.id),'Duplicate entity ID');ids.add(row.id);}
      const array=row.collection.split('.').reduce((v,k)=>v[k],result);
      assert(Number.isSafeInteger(row.ordinal)&&row.ordinal>=0&&row.ordinal<array.length&&!positions.has(row.ordinal),'Duplicate or invalid ordinal');positions.add(row.ordinal);array[row.ordinal]=row.value;
      indexed.set(`${row.collection}:${row.ordinal}`,[row.id,i]);
    }
  }
  for(const [name,positions]of seen)assert.equal(positions.size,manifest.reconstruction.collections[name],`Missing rows ${name}`);
  const index=await json(manifest.detail_index);assert.deepEqual(index.partitions,manifest.partitions.map(p=>p.path));assert.deepEqual(Object.keys(index.collections),Object.keys(manifest.reconstruction.collections));
  for(const [name,rows]of Object.entries(index.collections)) {
    assert.equal(rows.length,manifest.reconstruction.collections[name]);
    rows.forEach((row,ordinal)=>assert.deepEqual(row,indexed.get(`${name}:${ordinal}`)));
  }
  const core=await json(manifest.core),mapCore=await json(manifest.map_core),browser=prepareBrowserView(core,manifest.source_export_id);
  assert.deepEqual(mapCore.records,result.map.records.map(({claims,...row})=>row));
  for(const k of ['tracks','map_links','relationships'])assert.deepEqual(mapCore[k],result.map[k]);
  const originals={};
  for(const [key,path]of [['site',sitePath],['map',mapPath]])if(path){const bytes=await readFile(path);assert.equal(hash(bytes),manifest.source[key].sha256);assert.equal(bytes.length,manifest.source[key].bytes);originals[key]=parseJsonBytes(bytes);assert.deepEqual(result[key],originals[key],`Reconstruction mismatch ${key}`);}
  // Every asset is checked, including assets not needed by the selector.
  for(const name of Object.keys(manifest.assets))await read(name);
  const version=result.site.contract_version;
  const {prepareView}=await import(new URL('../src/atlas/assets/site_view.js',import.meta.url));
  const selectorFile={'1.5.0':'site_view_v1_5.js','1.6.0':'site_view_v1_6.js','1.7.0':'site_view_v1_7.js','1.8.0':'site_view_v1_8.js','1.9.0':'site_view.js'}[version];
  assert(selectorFile,'No pinned selector for this scientific contract');
  const pinned=(await import(new URL(`../src/atlas/assets/${selectorFile}`,import.meta.url))).selectView;
  const reference=prepareView(result.site),series=new Map(result.site.metrics.reviewed_series.map(s=>[s.series_id,s]));
  const dates=result.site.records.map(r=>r.publication.slice(0,10)).sort(),from=dates[0],until=dates.at(-1);
  const cases=[[from,until],[from,until,'publication',null,[]],[from,until,'capture'],[from,until,'publication',result.site.records[0].capture]];
  for(const domain of ['human','animal','environment','food','unknown'])cases.push([from,until,'publication',null,null,{domains:[domain]}]);
  cases.push([from,until,'publication',null,null,{observation_from:from,observation_until:until}]);
  for(const c of result.site.comparisons){const ids=c.eligibility.record_ids;cases.push([from,until,'publication',null,ids]);if(ids.length)cases.push([from,until,'publication',null,ids.slice(1)]);}
  for(const channel of result.site.channels)cases.push([from,until,'publication',null,result.site.records.filter(r=>r.channel_id===channel.id).map(r=>r.id)]);
  for(const p of result.site.places.slice(0,12))cases.push([from,until,'publication',null,p.record_ids]);
  for(const d of result.site.diseases.slice(0,12))cases.push([from,until,'publication',null,result.site.disease_reviews.filter(r=>r.disease_ids.includes(d.id)).map(r=>r.record_id)]);
  for(const month of [...new Set(dates.map(d=>d.slice(0,7)))])cases.push([`${month}-01`,`${month}-${new Date(Date.UTC(Number(month.slice(0,4)),Number(month.slice(5)),0)).getUTCDate()}`]);
  if(everyRecord)for(const r of result.site.records)cases.push([from,until,'publication',null,[r.id]]);
  for(const args of cases){const selected=hydrateBrowserView(browser.select(...args),series);assert.deepEqual(selected,reference(...args));assert.deepEqual(selected,pinned(result.site,...args));}
  assert.deepEqual(await readFile(manifestPath),manifestBytes,'Manifest changed during verification');
  const producerReady=!!(sitePath&&mapPath&&everyRecord);
  return {browser_handoff_version:'0.1.0',checked_at:new Date().toISOString(),source_export_id:manifest.source_export_id,asset_count:Object.keys(manifest.assets).length,source_files_compared:Object.keys(originals),reconstruction:true,selection_cases:cases.length,pinned_selector_parity:true,all_records_individually:everyRecord,producer_ready:producerReady,browser:producerReady?{transport_version:manifest.transport_version,source_export_id:manifest.source_export_id,scientific_contract:manifest.source.site_contract_version,directory:resolve(directory),manifest:{path:manifestPath,sha256:hash(manifestBytes),bytes:manifestBytes.length},source:manifest.source}:null,consumer_adoption:false,publication_authorized:false};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const {values}=parseArgs({options:{directory:{type:'string'},site:{type:'string'},map:{type:'string'},out:{type:'string'},'every-record':{type:'boolean',default:false}}});
  assert(values.directory&&values.site&&values.map&&values.out,'Need directory, site, map and out');
  const receipt=await verifyTransport(resolve(values.directory),{sitePath:values.site,mapPath:values.map,everyRecord:values['every-record']});
  await writeFile(values.out,JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(receipt));
}
