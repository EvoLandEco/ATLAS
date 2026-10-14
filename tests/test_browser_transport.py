"""Browser summaries preserve source selection and retain lossless detail partitions."""
import json
import subprocess
from pathlib import Path
from atlas.site_export import export_site, verify_site
from atlas.handoff import inspect_export
from test_one_health_panels import panel_inputs

ROOT = Path(__file__).resolve().parents[1]


def test_scientific_export_fits_compact_transport_budget(tmp_path):
    paths, _ = panel_inputs(tmp_path)
    directory = tmp_path / 'site'
    bundle = export_site(**paths, out=directory)
    encoded = (directory / 'atlas-site.json').read_bytes()
    assert json.loads(encoded) == bundle
    assert verify_site(directory)['status'] == 'valid'
    reference = inspect_export(directory, paths['snapshot'])
    script = """
const {exportTransport}=await import(process.argv[1]);
const assert=await import('node:assert/strict');
for(const limit of [0,2000000001,true,1.5]) await assert.rejects(exportTransport(...process.argv.slice(2),{maxInputBytes:limit}),/Transport input budget must/);
await exportTransport(...process.argv.slice(2),{maxInputBytes:36000});
"""
    subprocess.run(['node', '--input-type=module', '-e', script,
                    (ROOT / 'scripts/export_browser_transport.mjs').as_uri(),
                    str(directory / 'atlas-site.json'), str(paths['snapshot']),
                    str(tmp_path / 'browser'), reference['export_id']], check=True)


def test_transport_roundtrip_and_corruption(tmp_path):
    paths, _ = panel_inputs(tmp_path)
    bundle = tmp_path / 'site'
    export_site(**paths, out=bundle)
    # The fixture source snapshot is the same exact file bound by export_site.
    snapshot = paths['snapshot']
    reference = inspect_export(bundle, snapshot)
    script = r"""
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
const {exportTransport,makeCore,transportSchema}=await import(process.argv[1]);
const {verifyTransport}=await import(process.argv[2]);
const {decodeBrowserCore,prepareBrowserView,hydrateBrowserView}=await import(process.argv[3]);
const {prepareView}=await import(new URL('site_view.js',process.argv[3]));
const [site,map,out,id]=process.argv.slice(4);
const manifest=await exportTransport(site,map,out,id);
const result=await verifyTransport(out,{sitePath:site,mapPath:map,everyRecord:true});assert(result.reconstruction);
assert(result.producer_ready);assert(result.pinned_selector_parity);assert.equal(result.browser.source_export_id,id);
assert.equal(result.browser.manifest.bytes,(await readFile(out+'/manifest.json')).length);
assert.equal(result.browser.manifest.sha256,(await import('node:crypto')).createHash('sha256').update(await readFile(out+'/manifest.json')).digest('hex'));
assert.deepEqual(result.browser.source,manifest.source);assert.equal(result.publication_authorized,false);
const partial=await verifyTransport(out,{sitePath:site,mapPath:map});assert.equal(partial.producer_ready,false);assert.equal(partial.browser,null);
const original=JSON.parse(await readFile(site));
// Nonempty lineage is an ordered array of edge objects, including under partial support.
original.comparisons[0].lineage=[{from_assertion_id:original.assertions[0].id,to_assertion_id:original.assertions[1].id,evidence_ids:[]}];
const core=makeCore(original,id),decoded=decodeBrowserCore(core,id);
assert.deepEqual(decoded.comparisons[0].lineage,original.comparisons[0].lineage);
for (const qualifier of ["more_than", "less_than", "at_least", "at_most", "exact"]) {
  original.metrics.measures[0].qualifier=qualifier;
  assert.equal(decodeBrowserCore(makeCore(original,id),id).metrics.measures[0].qualifier,qualifier);
}
for (const kind of ['correction','supersession','contradiction','different_scope','unresolved_association']) {
  original.comparisons[0].kind=kind;
  original.comparisons[0].lineage=['correction','supersession'].includes(kind)?decoded.comparisons[0].lineage:[];
  const compact=prepareBrowserView(makeCore(original,id),id),full=prepareView(original);
  const series=new Map(original.metrics.reviewed_series.map(s=>[s.series_id,s]));
  for(const selected of [null,[],original.records.map(r=>r.id),[original.records[0].id]]) {
    const args=['2020-01-01','2030-01-01','publication',null,selected];
    assert.deepEqual(hydrateBrowserView(compact.select(...args),series),full(...args));
  }
}
const bad=structuredClone(core);bad.tables.records.rows[0].pop();assert.throws(()=>decodeBrowserCore(bad,id));
const ref=structuredClone(core);ref.tables.records.rows[0][0]=core.strings.length;assert.throws(()=>decodeBrowserCore(ref,id));
assert.throws(()=>decodeBrowserCore(core,'wrong-source'));
const reordered=structuredClone(core);reordered.tables.records.columns.reverse();assert.throws(()=>decodeBrowserCore(reordered,id));
await writeFile(out+'/schema-for-test.json',JSON.stringify(transportSchema()));
const path=out+'/'+manifest.partitions[0].path,bytes=await readFile(path);await writeFile(path,bytes.subarray(1));
await assert.rejects(verifyTransport(out,{sitePath:site,mapPath:map}),/Size mismatch/);
await writeFile(path,bytes);
const indexPath=out+'/'+manifest.detail_index,index=await readFile(indexPath);await writeFile(indexPath,Buffer.alloc(index.length));
await assert.rejects(verifyTransport(out,{sitePath:site,mapPath:map}),/Hash mismatch/);
"""
    out = tmp_path / 'browser'
    subprocess.run(['node', '--input-type=module', '-e', script,
                    (ROOT/'scripts/export_browser_transport.mjs').as_uri(),
                    (ROOT/'scripts/verify_browser_transport.mjs').as_uri(),
                    (ROOT/'src/atlas/assets/browser_transport.js').as_uri(),
                    str(bundle/'atlas-site.json'), str(snapshot), str(out), reference['export_id']], check=True)
    import jsonschema
    jsonschema.validate(json.loads((out/'core.json').read_text()), json.loads((out/'schema-for-test.json').read_text()))
    jsonschema.validate(json.loads((out/'manifest.json').read_text()), json.loads((ROOT/'schemas/browser-manifest.schema.json').read_text()))
