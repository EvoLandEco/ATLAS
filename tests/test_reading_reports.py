import importlib.util
from pathlib import Path

from atlas.sources import save_document


def test_reading_archive_dates_and_escaping(store, tmp_path):
    spec = importlib.util.spec_from_file_location('reading_reports', Path('scripts/reading_reports.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for day in ['2024-09-24', '2024-09-25', '2026-09-25', '2026-09-26']:
        save_document(store, {'id':'who_don'}, text='<script>alert(1)</script>', raw=b'text',
                      url='https://www.who.int/'+day, content_url='https://www.who.int/'+day,
                      title='Source <title>', at='2026-09-25T12:00:00Z', published_at=day)
    result = module.render_reports(store.home, tmp_path/'reports', '2024-09-25', '2026-09-25')
    assert (result['publications'], result['excluded'], result['months']) == (2, 2, 2)
    html = (tmp_path/'reports/2024-09.html').read_text()
    assert '&lt;script&gt;' in html and '<script>' not in html
    assert '2024-09-24' not in html
