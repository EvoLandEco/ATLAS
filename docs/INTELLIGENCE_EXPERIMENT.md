# Intelligence experiments

The Intelligence experiment prepares monitoring signals, source-attributed risk profiles and probabilistic forecasts from a validated ATLAS export. It writes a separate versioned sidecar for an experimental interface. Collection, scientific annotations, sealed reports and the public release remain under their existing workflows.

## Implemented experiment

`scripts/intelligence/build.py` verifies the input bundle, invokes its trusted selector and evaluates eligible reviewed series. The experiment requires reported weekly interval counts and at least twelve consecutive observations. Every model connection must be present in the reviewed series. Conflicts, missing weeks and incompatible periods break the sequence. Cumulative totals cannot supply weekly incident counts.

Forecasts use at least eight training observations and predict a single reported weekly count one or two weeks ahead. All models receive the same training prefixes and targets. No future count enters fitting. The three component methods are:

1. **Persistence random walk.** The innovation distribution contains every preceding adjacent change and its negative. The count process is `Y[t+1] = max(0, Y[t] + innovation)`. Exact enumeration gives the one- and two-step distributions. This is a count-censored empirical random walk related to the Forecast Hub baseline described by [Ray et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC9247236/).
2. **Recent-change random walk.** The same count process uses the last eight signed changes as its innovation distribution. This experiment candidate carries recent directional change into its predictions. The window is fixed across series and test origins.
3. **Gamma–Poisson local level.** The last four reported weekly counts share a constant Poisson rate. Jeffreys prior gives posterior shape `sum(counts) + 0.5` and rate `4`. The predictive count distribution is negative binomial with that shape and success probability `4/5`. A forecast targets one future week, so its marginal distribution is the same at both horizons. The model assumes a locally stable rate and contains no extra variation between weekly rates.

