/* Deterministic selector stress test using independent copies of a captured graph. */
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {performance} from 'node:perf_hooks';
import assert from 'node:assert/strict';
const [bundlePath, selectorPath, outputPath, referencePath] = process.argv.slice(2);
if (!outputPath) throw new Error('Usage: node scripts/benchmark_view.mjs BUNDLE SELECTOR OUTPUT [REFERENCE_SELECTOR]');
const original = JSON.parse(fs.readFileSync(bundlePath));
const {selectView} = await import(pathToFileURL(path.resolve(selectorPath)));
const reference = referencePath ? (await import(pathToFileURL(path.resolve(referencePath)))).selectView : null;
// Only fields consumed by the selector are replicated; source text and file parsing are outside the timing.
const base = Object.fromEntries(['contract_version','records','assertions','comparisons','relationships','places','location_memberships','source_coverage','reviewed_chains','diseases','disease_reviews','one_health_reviews','one_health_nodes','one_health_relations'].map(k => [k,original[k]]));
base.metrics = Object.fromEntries(['measures','panels','reviewed_series'].map(k => [k,original.metrics[k]]));
const ids = new Set();
function collect(value) {
  if (Array.isArray(value)) value.forEach(collect);
  else if (value && typeof value === 'object') for (const [key,item] of Object.entries(value)) {
    if ((key === 'id' || key.endsWith('_id')) && typeof item === 'string') ids.add(item);
    if (key.endsWith('_ids') && Array.isArray(item)) item.forEach(id => ids.add(id));
    collect(item);
  }
}
collect(base);
function copy(value, index) {
  if (typeof value === 'string') return ids.has(value) ? `${index}:${value}` : value;
  if (Array.isArray(value)) return value.map(v => copy(v,index));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k,v]) => [k,copy(v,index)]));
  return value;
}
const rows=[];
for (const scale of [1,2,4,8]) {
  const data=copy(base,0);
  for (let i=1;i<scale;i++) {
    const next=copy(base,i);
    for (const key of Object.keys(base)) if (Array.isArray(data[key])) data[key].push(...next[key]);
    for (const key of Object.keys(base.metrics)) data.metrics[key].push(...next.metrics[key]);
  }
  const dates=data.records.map(r=>r.publication.slice(0,10)).sort(),from=dates[0],until=dates.at(-1);
  const channel=data.records[0].channel_id;
  const selected=data.records.filter(r=>r.channel_id===channel).map(r=>r.id);
  for (const [name,selection] of [['all',null],['source',selected]]) {
    const args=[data,from,until,'publication',null,selection];
    if (reference) assert.deepEqual(selectView(...args),reference(...args));
    for (let warmup=0;warmup<5;warmup++) selectView(...args);
    const elapsed=[];
    for (let run=0;run<11;run++) {const start=performance.now();selectView(...args);elapsed.push(performance.now()-start);}
    rows.push({scale,selection:name,records:data.records.length,coverage_edges:data.source_coverage.length,median_ms:elapsed.sort((a,b)=>a-b)[5]});
  }
}
const result={node:process.version,platform:process.platform,arch:process.arch,method:'Five warmups, eleven timed calls; median. Independent graph replicas with unique identities; not a projection of future report content. JSON parsing, rendering and graph construction excluded.',reference_equivalence:reference!==null,rows,process_peak_rss_mib:process.resourceUsage().maxRSS/1024};
fs.writeFileSync(outputPath,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(rows));
