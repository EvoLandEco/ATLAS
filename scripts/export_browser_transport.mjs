/* Lossless transport from a sealed, locally verified ATLAS export. */
import assert from 'node:assert/strict';
import {parseJsonBytes} from './json-file.mjs';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,stat} from 'node:fs/promises';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';
import {spawnSync} from 'node:child_process';
import {TABLES,decodeBrowserCore,BROWSER_TRANSPORT_VERSION} from '../src/atlas/assets/browser_transport.js';
import {compactFigureIdentity} from '../src/atlas/assets/site_view.js';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const encode=value=>Buffer.from(JSON.stringify(value)+'\n');
const pick=(row,keys)=>Object.fromEntries(keys.map(k=>{assert(Object.hasOwn(row,k),`Missing ${k}`);return [k,row[k]];}));
export const detailIdentity=row=>row&&typeof row==='object'?(row.id??row.measure_id??row.series_id??row.finding_id??row.conflict_id??row.context_id??row.record_id??row.code??null):null;
const get=(data,name)=>name.startsWith('metrics.')?data.metrics[name.slice(8)]:data[name];
export function makeCore(site,exportId) {
  const strings=[],stringIds=new Map(),sets=[],setIds=new Map(),figures=new Map();
  const text=value=>{assert.equal(typeof value,'string');if(!stringIds.has(value)){stringIds.set(value,strings.length);strings.push(value);}return stringIds.get(value);};
  const support=value=>{
    assert.equal(value.rule,'all_supporting_records_in_window');assert.equal(value.partial,'hide_relationship_keep_visible_assertions');
    const ids=value.record_ids.map(text),key=JSON.stringify(ids);
    if(!setIds.has(key)){setIds.set(key,sets.length);sets.push(ids);}return setIds.get(key);
  };
  const tables={};
  for(const [name,spec] of Object.entries(TABLES)) {
    const values=name==='report_assessments' && !['1.8.0','1.9.0'].includes(site.contract_version)?[]:get(site,name);
    const rows=values.map(source=>{
      let row=source;
      if(name==='metrics.measures') {
        const key=compactFigureIdentity(source);
        if(key!==null&&!figures.has(key))figures.set(key,figures.size);
        row={...source,source_record_id:source.source_reference.record_id,evidence_record_ids:source.evidence_references.map(e=>e.record_id),compact_figure_id:key===null?null:figures.get(key)};
      }
      if(name==='metrics.reviewed_series')row={...source,evidence_ids:source.evidence.map(e=>e.id)};
      return spec.columns.map((key,i)=>{
        assert(Object.hasOwn(row,key),`Missing ${name}.${key}`);const v=row[key],mode=spec.encoding[i];
        return v===null?null:mode==='string'?text(v):mode==='strings'?v.map(text):mode==='eligibility'?support(v):v;
      });
    });
    tables[name]={...spec,rows};
  }
  const core={transport_version:BROWSER_TRANSPORT_VERSION,source_export_id:exportId,
    metadata:{...pick(site,['contract_version','snapshot','reviewed_chains']),metrics:pick(site.metrics,['contract_version','coverage'])},
    strings,eligibility_record_sets:sets,tables};
  decodeBrowserCore(core,exportId);
  return core;
}
export async function exportTransport(sitePath,mapPath,out,exportId,{maxInputBytes=400_000_000,maxPartitionBytes=2_000_000}={}) {
  assert(/^[a-f0-9]{64}$/.test(exportId),'Invalid export ID');
  assert(Number.isSafeInteger(maxInputBytes) && maxInputBytes > 0 && maxInputBytes <= 2_000_000_000,'Transport input budget must be an integer from 1 to 2000000000 bytes');
  const sizes=await Promise.all([stat(sitePath),stat(mapPath)]);assert(sizes.reduce((n,s)=>n+s.size,0)<=maxInputBytes,'Transport input budget exceeded');
  const [siteBytes,mapBytes,originalSelector]=await Promise.all([readFile(sitePath),readFile(mapPath),readFile(join(dirname(sitePath),'view.mjs'))]);
  assert(siteBytes.length+mapBytes.length<=maxInputBytes,'Transport input budget exceeded');
  const site=parseJsonBytes(siteBytes),map=parseJsonBytes(mapBytes);
  assert(['1.5.0','1.6.0','1.7.0','1.8.0','1.9.0'].includes(site.contract_version),'Unsupported scientific contract');
  assert.equal(hash(mapBytes),site.snapshot.source_snapshot_sha256);
  const manifestBytes=await readFile(join(dirname(sitePath),'manifest.json')),sealed=JSON.parse(manifestBytes);
  assert.equal(exportId,hash(JSON.stringify({manifest_sha256:hash(manifestBytes),map_snapshot_sha256:hash(mapBytes)})),'Source export identity mismatch');
  assert.equal(hash(siteBytes),sealed.files['atlas-site.json']);assert.equal(hash(originalSelector),sealed.files['view.mjs']);
  await mkdir(out,{recursive:false});await mkdir(join(out,'details'));
  const manifest={transport_version:BROWSER_TRANSPORT_VERSION,source_export_id:exportId,
    source:{manifest:{path:'manifest.json',sha256:hash(manifestBytes),bytes:manifestBytes.length},site:{path:'atlas-site.json',sha256:hash(siteBytes),bytes:siteBytes.length},map:{path:'map.json',sha256:hash(mapBytes),bytes:mapBytes.length},
      metrics_sha256:site.snapshot.metrics_sha256,site_contract_version:site.contract_version,selector:{path:'view.mjs',sha256:hash(originalSelector),bytes:originalSelector.length}},
    core:'core.json',map_core:'map-core.json',detail_index:'detail-index.json',selector:'browser_transport.js',assets:{},partitions:[],reconstruction:{metadata:{site:{metrics:{}},map:{}},collections:{}}};
  const save=async(path,value,kind,raw=false)=>{
    const bytes=raw?value:encode(value);await writeFile(join(out,path),bytes,{flag:'wx'});
    manifest.assets[path]={sha256:hash(bytes),bytes:bytes.length,kind};
  };
  await save('core.json',makeCore(site,exportId),'core');
  await save('map-core.json',{transport_version:BROWSER_TRANSPORT_VERSION,source_export_id:exportId,
    ...pick(map,['tracks','map_links','relationships']),records:map.records.map(({claims,...row})=>row)},'map-core');
  for(const name of ['browser_transport.js','browser_tables.js','site_view.js'])await save(name,await readFile(join(root,'src/atlas/assets',name)),'selector',true);
  await save('browser.d.mts',await readFile(join(root,'types/browser.d.mts')),'types',true);
  await save('atlas.d.ts',await readFile(join(root,'types/atlas.d.ts')),'types',true);
  const recordDocs=new Map(site.records.map(r=>[r.id,r.document_id])),owners=new Map(),index={};
  const owner=(collection,row)=>{
    if(collection==='site.metrics.reviewed_series')return `series:${row.series_id}`;
    const document=row?.document_id??row?.source_reference?.document_id??recordDocs.get(row?.record_id??row?.eligibility?.record_ids?.[0]);
    return document?`document:${document}`:'reconstruction';
  };
  function collect(prefix,object,metadata) {
    for(const [key,value]of Object.entries(object)) {
      if(prefix==='site'&&key==='metrics'){collect('site.metrics',value,metadata.metrics);continue;}
      if(!Array.isArray(value)){metadata[key]=value;continue;}
      const collection=`${prefix}.${key}`;manifest.reconstruction.collections[collection]=value.length;index[collection]=new Array(value.length);
      value.forEach((row,ordinal)=>{
        const id=detailIdentity(row);
        const key=owner(collection,row);if(!owners.has(key))owners.set(key,[]);
        owners.get(key).push({collection,ordinal,id,value:row});
      });
    }
  }
  collect('site',site,manifest.reconstruction.metadata.site);collect('map',map,manifest.reconstruction.metadata.map);
  let counter=0;
  for(const [owner,rows]of [...owners].sort(([a],[b])=>a.localeCompare(b))) {
    let batch=[],size=512;
    const flush=async()=>{
      if(!batch.length)return;const path=`details/part-${String(counter++).padStart(5,'0')}.json`;
      await save(path,{transport_version:BROWSER_TRANSPORT_VERSION,source_export_id:exportId,owner,rows:batch},'detail');
      manifest.partitions.push({path,owner,rows:batch.length});
      for(const row of batch)index[row.collection][row.ordinal]=[row.id,manifest.partitions.length-1];batch=[];size=512;
    };
    for(const row of rows){const bytes=encode(row).length;assert(bytes+512<=maxPartitionBytes,'Single detail row exceeds partition budget');if(size+bytes>maxPartitionBytes)await flush();batch.push(row);size+=bytes;}
    await flush();
  }
  await save('detail-index.json',{transport_version:BROWSER_TRANSPORT_VERSION,source_export_id:exportId,partitions:manifest.partitions.map(p=>p.path),collections:index},'detail-index');
  await save('browser-transport.schema.json',transportSchema(),'schema');
  await save('browser-manifest.schema.json',await readFile(join(root,'schemas/browser-manifest.schema.json')),'schema',true);
  await writeFile(join(out,'manifest.json'),encode(manifest),{flag:'wx'});
  return manifest;
}
export function transportSchema() {
  const ref={type:'integer',minimum:0},object=properties=>({type:'object',properties,required:Object.keys(properties),additionalProperties:false});
  const tableSchemas=Object.fromEntries(Object.entries(TABLES).map(([name,spec])=>[name,object({columns:{const:spec.columns},encoding:{const:spec.encoding},rows:{type:'array',items:{type:'array',minItems:spec.columns.length,maxItems:spec.columns.length,prefixItems:spec.encoding.map(mode=>mode==='json'?{}:mode==='eligibility'?ref:{anyOf:[{type:'null'},mode==='strings'?{type:'array',items:ref}:ref]}),items:false}}})]));
  return {$schema:'https://json-schema.org/draft/2020-12/schema',title:'ATLAS browser core 0.4.0',...object({transport_version:{const:BROWSER_TRANSPORT_VERSION},source_export_id:{type:'string',pattern:'^[a-f0-9]{64}$'},metadata:object({contract_version:{enum:['1.5.0','1.6.0','1.7.0','1.8.0','1.9.0']},snapshot:{type:'object'},reviewed_chains:{type:'array'},metrics:object({contract_version:{enum:['0.2.0','0.3.0','0.4.0','0.5.0']},coverage:{type:'object'}})}),strings:{type:'array',uniqueItems:true,items:{type:'string'}},eligibility_record_sets:{type:'array',items:{type:'array',items:ref}},tables:object(tableSchemas)})};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const {values}=parseArgs({options:Object.fromEntries(['site','map','out','export-id','max-input-bytes'].map(k=>[k,{type:'string'}]))});
  for(const key of ['site','map','out','export-id'])assert(values[key],`--${key} is required`);
  const verify=spawnSync(join(root,'.venv/bin/atlas'),['site-verify',dirname(resolve(values.site))],{cwd:root,env:{...process.env,PYTHONPATH:join(root,'src')},encoding:'utf8'});
  assert.equal(verify.status,0,verify.stderr||verify.stdout);
  const result=await exportTransport(resolve(values.site),resolve(values.map),resolve(values.out),values['export-id'],{maxInputBytes:values['max-input-bytes'] === undefined ? 400_000_000 : Number(values['max-input-bytes'])});
  console.log(JSON.stringify({source_export_id:result.source_export_id,assets:Object.keys(result.assets).length,core_bytes:result.assets[result.core].bytes,map_core_bytes:result.assets[result.map_core].bytes}));
}