**Median ensemble.** At each origin and horizon, take the median of the three component values separately for the central prediction and each bound of the 50%, 80% and 95% intervals. This equal-weight quantile combination follows [Ray et al. (2023), section 2.6](https://doi.org/10.1016/j.ijforecast.2022.06.005). It requires all three components with identical target dates and training measurement IDs. Backtests also require identical target measurement IDs and observed values. Missing, duplicate or mismatched components stop the export. Component quantiles must be finite, nonnegative and ordered; taking their median preserves that order.

The weights are fixed at one third per component and require no performance fitting. The result is a quantile ensemble, not a fitted mixture of experts or a mixture of probability distributions. Evidence supporting this combination method does not establish its performance on ATLAS data. Ensemble MAE, WIS and coverage are calculated from the combined predictions on the same held-out targets as every component; component scores are not averaged. The monitoring count checks retain their persistence random-walk method.

The random-walk zero boundary is part of the stated stochastic count process. Empirical quantiles use the inverse cumulative distribution, averaging the bounding support values at an exact probability boundary. Gamma–Poisson quantiles use the discrete inverse cumulative distribution. Computation is deterministic and uses no simulated samples or fitted random seed.

Evaluation reports mean absolute error, [weighted interval score](https://epiforecasts.io/scoringutils/reference/wis.html), and coverage of the 50%, 80% and 95% prediction intervals. WIS weights the median absolute error by `0.5` and each interval score by `alpha/2`, then divides by `3.5`. Lower scores are better. Relative WIS divides a model's mean WIS by the persistence model's mean WIS on the same series, horizon and targets. The experiment reports every candidate; it does not declare a general winner from a short test.

## Monitoring and risk evidence

Each eligible one-week target is compared with the preceding-history random-walk 95th predictive quantile. The sidecar retains every check, including non-exceedances. An exceedance is an investigation signal. Its outbreak sensitivity and false-alert rate require adjudicated event labels and prospective evaluation; they cannot be inferred from predictive coverage alone.

The network experiment identifies the first appearance of each country-pair, disease-label set, relationship-kind and direction combination in the selected archive. It uses ATLAS's source-supported geographic relationship units. The first appearance requires all supporting records to be available by publication date. Pre-archive history is unknown. Multiple first-date statements remain visible, and a shared source or disease label does not establish independent events. These flags describe reporting novelty, not pathogen emergence, travel volume or importation probability.

`risk-profiles.json` contains three curated source reviews. Every risk rating names its issuing authority, population and supporting assertion. The profiles organize hazard, exposure, impact, response and remaining questions. They preserve exact quotes and eligible One Health observations and relationships. Superseded or contradicted support requires reassessment. This is an evidence preparation component; it assigns no composite score or numerical risk probability. The structure follows the hazard, exposure, context, likelihood and impact distinctions in the [WHO MS-RRA guidance](https://www.who.int/publications/i/item/9789240119383).

## Time and selection

The September 2026 experiment uses an archive collected after many of its observation periods. Its backtests are retrospective tests in observation order, with source review completed later. They do not reconstruct historical operational performance. Each row records whether its training observations and series review were available in ATLAS at the forecast origin. Publication edition dates, observation periods, capture timestamps and review timestamps retain separate meanings.

The forecast display preserves observation segments, historical origins, target weeks, interval levels, source IDs and excluded measurements. Last-origin extrapolations are historical demonstrations when their target dates precede the experiment date. They are not a current outlook. Results bind to one exact source export and cannot be reused under arbitrary date or source filters without recomputation.

## Reproduce and validate

Use the ATLAS environment and a local Node executable:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_intelligence_experiment.py
PYTHONPATH=src .venv/bin/python scripts/intelligence/build.py \
  --bundle /path/to/validated/structured \
  --node /path/to/node \
  --out /path/to/experiment-directory
```

The reviewed profile configuration binds this experiment to its named source assertions; a different bundle must retain that support or supply a separately reviewed profile configuration. No collection or model extraction runs during this command. It writes `intelligence.json` and `validation.json`. The schema is `scripts/intelligence/contract.schema.json`, version `0.2.0`. Experiment identity binds the input, selector, producer, profile configuration, schema and network method hashes. Generation time is outside the scientific identity. A replay can differ in that timestamp while retaining identical scientific results.

The method ID is `ensemble_median`, labelled “Median ensemble”. Its method metadata includes `combination: "equal_weight_quantile_median"`, `require_all_components: true`, and `components`, an array of `{model_id, weight}` objects for `random_walk`, `recent_changes` and `gamma_poisson`, each with weight `1/3`. Backtest and forecast rows retain the common origin, target, horizon and training IDs. The component rows remain available beside the ensemble. Consumers display the producer's predictions and scores without recomputing them.

Use an empty output directory. Preserve the experiment being compared, verify identical source and selector hashes, and compare every component prediction, score, count check and source reference. Replay into a second empty directory; scientific content and experiment identity must match after excluding generation time. Record the comparison, executed checks, exact hashes and consumer handoff with the private experiment.

Producer checks include full input-bundle verification, JSON Schema validation and tests of predictive support, scoring, reviewed gaps, conflicts, zero counts, training-target separation and historical availability. Run-specific results and validation receipts belong with their experiment output. Consumer adoption and public publication are separate outcomes.

## Release dependency

A public Analysis view consumes this experiment only alongside its exact source export. Follow the [Analysis attachment handoff](PUBLICATION_HANDOFF.md#analysis-attachment): validate the source export ID, site SHA-256 and selector SHA-256, authorize the exact data and schema files, and stage them before activating their release descriptor. Regenerate the experiment for a different base bundle. If no matching experiment is published, Analysis remains unavailable. Consumer presentation and dataset publication have separate verification receipts.

## Development path

**Threat monitoring:** add a dated signal ledger keyed to first capture and explicit source revisions. Source-issued risk changes, reviewed new host observations and reported geographic connections can enter an evidence review queue. Record every disposition to measure alert precision, workload and timeliness. Keep reporting volume and source availability alongside the signals. Longer, comparable histories can support a seasonally adjusted count detector such as [Farrington Flexible](https://pmc.ncbi.nlm.nih.gov/articles/PMC3692796/).

**Risk analysis:** define a question, population, location, horizon and consequence before assessment. Extend curated risk annotations to source-attributed ratings and separate analyst judgments, including negative findings, unresolved evidence and response capacity. A multidisciplinary review can assign likelihood, impact and confidence for that exact question. Quantitative importation or spillover models require relevant exposure denominators, observed outcomes and a validated sampling process; reporting-network strength cannot substitute for them.

**Forecasting:** compare an overdispersed dynamic count model with the three baselines, then add seasonality where several comparable seasons exist. Freeze each forecast with the evidence and review state available at issuance. Keep first-reported and revised targets separate. Assess models over multiple surveillance programmes and rising and falling periods; report paired score comparisons, interval coverage and missing-target rates. More source coverage and better review data strengthen this evaluation before additional model complexity does.

**One Health research:** evaluate whether source-reviewed animal, food or environmental observations add forecast value only where endpoint identity, temporal order, measurement scope and a plausible exposure pathway are established. Compare models with and without those predictors using the same held-out targets. A connection or shared pathogen alone cannot establish predictive lead time or spillover probability.

The next release decision should be based on frozen prospective predictions and adjudicated monitoring outcomes. The experimental interface provides evidence drill-through, model comparison and uncertainty inspection while these assessments accumulate.
