# Technical review: time windows and epidemiological links

Review date: 26 September 2026. This focused review examines five research papers and the selected ATLAS map data: 114 report entries from 49 documents, grouped into 34 reporting topics. The broader extraction corpus contains 91 publications.

## Assessment

A reporting window is useful for comparing periods and reducing visual clutter. Geographic links are useful when their meaning comes from a source statement about travel, a shared event or a proposed epidemiological relationship. A shared disease label identifies material to compare. Appearance in the same bulletin identifies a reporting relationship. Neither supplies a biological link between places.

The 119 pairwise links assessed here comprise 48 matches on a broad disease group and 71 pairs mentioned in the same document. These are descriptive properties of the collection. Their epidemiological relevance is limited by the construction rule: a long bulletin creates many pairs, and a broad disease category connects different subtypes, hosts and episodes. Those counts do not measure transmission, outbreak similarity or statistical significance.

## Findings from the literature

| Study | Relevant finding | Implication for ATLAS |
| --- | --- | --- |
| [Valentin et al., 2023: Dissemination of information in event-based surveillance](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0285341) | The study traces outbreak information through primary sources, secondary sources and surveillance aggregators. Its network edges describe information flow. | Represent reporting coverage in a document–topic network. A bulletin that covers two places supplies a common source, not an epidemiological relationship between those places. |
| [Campbell et al., 2019: Bayesian inference of transmission chains](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1006930) | Combining contact information with symptom timing and genomes improves transmission reconstruction in the study's simulated outbreaks. | Give priority to explicit contact, shared exposure and source-described links. The present corpus lacks the case-level inputs needed to fit this transmission model. |
| [Campbell et al., 2018: When are pathogen genome sequences informative of transmission events?](https://journals.plos.org/plospathogens/article?id=10.1371/journal.ppat.1006885) | The resolution of transmission histories depends on genetic diversity accumulating on epidemiological timescales. Many simulated transmission pairs have identical genomes. | Even a matching subtype or clade is insufficient to assign who infected whom. A broad label such as avian influenza is a topic grouping. |
| [Holme, 2013: Epidemiologically optimal static networks from temporal network data](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003142) | The study compares static representations of temporal contact data. Networks accumulating all contacts over the full observation period perform worse than some alternatives for the evaluated epidemic simulations. | Preserve dates and allow window selection. This supports attention to temporal structure; it does not validate a particular slider width or turn publication dates into contact times. |
| [Kulldorff et al., 2005: A space–time permutation scan statistic for disease outbreak detection](https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.0020059) | The method detects unusual concentrations using case data, with adjustment for spatial and temporal variation and multiple testing. This formulation does not require population denominators. | Statistical clusters require an appropriate case series and a stated null model. Selected articles, overlapping cumulative totals and country reference points do not provide that input. |

The implications in the last column are design judgments for ATLAS. The papers do not evaluate this dataset or validate its link annotations.

## Link rules for the map

| Type | Required source information | Direction | Current examples |
| --- | --- | --- | --- |
| Reported movement | Explicit travel, importation or medical transfer connecting two named places, with a quotation supporting the connection. | The direction described in the report. | DRC to France, Germany and Uganda for Bundibugyo reporting; Guatemala to Belize for measles reporting. |
| Shared event | A source explicitly associates cases in both places with the same named gathering or exposure event. | Undirected. | Measles cases in Sweden and Finland associated with the Västernorrland festival. |
| Source hypothesis | A source explicitly proposes an epidemiological connection or a common introduction mechanism and names both places. | Undirected in this map. | The unconfirmed cholera link between South Ubangi and the Central African Republic; the suggested migratory-bird mechanism for H5N1 introductions into Australia and New Zealand. |

These seven connections offer concrete questions to investigate. Travel can identify a plausible importation context; a common event can guide exposure investigation; a source hypothesis can identify evidence to seek. Each connection retains its limits. Medical evacuation describes treatment movement, travel history does not establish the infection site, and a common proposed introduction mechanism does not establish one transmission chain.

The 13 existing source assessments remain in the evidence panel. They include outbreak follow-up, exposure, suspected transmission, secondary cases and unresolved questions. Assessments involving hosts or cases without geographic endpoints use a local diagram. The map does not invent an origin for Frankfurt airport malaria or assign patient coordinates to Panama's secondary cases.

The source–topic network retains document coverage without projecting every shared bulletin into a geographic edge. Disease groups remain descriptive topic metadata. The geographic link builder accepts explicit source annotations rather than generating pairs from topic labels or proximity.

## Date window

The two handles select an inclusive interval. Exact date fields support keyboard entry. Publication mode includes reports whose publication or edition date falls in that interval. Capture mode includes reports saved by ATLAS during the interval. The map, source network, chronology and supporting assessments use the same selection.

A link appears only when every supporting report entry is inside the window. A later assessment appears when its supporting report enters the window. Play advances both handles by one day and preserves the selected width. The full 93-date interval fills the available timeline; choose a shorter interval to animate it.

This window describes reporting or collection activity. Source observation periods, travel dates and symptom dates remain attached to the findings. A July bulletin may describe an April exposure. Selecting July includes that report; it does not date the exposure to July. An empty window means no selected reports, rather than no disease occurrence.

## Implementation checks and evaluation

The link validator checks link types, direction rules, geographic bounds, location precision and quoted support. Demo checks cover inclusive dates, a single-day window, handle crossings, fixed-width playback, publication and capture dates, link filtering and preservation of conflicting source counts. The source annotations identify the exact report and claim used for each connection.

These checks establish software behaviour and traceability. Epidemiological performance needs a reference set of positive and negative links reviewed against the original reports. Measure agreement on link type, endpoints, direction and uncertainty, and record false connections and missed source links. A separate event-date dataset would be needed to evaluate transmission timing or spatiotemporal clustering.

See [Relationship rules](RELATIONSHIP_RULES.md) for operating definitions and [Evaluation](EVALUATION.md) for the wider workflow assessment.
