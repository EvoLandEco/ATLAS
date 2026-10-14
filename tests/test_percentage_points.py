"""Source-reported percentage-point differences retain their ordered context."""
import copy
from pathlib import Path
import subprocess

import jsonschema
import pytest

from atlas.metrics import CardMeasure, MetricAnnotations, MetricsExport
from atlas.models import Observation
from atlas.util import digest, read_json, write_json
from test_metrics import inputs, run


def point_inputs(tmp_path, value=-1.5):
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths = inputs(tmp_path)
    batch, snapshot = paths[3:]
    quote = f'Test positivity in week 37 minus week 36 was {value:g} percentage points.'
    snapshot['records'][0]['claims'][0].update(text=quote, quotes=[quote])
    measure = batch['measures'][0]
    measure.update(unit='percentage_points', value=value, metric='test_positivity',
                   ratio_basis='source_reported', label='Change in test positivity',
                   percentage_point_comparison={'baseline': 'Week 36', 'comparison': 'Week 37',
                                                'operation': 'comparison_minus_baseline'})
    measure['evidence']['quote'] = quote
    batch.update(contract_version='0.5.0', records_sha256=digest(snapshot['records']))
    (paths[2] / (measure['source_reference']['document_id'] + '.txt')).write_text(
        '\n'.join(claim['quotes'][0] for claim in snapshot['records'][0]['claims']))
    write_json(paths[0], snapshot)
    write_json(paths[1], batch)
    return paths


@pytest.mark.parametrize('value', [-100, -1.5, 0, 0.2, 100])
def test_signed_percentage_points_preserve_evidence_and_context(tmp_path, value):
    paths = point_inputs(tmp_path, value)
    result = run(paths, tmp_path / 'out')
    measure = result['measures'][0]
    assert result['contract_version'] == '0.5.0'
    assert measure['unit'] == 'percentage_points' and measure['value'] == value
    assert measure['percentage_point_comparison'] == paths[3]['measures'][0]['percentage_point_comparison']
    assert measure['evidence_references'][0]['quotes'] == [paths[3]['measures'][0]['evidence']['quote']]
    assert result['reviewed_series'] == []
    assert result['series'][0]['connect_points'] is False
    jsonschema.Draft202012Validator(read_json(tmp_path / 'out/metrics.schema.json')).validate(result)
    MetricsExport.model_validate(result)


@pytest.mark.parametrize('value', [-100.01, 100.01, float('inf'), float('nan')])
def test_percentage_point_range(tmp_path, value):
    batch = point_inputs(tmp_path)[3]
    batch['measures'][0]['value'] = value
    with pytest.raises(ValueError):
        MetricAnnotations.model_validate(batch)


def test_percentage_points_need_their_version_and_source_context(tmp_path):
    batch = point_inputs(tmp_path)[3]
    mutations = [
        lambda b: b.update(contract_version='0.4.0'),
        lambda b: b['measures'][0].pop('percentage_point_comparison'),
        lambda b: b['measures'][0]['percentage_point_comparison'].update(operation='baseline_minus_comparison'),
        lambda b: b['measures'][0]['percentage_point_comparison'].update(baseline=''),
        lambda b: b['measures'][0]['percentage_point_comparison'].update(comparison='Week 36'),
        lambda b: b['measures'][0].update(ratio_basis='not_applicable'),
        lambda b: b['measures'][0].update(denominator=100, denominator_status='reported',
                                       denominator_population={'value': 'Samples', 'status': 'reported'}),
    ]
    for mutate in mutations:
        invalid = copy.deepcopy(batch)
        mutate(invalid)
        with pytest.raises(ValueError):
            MetricAnnotations.model_validate(invalid)
    paths = point_inputs(tmp_path / 'other')
    paths[4]['records'][0]['claims'][0]['quotes'][0] = 'Unsupported quoted value.'
    paths[3]['records_sha256'] = digest(paths[4]['records'])
    write_json(paths[0], paths[4])
    write_json(paths[1], paths[3])
    with pytest.raises(ValueError):
        run(paths, tmp_path / 'bad')


def test_extraction_and_card_measure_schemas_are_preserved():
    fixture = Path(__file__).parent / 'fixtures/metrics-0.4-schemas.json'
    expected = read_json(fixture)
    assert CardMeasure.model_json_schema() == expected['CardMeasure']
    assert Observation.model_json_schema() == expected['Observation']


def test_ordered_comparison_context_separates_compact_figures(tmp_path):
    measure = run(point_inputs(tmp_path), tmp_path / 'out')['measures'][0]
    second = copy.deepcopy(measure)
    second['percentage_point_comparison'].update(baseline='Week 37', comparison='Week 36')
    source = Path(__file__).parents[1] / 'src/atlas/assets/site_view.js'
    values = tmp_path / 'values.json'
    write_json(values, [measure, second])
    subprocess.run(['node', '--input-type=module', '-e', """
import fs from 'node:fs';
import assert from 'node:assert/strict';
const {compactFigureIdentity} = await import(process.argv[1]);
const [a,b] = JSON.parse(fs.readFileSync(process.argv[2]));
assert.notEqual(compactFigureIdentity(a), compactFigureIdentity(b));
""", source.as_uri(), str(values)], check=True)
