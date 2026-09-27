from atlas.config import load_config
from atlas.sources import discover_archive, html_text
from pathlib import Path


def test_ukhsa_article_date_is_separate_from_reporting_week():
    source = next(s for s in load_config(Path('config/backfill.yaml'))['sources'] if s['id'] == 'ukhsa_monitoring')
    archive = b'''<section class="gem-c-attachment"><h3 class="gem-c-attachment__title"><a href="/government/publications/outbreaks-under-monitoring-in-2026/outbreaks-under-monitoring-week-12-week-ending-22-march-2026">Week 12</a></h3></section>'''
    class Archive:
        def get(self, url):
            return archive, {}, url, 200
    entries, notes = discover_archive(source, Archive(), '2026-03-26', {'max_index_pages': 1})
    assert len(entries) == 1 and entries[0]['published_at'] is None
    assert notes == ['archive_publication_date_missing']
    article = '''<h1>Week 12, ending 22 March 2026</h1><script type="application/ld+json">{"@type":"Article","datePublished":"2026-03-26T12:00:05+00:00","dateModified":"2026-09-24T15:30:06+01:00"}</script><main><div class="govspeak">Captured outbreak evidence.</div></main>'''
    text, title, published, precision = html_text(article, content_selector=source['content_selector'])
    assert published == '2026-03-26T12:00:05.000000Z' and precision == 'instant'
    assert text == 'Captured outbreak evidence.' and '22 March' in title
