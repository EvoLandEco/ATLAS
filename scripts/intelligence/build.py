"""Retrospective monitoring, risk evidence and count forecasting experiments."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess

from atlas.network_analysis import units_from_site
from atlas.site_export import verify_site
from atlas.util import digest
import jsonschema

VERSION = '0.2.0'
LEVELS = (0.5, 0.8, 0.95)
MODELS = ('random_walk', 'recent_changes', 'gamma_poisson')
ENSEMBLE = 'ensemble_median'
MODEL_NOTES = {
    'random_walk': 'Empirical count random walk. Innovations are all preceding adjacent changes and their negatives; count paths are censored at zero at each step.',
    'recent_changes': 'Empirical count random walk with innovations drawn from the last eight adjacent changes, preserving their signed distribution. Count paths are censored at zero at each step.',
    'gamma_poisson': 'Constant weekly Poisson rate over the last four weeks with Jeffreys prior. The Gamma posterior gives an exact negative-binomial predictive distribution for a single future week.',
}
METHODS = [
    {'id': ENSEMBLE, 'label': 'Median ensemble',
     'description': 'Equal-weight median of the three component predictions at each quantile, with all components matched by origin, target, horizon and training measurements. Weights are fixed; no ensemble fitting is performed.',
     'url': 'https://doi.org/10.1016/j.ijforecast.2022.06.005',
     'combination': 'equal_weight_quantile_median', 'require_all_components': True,
     'components': [{'model_id': model, 'weight': 1/3} for model in MODELS]},
    {'id': 'random_walk', 'label': 'Persistence random walk', 'description': MODEL_NOTES['random_walk'], 'url': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9247236/'},
    {'id': 'recent_changes', 'label': 'Recent-change random walk', 'description': MODEL_NOTES['recent_changes'], 'url': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC13015638/'},
    {'id': 'gamma_poisson', 'label': 'Gamma–Poisson local level', 'description': MODEL_NOTES['gamma_poisson'], 'url': None},
    {'id': 'wis', 'label': 'Weighted interval score', 'description': 'Mean of the median absolute error and central 50%, 80% and 95% interval scores, weighted by 0.5 and alpha/2, divided by 3.5. Lower is better.', 'url': 'https://epiforecasts.io/scoringutils/reference/wis.html'},
    {'id': 'risk_evidence', 'label': 'Structured risk evidence', 'description': 'Source-attributed hazard, exposure, impact and response evidence with population-specific assessments and explicit unknowns. ATLAS assigns no composite risk score.', 'url': 'https://www.who.int/publications/i/item/9789240119383'},
    {'id': 'count_exceedance', 'label': 'Predictive exceedance', 'description': 'Observed count above the random-walk one-week 95th predictive quantile. An unadjusted investigation signal, without outbreak labels or a calibrated false-alert rate.', 'url': 'https://stacks.cdc.gov/view/cdc/164155'},
    {'id': 'network_first_appearance', 'label': 'First reported country connection', 'description': 'First publication date of a country-pair, disease and relationship-kind combination in the selected archive. Direction is retained when supplied. This measures archive novelty, not biological emergence.', 'url': 'https://github.com/EvoLandEco/ATLAS/blob/main/docs/NETWORK_ANALYSIS.md'},
]


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def discrete_quantile(mass, probability):
    total = sum(mass.values())
    cumulative = 0.0
    ordered = sorted(mass.items())
    for index, (value, weight) in enumerate(ordered):
        cumulative += weight
        if math.isclose(cumulative, probability*total, rel_tol=0, abs_tol=1e-12) and index+1 < len(ordered):
            return (value+ordered[index+1][0])/2
        if cumulative >= probability * total - 1e-12:
            return value
    raise ValueError('Empty predictive distribution')


def forecast(values, horizon, model):
    if horizon not in (1, 2) or len(values) < 8:
        raise ValueError('Forecast requires eight observations and a one or two week horizon')
    if any(not math.isfinite(y) or y < 0 or int(y) != y for y in values):
        raise ValueError('Forecast target must contain finite, nonnegative integer counts')
    probabilities = sorted({0.05, 0.5, *[(1-level)/2 for level in LEVELS], *[(1+level)/2 for level in LEVELS]})
    if model == 'gamma_poisson':
        # Each target is one weekly count, not a sum over the forecast horizon.
        shape = sum(values[-4:]) + 0.5
        p = 4 / 5
        result, cumulative, index = {}, 0.0, 0
        for value in range(100000):
            log_mass = math.lgamma(value+shape)-math.lgamma(shape)-math.lgamma(value+1)+shape*math.log(p)+value*math.log1p(-p)
            cumulative += math.exp(log_mass)
            while index < len(probabilities) and cumulative >= probabilities[index]:
                result[probabilities[index]] = value
                index += 1
            if index == len(probabilities):
                return result
        raise ValueError('Predictive quantile exceeds the experiment count bound')
    changes = [b-a for a, b in zip(values, values[1:])]
    if model == 'random_walk':
        changes += [-x for x in changes]
    elif model == 'recent_changes':
        changes = changes[-8:]
    else:
        raise ValueError('Unknown forecast model')
    innovations = Counter(changes)
    mass = {values[-1]: 1.0}
    for _ in range(horizon):
        following = defaultdict(float)
        for current, weight in mass.items():
            for change, count in innovations.items():
                following[max(0, current+change)] += weight*count/len(changes)
        mass = following
    return {p: discrete_quantile(mass, p) for p in probabilities}


def prediction(values, horizon, model):
    quantiles = forecast(values, horizon, model)
    return {'central': quantiles[0.5], 'intervals': [
        {'level': level, 'lower': quantiles[(1-level)/2], 'upper': quantiles[(1+level)/2]} for level in LEVELS]}


def score(prediction, observed):
    absolute_error = abs(prediction['central']-observed)
    total = 0.5*absolute_error
    for interval in prediction['intervals']:
        alpha = 1-interval['level']
        lower, upper = interval['lower'], interval['upper']
        total += alpha/2*(upper-lower) + max(lower-observed, 0) + max(observed-upper, 0)
    return absolute_error, total/(len(prediction['intervals'])+0.5)



def median_ensemble(rows):
    """Combine one complete, aligned set of component predictive quantiles."""
    if len(rows) != len(MODELS) or {r['model_id'] for r in rows} != set(MODELS):
        raise ValueError('Ensemble requires exactly one prediction from each component')
    first = rows[0]
    keys = ('origin', 'target', 'horizon_weeks', 'training_measure_ids')
    if 'observed' in first:
        keys += ('observed', 'target_measure_id', 'available_in_atlas_at_origin')
    if any(any(key not in r or r[key] != first[key] for key in keys) or
           ('observed' in r) != ('observed' in first) for r in rows):
        raise ValueError('Ensemble component origins, targets or training measurements differ')
    for row in rows:
        intervals = row['intervals']
        if [i['level'] for i in intervals] != list(LEVELS):
            raise ValueError('Component interval levels differ')
        quantiles = [i['lower'] for i in reversed(intervals)] + [row['central']] + [i['upper'] for i in intervals]
        if any(not math.isfinite(q) or q < 0 for q in quantiles) or quantiles != sorted(quantiles):
            raise ValueError('Component quantiles must be finite, nonnegative and ordered')
    result = {key: first[key] for key in keys}
    result.update(model_id=ENSEMBLE, central=statistics.median(r['central'] for r in rows),
                  intervals=[dict(level=level, **{bound: statistics.median(r['intervals'][i][bound] for r in rows)
                                                 for bound in ('lower', 'upper')})
                             for i, level in enumerate(LEVELS)])
    if 'observed' in first:
        prefix, model, origin, horizon = first['id'].rsplit(':', 3)
        result['id'] = f'{prefix}:{ENSEMBLE}:{origin}:{horizon}'
        result['mae'], result['wis'] = score(result, result['observed'])
    return result


def segments(series, measures):
    """Only exact reviewed connections can join model observations."""
    rows = sorted((measures[x['measure_id']] for x in series['members']), key=lambda m: (m['observation_date'] or '', m['measure_id']))
    edges = {(e['from_measure_id'], e['to_measure_id']) for e in series['connections']}
    duplicate_dates = Counter(m['observation_date'] for m in rows)
    result, excluded = [], []
    for m in rows:
        reason = None
        if m['conflict_set'] or duplicate_dates[m['observation_date']] > 1:
            reason = 'Conflicting or duplicated observation date'
        elif m['value_status'] != 'reported' or m['count_kind'] != 'interval' or m['value'] is None or m['value'] < 0 or not float(m['value']).is_integer():
            reason = 'Not a reported nonnegative interval count'
        elif not m['period_start']['value'] or not m['period_end']['value'] or (date.fromisoformat(m['period_end']['value'])-date.fromisoformat(m['period_start']['value'])).days != 6:
            reason = 'Not an explicit seven-day observation'
        if reason:
            excluded.append({'measure_id': m['measure_id'], 'reason': reason})
            continue
        prior = result[-1][-1] if result else None
        adjacent = prior is not None and (prior['measure_id'], m['measure_id']) in edges and date.fromisoformat(m['period_start']['value']) == date.fromisoformat(prior['period_end']['value'])+timedelta(days=1)
        if adjacent:
            result[-1].append(m)
        else:
            result.append([m])
    return result, excluded


def metrics_for(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r['model_id'], r['horizon_weeks'])].append(r)
    cohorts = {}
    for key, group in groups.items():
        cohort = {(r['origin'], r['target'], r['target_measure_id'], tuple(r['training_measure_ids']), r['observed']) for r in group}
        if len(cohort) != len(group):
            raise ValueError('Duplicate scoring target')
        cohorts[key] = cohort
    for (model, horizon), cohort in cohorts.items():
        if cohort != cohorts.get(('random_walk', horizon)):
            raise ValueError('Scores require identical targets and training inputs across models')
    result = []
    for (model, horizon), group in sorted(groups.items()):
        result.append({'model_id': model, 'horizon_weeks': horizon, 'n': len(group),
                       'mae': statistics.mean(r['mae'] for r in group), 'wis': statistics.mean(r['wis'] for r in group),
                       'coverage': [{'level': level, 'value': statistics.mean(next(i['lower'] <= r['observed'] <= i['upper'] for i in r['intervals'] if i['level'] == level) for r in group)} for level in LEVELS],
                       'baseline_id': 'random_walk', 'relative_wis': None})
    baseline = {r['horizon_weeks']: r['wis'] for r in result if r['model_id'] == 'random_walk'}
    for r in result:
        r['relative_wis'] = r['wis']/baseline[r['horizon_weeks']] if baseline[r['horizon_weeks']] else None
    return result


def forecast_series(series, measures, records):
    runs, excluded = segments(series, measures)
    points, backtests, outlook, signals, checks = [], [], [], [], []
    for segment_index, run in enumerate(runs):
        for m in run:
            r = records[m['source_reference']['record_id']]
            points.append({'date': m['period_end']['value'], 'value': m['value'], 'measure_id': m['measure_id'],
                           'record_id': r['id'], 'source_id': r['document_id'], 'publication': r['publication'], 'capture': r['capture'], 'segment': segment_index})
        for stop in range(8, len(run)):
            training = run[:stop]
            values = [m['value'] for m in training]
            origin = training[-1]['period_end']['value']
            for horizon in (1, 2):
                if stop+horizon > len(run):
                    continue
                target = run[stop+horizon-1]
                target_date = target['period_end']['value']
                available = all(m['capture'][:10] <= origin and m['publication'][:10] <= origin for m in training) and series['reviewed_at'][:10] <= origin
                for model in MODELS:
                    pred = prediction(values, horizon, model)
                    mae, wis = score(pred, target['value'])
                    backtests.append({'id': f"{series['series_id']}:{model}:{origin}:{horizon}", 'model_id': model,
                                      'origin': origin, 'target': target_date, 'horizon_weeks': horizon,
                                      'training_measure_ids': [m['measure_id'] for m in training],
                                      'observed': target['value'], 'target_measure_id': target['measure_id'],
                                      'available_in_atlas_at_origin': available, 'mae': mae, 'wis': wis, **pred})
                backtests.append(median_ensemble(backtests[-len(MODELS):]))
                if horizon == 1:
                    threshold = discrete_quantile_for_upper(values)
                    r = records[target['source_reference']['record_id']]
                    expected = prediction(values, 1, 'random_walk')['central']
                    checks.append({'date': target_date, 'origin': origin, 'observed': target['value'],
                                   'expected': expected, 'threshold': threshold, 'above_threshold': target['value'] > threshold,
                                   'measure_id': target['measure_id'], 'record_id': r['id'], 'source_id': r['document_id']})
                    if target['value'] > threshold:
                        signals.append({'id': 'signal:'+target['measure_id'], 'kind': 'count_exceedance', 'label': series['label'],
                                        'date': target_date, 'series_id': series['series_id'], 'observed': target['value'],
                                        'expected': expected, 'threshold': threshold,
                                        'unit': 'reported people', 'method_id': 'count_exceedance', 'record_ids': [r['id']],
                                        'source_ids': [r['document_id']], 'relationship_ids': [],
                                        'interpretation': 'Count exceeds the preceding-history one-week 95th predictive quantile. Investigation signal; outbreak status is unassessed.',
                                        'eligibility': {'status': 'retrospective_only', 'reason': 'Source observations were collected after this historical signal date.'}})
    if runs and len(runs[-1]) >= 8:
        training = runs[-1]
        origin = training[-1]['period_end']['value']
        for model in MODELS:
            for horizon in (1, 2):
                outlook.append({'model_id': model, 'origin': origin, 'target': (date.fromisoformat(origin)+timedelta(days=7*horizon)).isoformat(),
                                'horizon_weeks': horizon, 'training_measure_ids': [m['measure_id'] for m in training],
                                **prediction([m['value'] for m in training], horizon, model)})
        components = list(outlook)
        for horizon in (1, 2):
            outlook.append(median_ensemble([r for r in components if r['horizon_weeks'] == horizon]))
    return {'id': series['series_id'], 'label': series['label'], 'outcome': measures[series['members'][0]['measure_id']]['label'],
            'unit': 'reported people per week', 'location': 'Nigeria', 'operation': series['operation'],
            'reviewed_at': series['reviewed_at'], 'status': 'retrospective_experiment', 'observations': points,
            'segments': [[m['measure_id'] for m in run] for run in runs], 'excluded': excluded,
            'backtests': backtests, 'metrics': metrics_for(backtests), 'forecasts': outlook, 'monitoring_checks': checks,
            'limitations': series['limitations'] + ['Forecasts target reported counts. Historical capture and editorial availability are not reconstructed; extrapolations are not a current outlook.'],
            'source_ids': sorted({p['source_id'] for p in points})}, signals


def discrete_quantile_for_upper(values):
    changes = [b-a for a, b in zip(values, values[1:])]
    changes += [-x for x in changes]
    return discrete_quantile(Counter(max(0, values[-1]+x) for x in changes), 0.95)


def network_signals(site, view):
    records = {r['id']: r for r in site['records']}
    diseases = {r['record_id']: tuple(sorted(r['disease_ids'])) for r in site['disease_reviews']}
    eligible = set(view['relationship_ids'])
    blocks = defaultdict(list)
    for unit in units_from_site(site)[0]:
        if unit['id'] not in eligible:
            continue
        pair = (unit['from_country'], unit['to_country']) if unit['directed'] else tuple(sorted((unit['from_country'], unit['to_country'])))
        topic = tuple(sorted({d for rid in unit['record_ids'] for d in diseases.get(rid, ())}))
        if not topic:
            continue
        key = (unit['kind'], unit['directed'], pair, topic)
        unit['publication_day'] = max(records[r]['publication'][:10] for r in unit['record_ids'])
        blocks[key].append(unit)
    labels = {d['id']: d['label'] for d in site['diseases']}
    result = []
    for key, units in sorted(blocks.items()):
        first = min(u['publication_day'] for u in units)
        at_first = [u for u in units if u['publication_day'] == first]
        rids = sorted({rid for u in at_first for rid in u['record_ids']})
        result.append({'id': 'network:'+digest(key)[:24], 'kind': 'network_first_appearance',
                       'label': f"{', '.join(labels[d] for d in key[3])}: {' → ' .join(key[2]) if key[1] else ' ↔ '.join(key[2])}",
                       'date': first, 'series_id': None, 'observed': len(at_first), 'expected': None, 'threshold': None,
                       'unit': 'source relationship statements', 'method_id': 'network_first_appearance', 'record_ids': rids,
                       'source_ids': sorted({records[r]['document_id'] for r in rids}), 'relationship_ids': sorted(u['id'] for u in at_first),
                       'interpretation': 'First appearance of this disease and country connection in the selected archive. Pre-archive history is unknown. Statements may repeat an episode. It does not establish a new route of transmission.',
                       'eligibility': {'status': 'retrospective_only', 'reason': 'Novelty is relative to this collected corpus, not all surveillance or historical knowledge.'}})
    return sorted(result, key=lambda r: (r['date'], r['id']), reverse=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--node', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError('Experiment output directory must be empty')
    args.out.mkdir(parents=True, exist_ok=True)
    integrity = verify_site(args.bundle)
    site = read(args.bundle/'atlas-site.json')
    view = json.loads(subprocess.check_output([args.node, str(Path(__file__).with_name('select.mjs')), str(args.bundle)]))
    records = {r['id']: r for r in site['records']}
    measures = {m['measure_id']: m for m in site['metrics']['measures']}
    forecasts, signals, audit = [], [], []
    for series in view['reviewed_series']:
        if series['operation'] != 'reported_interval_counts':
            audit.append({'series_id': series['series_id'], 'status': 'excluded', 'reason': 'Cumulative totals cannot supply weekly incident counts.'})
            continue
        runs, _ = segments(series, measures)
        longest = max(map(len, runs), default=0)
        if longest < 12:
            audit.append({'series_id': series['series_id'], 'status': 'excluded', 'reason': f'Longest reviewed consecutive segment has {longest} weeks; experiment requires twelve.'})
            continue
        audit.append({'series_id': series['series_id'], 'status': 'included', 'reason': 'Reviewed weekly counts with at least twelve consecutive observations.'})
        forecast_result, count_signals = forecast_series(series, measures, records)
        forecasts.append(forecast_result)
        signals.extend(count_signals)
    signals.extend(network_signals(site, view))
    profiles = risk_profiles(site, view)
    used = {sid for s in forecasts for sid in s['source_ids']} | {sid for s in signals for sid in s['source_ids']} | {sid for p in profiles for sid in p['source_ids']}
    sources = [{'id': d['id'], 'title': d['title'], 'url': d['url'], 'publication': d['publication'], 'capture': d['capture'], 'text_sha256': d['text_sha256']} for d in site['documents'] if d['id'] in used]
    identity = {'site_sha256': sha(args.bundle/'atlas-site.json'), 'selector_sha256': sha(args.bundle/'view.mjs'),
                'producer_sha256': sha(__file__), 'profile_sha256': sha(Path(__file__).with_name('risk-profiles.json')),
                'schema_sha256': sha(Path(__file__).with_name('contract.schema.json')),
                'selection_adapter_sha256': sha(Path(__file__).with_name('select.mjs')),
                'network_method_sha256': sha(Path(__file__).parents[2]/'src/atlas/network_analysis.py'),
                'method_version': VERSION}
    export_id = digest({'manifest_sha256': sha(args.bundle/'manifest.json'), 'map_snapshot_sha256': site['snapshot']['source_snapshot_sha256']})
    result = {'schema_version': VERSION, 'experiment_id': digest(identity), 'generated_at': datetime.now(timezone.utc).isoformat(),
              'source_export_id': export_id, 'input_identity': identity,
              'time_basis': 'retrospective_observation_order', 'status': 'research_experiment',
              'scope': {'publication_from': site['snapshot']['publication_from'], 'publication_until': site['snapshot']['publication_until'],
                        'capture_until': site['snapshot']['capture_until'], 'documents': len(site['documents']), 'records': len(site['records']),
                        'forecast_series': len(forecasts), 'risk_profiles': len(profiles)},
              'limitations': ['Historical reports were captured in September 2026. Backtests measure prediction from earlier observations, not historical operational lead time.',
                              'Monitoring flags support evidence review. Their sensitivity and false-alert rate are unvalidated because adjudicated outbreak labels are absent.',
                              'Country connections describe source statements. They do not estimate movement volume, importation probability or disease burden.',
                              'Source risk assessments retain their original population and date. No ATLAS probability or composite risk score is assigned.',
                              'The small series selection cannot establish general forecasting performance. Prediction intervals require prospective calibration.'],
              'methods': METHODS, 'sources': sources, 'series_audit': audit,
              'monitoring': sorted(signals, key=lambda r: (r['date'], r['id']), reverse=True), 'risk_profiles': profiles, 'forecast_series': forecasts}
    jsonschema.validate(result, read(Path(__file__).with_name('contract.schema.json')))
    write(args.out/'intelligence.json', result)
    write(args.out/'validation.json', {'status': 'passed', 'input_bundle': integrity, 'experiment_id': result['experiment_id'],
                                     'source_export_id': export_id, 'intelligence_sha256': sha(args.out/'intelligence.json'),
                                     'strict_historical_backtests': sum(b['available_in_atlas_at_origin'] for s in forecasts for b in s['backtests']),
                                     'backtests': sum(len(s['backtests']) for s in forecasts),
                                     'conflicted_measurements_excluded': sum(len(s['excluded']) for s in forecasts)})
    print(json.dumps({'experiment_id': result['experiment_id'], 'series': len(forecasts), 'signals': len(signals), 'profiles': len(profiles)}))


def risk_profiles(site, view):
    assertions = {a['id']: a for a in site['assertions']}
    evidence = {e['id']: e for e in site['evidence']}
    records = {r['id']: r for r in site['records']}
    active = set(view['assertion_ids'])-set(view['superseded_assertion_ids'])
    comparison_ids = set(view['comparison_ids'])
    contested = {aid for c in site['comparisons'] if c['id'] in comparison_ids and c['kind'] == 'contradiction' for aid in c['participant_ids']}
    output = []
    for profile in read(Path(__file__).with_name('risk-profiles.json')):
        r = records[profile['record_id']]
        aids = {aid for dimension in profile['dimensions'] for aid in dimension['assertion_ids']}
        aids.update(aid for assessment in profile['assessments'] for aid in assessment['assertion_ids'])
        if not aids <= active or any(assertions[aid]['record_id'] != r['id'] for aid in aids):
            raise ValueError('Risk profile support is absent from the selected evidence')
        if aids.intersection(contested):
            raise ValueError('Risk profile includes contested evidence and needs reassessment')
        profile['evidence'] = [{'assertion_id': aid, 'text': assertions[aid]['text'],
                                'quotes': [{'id': eid, 'quote': evidence[eid]['quote'], 'page': evidence[eid]['page'], 'quote_sha256': evidence[eid]['quote_sha256']} for eid in assertions[aid]['evidence_ids']]} for aid in sorted(aids)]
        profile['source_ids'] = [r['document_id']]
        profile['publication'] = r['publication']
        profile['capture'] = r['capture']
        profile['probability'] = None
        profile['method_id'] = 'risk_evidence'
        profile['review_status'] = 'source_checked_experiment'
        profile['one_health'] = {'nodes': [n for n in view['one_health']['nodes'] if n['record_id'] == r['id']],
                                 'relations': [n for n in view['one_health']['relations'] if r['id'] in n['record_ids']]}
        output.append(profile)
    return output


if __name__ == '__main__':
    main()
