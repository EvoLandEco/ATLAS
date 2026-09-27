"""Render the geographic preview from the exact validated export snapshot."""
import argparse
from datetime import date
from html import escape
import json
import os
from pathlib import Path

from atlas.config import assets
from atlas.geography import validate_coverage
from atlas.handoff import inspect_export
from atlas.util import read_json, write_json


def render(snapshot, bundle, source_dir, land_path, out, coverage):
    reference=inspect_export(bundle,snapshot)
    data=read_json(snapshot);validate_coverage(data)
    site=read_json(bundle/'atlas-site.json')
    memberships={m['id']:m for m in site['location_memberships']};record_topics={r['id']:r['topic_id'] for r in site['records']}
    expected={}
    for p in site['places']:
        if not p['topic_ids']:continue
        rules=sorted({tuple(sorted({memberships[mid]['record_id']}|set(memberships[mid]['eligibility']['record_ids']))) for mid in p['location_membership_ids'] if record_topics[memberships[mid]['record_id']] in p['topic_ids']})
        expected[p['id']]=dict(id=p['id'],label=p['label'],lat=p['latitude'],lon=p['longitude'],precision=p['precision'],topic_ids=p['topic_ids'],eligibility=[dict(record_ids=list(ids),rule='all_supporting_records_in_window',partial='hide_relationship_keep_visible_assertions') for ids in rules])
    if {p['id']:p for p in data['map_places']} != expected or len(data['map_places'])!=len(expected):
        raise ValueError('Map places differ from structured export')
    if out.exists() and any(out.iterdir()):raise ValueError('Map output directory must be empty')
    dates=[r[k][:10] for r in data['records'] for k in ['publication','capture']]
    window=[min(dates),max(dates)];days=(date.fromisoformat(window[1])-date.fromisoformat(window[0])).days
    data['display_window']=window
    paths=[]
    for feature in read_json(land_path)['features']:
        geom=feature['geometry'];polys=[geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']
        for poly in polys:
            paths.append(' '.join('M'+' L'.join(f'{(lon+180)*3:.2f},{(90-lat)*3:.2f}' for lon,lat,*_ in ring)+' Z' for ring in poly))
    source_url=os.path.relpath(source_dir.resolve(),out.resolve())
    for r in data['records']:
        if not (source_dir/(r['document_id']+'.txt')).is_file():raise ValueError('Missing captured text')
    page=assets('map_demo.html')
    replacements={'__DATA__':json.dumps(data).replace('<','\\u003c'), '__LINKS__':Path('scripts/map_links.js').read_text(),
        '__LAND__':''.join('<path d="'+p+'"/>' for p in paths),'__DAYS__':str(days),'__SINCE__':window[0],'__UNTIL__':window[1],
        '__WINDOW_LABEL__':' – '.join(window),'__SOURCE_URL__':escape(source_url,quote=True),
        '__COVERAGE_URL__':escape(os.path.relpath(coverage.resolve(),out.resolve()),quote=True)}
    for key,value in replacements.items():page=page.replace(key,value)
    out.mkdir(parents=True,exist_ok=True)
    (out/'index.html').write_text(page);write_json(out/'data.json',data)
    from markdown_it import MarkdownIt
    review=MarkdownIt('default',{'html':False}).render(Path('docs/LINK_REVIEW.md').read_text())
    for name in ['RELATIONSHIP_RULES.md','EVALUATION.md']:
        review=review.replace('href="'+name+'"','href="'+escape(os.path.relpath(Path('docs',name).resolve(),out.resolve()),quote=True)+'"')
    (out/'link-review.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>ATLAS map methods</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:35px auto;padding:20px}td,th{padding:10px;text-align:left}table{border-collapse:collapse}</style><a href="index.html">Return to map</a>'+review+'</html>')
    write_json(out/'build.json',dict(export_id=reference['export_id'],map_snapshot_sha256=reference['map_snapshot_sha256'],display_window=window,
        records=len(data['records']),topics=len(data['tracks']),places=len(data['map_places']),links=len(data['map_links']),coverage_records=len(data['geographic_review']['records'])))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['snapshot','bundle','source-dir','land','out','coverage']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();render(a.snapshot,a.bundle,a.source_dir,a.land,a.out,a.coverage)
