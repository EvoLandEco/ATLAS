# Source catalog and onboarding

Source coverage records distinguish discovered links, captured documents, topic exclusions, and access gaps. Publication and capture dates remain separate.

## Source catalog

| Source | Official access evidence | Scope and operating decision |
| --- | --- | --- |
| WHO DON | [DON index](https://www.who.int/emergencies/disease-outbreak-news); [website endpoint](https://www.who.int/api/news/diseaseoutbreaknews) | WHO publishes selected confirmed or potential acute public-health events. The website JSON endpoint is experimental in this adapter. Its two orderings cover publication and modification dates. |
| ECDC CDTR | [Weekly report index](https://www.ecdc.europa.eu/en/publications-and-data/monitoring/weekly-threats-reports); [official RSS page](https://www.ecdc.europa.eu/en/rss-feeds) | Weekly threat synthesis with European relevance and international events. Follow the dated archive and its published next-page links. Select the primary PDF by its attachment title; filenames are not stable. Wednesday uses the latest available publication. |
| EFSA | [Publications](https://www.efsa.europa.eu/en/publications); [News](https://www.efsa.europa.eu/en/news); [Data calls](https://www.efsa.europa.eu/en/calls/data) | Animal health and Biological hazards topic filters define publication and news scope. Data calls use the same topic labels on the call page. Missing topic labels require review. Wiley publications require accessible publisher pages or authorized imports. Publication context remains distinct from an outbreak observation. |
| FAO | [Situation updates](https://www.fao.org/animal-health/situation-updates/en); [AIV page](https://www.fao.org/animal-health/situation-updates/global-aiv-with-zoonotic-potential) | The adapter selects the global avian-influenza report body and its edition date. This mutable page does not provide a complete historical archive. Historical editions require a provider archive or retained copies. |
| RIVM | [RSS page](https://www.rivm.nl/rss) | The Nieuwsberichten feed supports weekly discovery. Backfill follows the published sitemap index and selects news URLs by reported modification date. Article publication dates remain separate; sitemap completeness and modification accuracy limit historical coverage. |
| WOAH WAHIS | [Official system description](https://www.woah.org/en/what-we-do/animal-health-and-welfare/disease-data-collection/world-animal-health-information-system/) | Official country animal-health reports and notifications. Integration uses provider-authorized local documents or exports; record notification/follow-up identifiers explicitly. |
| BEACON | [Public site](https://beaconbio.org/en); [About](https://beaconbio.org/en/about); [Resources](https://beaconbio.org/en/resources) | Curated discovery and errata. Systematic collection requires written permission under section 6 of the [BEACON terms](https://beaconbio.org/beaconTermsOfUse.pdf). Use authorized imports and follow through to original official reports. Request archive access, corrections, attribution requirements, and permission for research-group storage from ceid@bu.edu. |

## Publication dates and coverage
WHO website records expose several date fields. This adapter uses `PublicationDateAndTime` as the editorial publication field and treats `LastModified` separately. It scans publication and modification orderings. General content-management creation dates can reflect migration; inspect them before use.

Dated archives follow published pagination links within the page budget. A configured descending order is verified before using a date cutoff. EFSA data calls are not ordered by publication date, so every bounded archive page is inspected.

RSS has a finite archive window. The collector exposes a short feed window, a page limit, a document cap, unresolved feed labels, or partial retrieval as coverage notes. The latest source issue may predate the Wednesday scan. Manual-access and disabled sources remain present in the coverage table.

The default discovery window is 21 days, with bounded revisits to recently captured URLs. Its coverage is the set actually reached under those bounds. Missed periods can be backfilled with an explicit earlier `collect --since YYYY-MM-DD`; capture time still reflects when the backfill happened. A source outage produces a failed or partial coverage entry. A complete epidemiological all-clear requires its own explicit source statement.

## Access and rights
Configure an identifiable user-agent with a research-group contact before deployment. Respect source terms, robots directives, request limits, authentication, and redistribution rules. The fetcher uses an explicit HTTPS host allowlist, bounded redirects, public-address checks, size limits, delays, conditional fetch metadata, and bounded retries. The robots parser respects query rules, wildcard precedence, merged agent groups, and crawl delays. Authorization failures and rate limits suspend that host for the collection; HTTP 429 stops the source pass and records Retry-After when supplied. A blocked source remains a visible coverage gap while an authorized route is arranged.

Keep original source objects and full extraction evidence private. Distribute reviewed paraphrases, source links, hashes, and permitted derived fields. Review the actual source-specific rights before public publication; the repository's software license covers its code and documentation.

## Additional sources
Candidate extensions include WHO regional offices, PAHO official alerts, Africa CDC, national public-health institutes, ministries of health, national veterinary authorities, and their official datasets. Add each source through the same onboarding process: define its purpose and jurisdiction; locate an official supported feed/export/page; confirm access and reuse; implement and fixture-test its adapter; verify one live acquisition; compare its content against human review; add coverage expectations and an owner.

Research discovery can later add primary publications, official data repositories, or sequence-repository metadata through separate adapters. Keep literature findings and opportunities separate from official outbreak measurement claims.

## Engineering references
[GitHub Actions scheduled events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) documents timezone-aware scheduling and delivery behavior. [Codex CLI](https://developers.openai.com/codex/cli) and [AGENTS.md guidance](https://developers.openai.com/codex/guides/agents-md) describe repository operation. [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) describes the extraction API contract. Provider- and host-specific behavior is verified during installation rather than inferred from fixture tests.
