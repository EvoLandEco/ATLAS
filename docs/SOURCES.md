# Sources and collection

Source coverage records distinguish discovered links, captured documents, topic exclusions, and access gaps. Publication and capture dates remain separate.

## Source catalog

| Source | Access route | Coverage and collection method |
| --- | --- | --- |
| WHO DON | [DON index](https://www.who.int/emergencies/disease-outbreak-news); [website endpoint](https://www.who.int/api/news/diseaseoutbreaknews) | WHO publishes selected confirmed or potential acute public-health events. The website JSON endpoint is experimental in this adapter. Its two orderings cover publication and modification dates. |
| ECDC CDTR | [Weekly report index](https://www.ecdc.europa.eu/en/publications-and-data/monitoring/weekly-threats-reports); [official RSS page](https://www.ecdc.europa.eu/en/rss-feeds) | Weekly threat synthesis with European relevance and international events. Follow the dated archive and its published next-page links. Select the primary PDF by its attachment title; filenames are not stable. Wednesday uses the latest available publication. |
| EFSA | [Publications](https://www.efsa.europa.eu/en/publications); [News](https://www.efsa.europa.eu/en/news); [Data calls](https://www.efsa.europa.eu/en/calls/data) | Animal health and Biological hazards topic filters define publication and news scope. Data calls use the same topic labels on the call page. Missing topic labels require review. Wiley publications require accessible publisher pages or authorized imports. Publication context remains distinct from an outbreak observation. |
| FAO | [Situation updates](https://www.fao.org/animal-health/situation-updates/en); [AIV page](https://www.fao.org/animal-health/situation-updates/global-aiv-with-zoonotic-potential) | The adapter selects the global avian-influenza report body and its edition date. This mutable page does not provide a complete historical archive. Historical editions require a provider archive or retained copies. |
| RIVM | [RSS page](https://www.rivm.nl/rss) | The Nieuwsberichten feed supports weekly discovery. Backfill follows the published sitemap index and selects news URLs by reported modification date. Article publication dates come from the Publicatiedatum field and remain separate; sitemap completeness and modification accuracy limit historical coverage. |

## Possible sources, not used

Collaboration with BEACON and WOAH WAHIS is not established. ATLAS has no authorized retrieval or import route for either, and neither contributes data to the workflow. Both source entries are disabled in the supplied weekly and backfill configurations.

| Possible source | Potential contribution | Requirement before use |
| --- | --- | --- |
| [WOAH WAHIS](https://www.woah.org/en/what-we-do/animal-health-and-welfare/disease-data-collection/world-animal-health-information-system/) | Official animal health notifications and follow-up reports | Establish collaboration and a provider-authorized document or export route; preserve notification and follow-up identifiers. |
| [BEACON](https://beaconbio.org/) | Curated discovery, source references and errata | Establish collaboration and permission for the intended retrieval, storage and reuse; preserve original reporting sources. |

A public website being readable does not establish an authorized ATLAS integration. Record the agreed access route before enabling either source. Public reports collected directly from other agencies retain those agencies as their sources.

## Regional and national archives

WHO Africa collection follows the [outbreak bulletin archive](https://www.afro.who.int/health-topics/disease-outbreaks/outbreaks-and-other-emergencies-updates), its dated entries, and explicit PDF attachments. The page labels supply edition dates. Coverage notes identify missing weeks in the archive. Report geography comes from the bulletin evidence, not the country embedded in its website URL.

Nigeria NCDC collection follows disease-series links on its [situation report index](https://ncdc.gov.ng/diseases/sitreps). Download names supply edition dates; PDF text supplies observation periods and measurement definitions. Invalid edition dates and unavailable disease tables appear in coverage notes. Index week labels can disagree with PDF reporting weeks. The collector does not convert either into an inferred publication time. Each source pass permits up to 20 disease indexes.

PAHO collection follows the [epidemiological alert archive](https://www.paho.org/en/epidemiological-alerts-and-updates) and each document's download link. The archive includes public health recommendations as well as outbreak alerts. Extraction retains their distinction.

WHO situation updates use the publication website's OData meeting-report collection and its publisher category, Emergency situation update. PublicationDateAndTime determines the publication window; LastModified remains separate. The adapter preserves the publication page URL and downloads the linked PDF within the configured host allowlist. This category includes respiratory surveillance and humanitarian reports, which do not automatically describe individual outbreaks. Access failures on the document host remain coverage gaps.

Explicit attachment selectors require a single link and PDF bytes. Repository application shells and error pages cannot become bulletin evidence. The source adapter version is 0.3.0.

GDELT news discovery remains under evaluation. A ten-result probe received HTTP 429 on 26 September 2026; no news adapter is enabled. APHIS dataset acquisition requires a separate source contract and is not configured.

## Publication dates and coverage
WHO website records expose several date fields. This adapter uses `PublicationDateAndTime` as the editorial publication field and treats `LastModified` separately. It scans publication and modification orderings. General content-management creation dates can reflect migration; inspect them before use.

Dated archives follow published pagination links within the page budget. A configured descending order is verified before using a date cutoff. EFSA data calls are not ordered by publication date, so every bounded archive page is inspected.

RSS has a finite archive window. The collector exposes a short feed window, a page limit, a document cap, unresolved feed labels, or partial retrieval as coverage notes. The latest source issue may predate the Wednesday scan. Manual-access and disabled sources remain present in the coverage table.

The default discovery window is 21 days, with bounded revisits to recently captured URLs. Its coverage is the set actually reached under those bounds. Missed periods can be backfilled with an explicit earlier `collect --since YYYY-MM-DD`; capture time still reflects when the backfill happened. A source outage produces a failed or partial coverage entry. Record the end of an outbreak when a source reports it.

## Access and rights
The [source recovery procedure](SOURCE_RECOVERY.md) covers official coauthor copies, Europe PMC and PMC open access files, Consensus-assisted discovery and institutional repositories. These are reviewed agent access routes, with explicit host allowlists and retained provenance. Keep full-report gaps open when a service returns only metadata or an abstract.

Configure an identifiable user-agent with a research-group contact before deployment. Respect source terms, robots directives, request limits, authentication, and redistribution rules. The fetcher uses an explicit HTTPS host allowlist, bounded redirects, public-address checks, size limits, delays, conditional fetch metadata, and bounded retries. The robots parser respects query rules, wildcard precedence, merged agent groups, and crawl delays. Authorization failures and rate limits suspend that host for the collection; HTTP 429 stops the source pass and records Retry-After when supplied. A blocked source remains a visible coverage gap while an authorized route is arranged.

Keep original source objects and full extraction evidence private. Distribute reviewed paraphrases, source links, hashes, and permitted derived fields. Review the actual source-specific rights before public publication; the repository's software license covers its code and documentation.

## Additional sources
Candidate extensions include other WHO regional offices, Africa CDC, further national public-health institutes, ministries of health, national veterinary authorities, and their official datasets. Add each source through the same onboarding process: define its purpose and jurisdiction; locate an official supported feed/export/page; confirm access and reuse; implement and fixture-test its adapter; verify one live acquisition; compare its content against human review; add coverage expectations and an owner.

Research discovery can later add primary publications, official data repositories, or sequence-repository metadata through separate adapters. Keep literature findings and opportunities separate from official outbreak measurement claims.

## Engineering references
[GitHub Actions scheduled events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) documents timezone-aware scheduling and delivery behavior. [Codex CLI](https://developers.openai.com/codex/cli) and [AGENTS.md guidance](https://developers.openai.com/codex/guides/agents-md) describe repository operation. [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) describes the extraction API contract. Provider- and host-specific behavior is verified during installation rather than inferred from fixture tests.

## UKHSA global outbreak summaries

The [UKHSA annual archive](https://www.gov.uk/government/publications/outbreaks-under-monitoring-in-2026) lists weekly HTML reports about global disease events. The HTML archive collector follows its report links and reads publication dates from each article’s structured metadata. The annual page creation date and week ending dates do not define publication time. Archive rows have no publication date, so discovery records `archive_publication_date_missing`; the captured article supplies that date. The configured year requires review at the start of each year. UKHSA omits a weekly edition when there are no significant developments to report. Reported information may originate from other agencies or media; retain those citations when assessing corroboration.
