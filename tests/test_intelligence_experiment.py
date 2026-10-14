"""Scientific boundary checks for the isolated Intelligence experiment."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('intelligence_experiment', Path(__file__).parents[1]/'scripts/intelligence/build.py')
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


def test_predictions_are_nonnegative_and_score_matches_interval_formula():
    for model in experiment.MODELS:
        for horizon in (1, 2):
            pred = experiment.prediction([0]*8, horizon, model)
            assert pred['central'] == 0
            assert all(0 <= i['lower'] <= pred['central'] <= i['upper'] for i in pred['intervals'])
    pred = {'central': 10, 'intervals': [
        {'level': 0.5, 'lower': 8, 'upper': 12},
        {'level': 0.8, 'lower': 5, 'upper': 15},
        {'level': 0.95, 'lower': 0, 'upper': 20}]}
    assert experiment.score(pred, 10) == pytest.approx((0, 2.5/3.5))
    assert experiment.score(pred, 20) == pytest.approx((10, 20.5/3.5))
    with pytest.raises(ValueError):
        experiment.prediction([1]*7+[-1], 1, 'random_walk')


def test_exact_reviewed_edges_preserve_gaps_and_conflicts():
    rows = {
        str(i): {'measure_id': str(i), 'observation_date': end,
                 'value': 0, 'value_status': 'reported', 'count_kind': 'interval', 'conflict_set': None,
                 'period_start': {'value': start}, 'period_end': {'value': end}}
        for i, (start, end) in enumerate([('2026-01-05', '2026-01-11'), ('2026-01-12', '2026-01-18'), ('2026-01-19', '2026-01-25')])}
    series = {'members': [{'measure_id': k} for k in rows], 'connections': [
        {'from_measure_id': '0', 'to_measure_id': '1'}, {'from_measure_id': '1', 'to_measure_id': '2'}]}
    runs, excluded = experiment.segments(series, rows)
    assert [len(r) for r in runs] == [3] and excluded == []
    series['connections'].pop()
    assert [len(r) for r in experiment.segments(series, rows)[0]] == [2, 1]
    rows['1']['conflict_set'] = 'unresolved'
    runs, excluded = experiment.segments(series, rows)
    assert [[m['measure_id'] for m in r] for r in runs] == [['0'], ['2']]
    assert excluded[0]['measure_id'] == '1'


def test_baseline_has_exact_empirical_mass_and_training_only_forecasts():
    values = [10, 11, 12, 13, 14, 15, 16, 17]
    assert experiment.forecast(values, 1, 'random_walk')[0.5] == 17
    assert experiment.forecast(values, 1, 'recent_changes')[0.5] == 18
    forecast = experiment.prediction(values, 2, 'recent_changes')
    assert forecast['central'] == 19
    assert all(i['lower'] == i['upper'] == 19 for i in forecast['intervals'])
    experiment.score(forecast, 1000)
    assert experiment.prediction(values, 2, 'recent_changes') == forecast


def test_hindcast_excludes_target_and_preserves_historical_availability():
    from datetime import date, timedelta
    measures, records = {}, {}
    for i in range(12):
        end = date(2026, 1, 4)+timedelta(days=7*i)
        rid, mid = f'record-{i}', f'measure-{i}'
        records[rid] = {'id': rid, 'document_id': f'document-{i}', 'publication': end.isoformat(), 'capture': '2026-09-28T00:00:00Z'}
        measures[mid] = {'measure_id': mid, 'observation_date': end.isoformat(), 'value': i+10, 'value_status': 'reported',
                         'count_kind': 'interval', 'conflict_set': None, 'period_start': {'value': (end-timedelta(days=6)).isoformat()},
                         'period_end': {'value': end.isoformat()}, 'source_reference': {'record_id': rid},
                         'publication': end.isoformat(), 'capture': '2026-09-28T00:00:00Z', 'label': 'Cases'}
    series = {'series_id': 'test-series', 'label': 'Test programme', 'operation': 'reported_interval_counts',
              'reviewed_at': '2026-09-28T00:00:00Z', 'limitations': [], 'members': [{'measure_id': mid} for mid in measures],
              'connections': [{'from_measure_id': f'measure-{i}', 'to_measure_id': f'measure-{i+1}'} for i in range(11)]}
    result, _ = experiment.forecast_series(series, measures, records)
    for row in result['backtests']:
        assert row['target_measure_id'] not in row['training_measure_ids']
        assert all(measures[mid]['period_end']['value'] <= row['origin'] for mid in row['training_measure_ids'])
        assert row['available_in_atlas_at_origin'] is False
    initial = result['backtests'][0]
    initial_ensemble = next(r for r in result['backtests'] if r['model_id'] == 'ensemble_median')
    measures[initial['target_measure_id']]['value'] = 1000
    after, _ = experiment.forecast_series(series, measures, records)
    changed = after['backtests'][0]
    assert (initial['central'], initial['intervals']) == (changed['central'], changed['intervals'])
    assert initial['wis'] != changed['wis']
    changed_ensemble = next(r for r in after['backtests'] if r['id'] == initial_ensemble['id'])
    assert (initial_ensemble['central'], initial_ensemble['intervals']) == (changed_ensemble['central'], changed_ensemble['intervals'])
    assert initial_ensemble['wis'] != changed_ensemble['wis']
    assert len([r for r in result['forecasts'] if r['model_id'] == 'ensemble_median']) == 2


def component_rows():
    return [dict(model_id=model, origin='2026-01-04', target='2026-01-11', horizon_weeks=1,
                 training_measure_ids=['m'+str(i) for i in range(8)], central=value,
                 intervals=[dict(level=level, lower=max(0, value-width), upper=value+width)
                            for level, width in zip(experiment.LEVELS, (2, 4, 8))])
            for model, value in zip(experiment.MODELS, (10, 30, 20))]


def test_ensemble_requires_matched_complete_components_and_nested_quantiles():
    from copy import deepcopy
    rows = component_rows()
    saved = deepcopy(rows)
    combined = experiment.median_ensemble(rows)
    assert combined['central'] == 20
    assert combined['intervals'] == rows[2]['intervals']
    assert combined['model_id'] == 'ensemble_median'
    assert rows == saved
    for invalid in (rows[:2], rows+[rows[0]], [rows[0], rows[0], rows[2]]):
        with pytest.raises(ValueError):
            experiment.median_ensemble(invalid)
    for key, value in [('origin', '2026-01-03'), ('target', '2026-01-12'),
                       ('horizon_weeks', 2), ('training_measure_ids', ['other'])]:
        invalid = deepcopy(rows)
        invalid[1][key] = value
        with pytest.raises(ValueError):
            experiment.median_ensemble(invalid)
    invalid = deepcopy(rows)
    invalid[1]['intervals'][0]['lower'] = 100
    with pytest.raises(ValueError):
        experiment.median_ensemble(invalid)


def test_ensemble_scores_predictions_instead_of_averaging_scores():
    rows = component_rows()
    for row in rows:
        row.update(id='series:'+row['model_id']+':origin:1', observed=25,
                   target_measure_id='target', available_in_atlas_at_origin=False)
        row['mae'], row['wis'] = experiment.score(row, row['observed'])
    ensemble = experiment.median_ensemble(rows)
    assert ensemble['mae'] == 5
    assert ensemble['wis'] == experiment.score(ensemble, 25)[1]
    metrics = experiment.metrics_for(rows+[ensemble])
    metric = next(m for m in metrics if m['model_id'] == 'ensemble_median')
    assert metric['n'] == 1
    assert metric['relative_wis'] == ensemble['wis']/rows[0]['wis']
    assert [c['value'] for c in metric['coverage']] == [0, 0, 1]
    with pytest.raises(ValueError):
        experiment.metrics_for(rows[1:]+[ensemble])
    rows[1]['target_measure_id'] = 'other'
    with pytest.raises(ValueError):
        experiment.median_ensemble(rows)


def test_ensemble_method_contract_requires_exact_membership_and_weights():
    import copy
    import json
    import jsonschema
    schema = json.loads((Path(__file__).parents[1]/'scripts/intelligence/contract.schema.json').read_text())
    methods = schema['properties']['methods']
    jsonschema.validate(experiment.METHODS, methods)
    for change in ('missing', 'weight'):
        rows = copy.deepcopy(experiment.METHODS)
        method = next(m for m in rows if m['id'] == 'ensemble_median')
        if change == 'missing':
            method.pop('components')
        else:
            method['components'][0]['weight'] = 0.5
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(rows, methods)
