"""Create a local reading archive from captured source documents."""
import argparse
from collections import defaultdict, Counter
from datetime import date
from html import escape
from pathlib import Path

from atlas.store import Store


def render_reports(state, out, start, end):
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if start > end:
        raise ValueError('Start date must precede end date')
    store = Store(state)
    try:
        latest = {(r['payload']['source_id'], r['payload']['url']): r
                  for r in store.records('document')}
        groups = defaultdict(list)
        excluded = 0
        for row in latest.values():
            published = row['payload']['published_at']
            if not published or not start <= date.fromisoformat(published[:10]) <= end:
                excluded += 1
                continue
            groups[published[:7]].append(row)
        out.mkdir(parents=True, exist_ok=True)
        css = 'body{font:17px/1.6 system-ui;max-width:960px;margin:40px auto;padding:0 20px;color:#183441}a{color:#006880}article{border-top:1px solid #ccd8dd;padding:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}summary{cursor:pointer}table{border-collapse:collapse}td,th{padding:8px;text-align:left;border-bottom:1px solid #ccd8dd;vertical-align:top;overflow-wrap:anywhere}'
        def page(title, body):
            return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(title)+'</title><style>'+css+'</style><main><h1>'+escape(title)+'</h1>'+body+'</main></html>'
        note = '<p>Captured source reading archive. Extraction and event review are recorded separately in the workflow briefing. Publication dates determine the month; capture dates record when ATLAS retrieved the text. Entries are publications, not counts of distinct outbreaks.</p>'
        links = []
        for month, rows in sorted(groups.items(), reverse=True):
            articles = []
            for row in sorted(rows, key=lambda r: r['payload']['published_at'], reverse=True):
                p = row['payload']
                text = (store.home / p['text_object']).read_text()
                articles.append('<article><h2>'+escape(p['title'])+'</h2><p>'+escape(p['source_id'])+' · Published '+escape(p['published_at'][:10])+' · Captured '+escape(row['recorded_at'][:10])+'</p><p><a href="'+escape(p['url'], quote=True)+'">Original source</a> · Parse status: '+escape(p['parse_status'])+'</p><details><summary>Read captured source text</summary><pre>'+escape(text)+'</pre></details></article>')
            (out / (month+'.html')).write_text(page('ATLAS · '+month, '<p><a href="index.html">All months</a></p>'+note+''.join(articles)))
            links.append('<li><a href="'+month+'.html">'+month+'</a> · '+str(len(rows))+' publications</li>')
        checks = {}
        for row in store.records('source_check'):
            checks[row['payload']['source_id']] = row['payload']
        counts=Counter(r['payload']['source_id'] for rows in groups.values() for r in rows)
        coverage = '<table><tr><th>Source</th><th>Latest collection</th><th>Publications in archive</th><th>Limits and errors</th></tr>'
        for p in checks.values():
            notes='<details><summary>'+str(len(p['notes']))+' coverage notes</summary><ul>'+''.join('<li>'+escape(n)+'</li>' for n in p['notes'])+'</ul></details>' if p['notes'] else 'No collection errors reported'
            if p.get('scope_excluded'):
                notes+='<p>'+str(p['scope_excluded'])+' documents excluded by publisher topic labels.</p>'
            coverage += '<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in [p['source_id'],p['status'],counts[p['source_id']]])+'<td>'+notes+'</td></tr>'
        coverage += '</table>'
        total = sum(map(len, groups.values()))
        body = '<p>'+str(start)+' through '+str(end)+'</p>'+note+'<p>'+str(total)+' dated publications; '+str(excluded)+' documents outside the publication window or without a publication date are excluded from the monthly archive. Months without captured publications are omitted; their absence does not establish that no outbreaks occurred.</p><h2>Monthly reading reports</h2><ul>'+''.join(links)+'</ul><h2>Collection coverage</h2>'+coverage
        if (out/'coverage-review.html').exists():
            body='<p><a href="coverage-review.html">Coverage review and investigation instructions</a></p>'+body
        if (out/'workflow-review.html').exists():
            body='<p><a href="workflow-review.html">Model extraction, reviewed events, and draft briefing</a></p>'+body
        (out/'index.html').write_text(page('ATLAS · Source reading archive',body))
        return {'publications':total,'months':len(groups),'excluded':excluded,'index':str(out/'index.html')}
    finally:
        store.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', type=Path, default=Path('.runtime-state'))
    p.add_argument('--out', type=Path, default=Path('reports'))
    p.add_argument('--since', required=True)
    p.add_argument('--until', required=True)
    a = p.parse_args()
    print(render_reports(a.state, a.out, a.since, a.until))
