"""Source bounds and calendar precision survive research exports."""
import copy
import pytest
from atlas.metrics import CardMeasure,MetricAnnotations
from atlas.site_export import ObservationTime
from test_metrics import inputs


def test_strict_measurement_bounds_require_their_contract(tmp_path):
    batch=inputs(tmp_path)[3]
    batch['contract_version']='0.4.0'
    for qualifier in ['more_than','less_than']:
        batch['measures'][0]['qualifier']=qualifier
        assert MetricAnnotations.model_validate(batch).measures[0].qualifier==qualifier
        old=copy.deepcopy(batch);old['contract_version']='0.3.0'
        with pytest.raises(ValueError):MetricAnnotations.model_validate(old)


def test_mixed_precision_preserves_both_source_boundaries():
    time=dict(kind='intervention',extent='closed_interval',start=dict(value='2025',status='reported'),end=dict(value='2026-05',status='reported'),precision='mixed',certainty='exact',label='2025 through May 2026',reason='The source gives a year and a month boundary.')
    assert ObservationTime.model_validate(time).model_dump()==time
    assert ObservationTime.model_validate(dict(time,start=dict(value='2026-07',status='reported'),end=dict(value='2026',status='reported'))).end.value=='2026'
    for changes in [dict(end=dict(value='2026-13',status='reported')),dict(start=dict(value='2027',status='reported')),dict(precision='month'),dict(extent='point')]:
        with pytest.raises(ValueError):ObservationTime.model_validate(dict(time,**changes))


def test_mixed_precision_selection_uses_each_calendar_extent(tmp_path):
    import subprocess
    from test_one_health_panels import panel_inputs
    from atlas.site_export import export_site,verify_site
    from atlas.util import write_json
    paths,ann=panel_inputs(tmp_path)
    for field in ['one_health_timings','one_health_contexts']:
        ann[field][0]['time'].update(extent='closed_interval',start=dict(value='2025',status='reported'),end=dict(value='2026-07',status='reported'),precision='mixed')
    write_json(paths['annotations'],ann)
    export_site(**paths,out=tmp_path/'out')
    assert verify_site(tmp_path/'out')['contract_version']=='1.9.0'
    script="""
import fs from 'node:fs';import assert from 'node:assert/strict';
const {selectView}=await import(process.argv[1]);const data=JSON.parse(fs.readFileSync(process.argv[2]));
for(const [day,count] of [['2024-12-31',0],['2025-01-01',1],['2026-07-31',1],['2026-08-01',0]]) {
const view=selectView(data,'2026-07-01','2026-08-02','publication',null,null,{observation_from:day,observation_until:day});
assert.equal(view.one_health.timings.length,count,day);assert.equal(view.one_health.contexts.length,count,day);
}
"""
    subprocess.run(['node','--input-type=module','-e',script,(tmp_path/'out/view.mjs').as_uri(),str(tmp_path/'out/atlas-site.json')],check=True)
