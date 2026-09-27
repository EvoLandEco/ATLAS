"""Copy only an approved report bundle from private state into a release staging folder."""
import os,re,shutil
from pathlib import Path
from atlas.workflow import approved_bundle
from atlas.util import read_json
root=Path('.runtime-state').resolve()
def inside(value):
    p=(root/value).resolve()
    if not p.is_relative_to(root):raise SystemExit('Publication path must be inside private state')
    return p
bundle=inside(os.environ['BUNDLE_PATH']);approval=inside(os.environ['APPROVAL_PATH'])
approved_bundle(bundle,approval)
meta=read_json(bundle/'report.json')['metadata']
if not re.fullmatch(r'report_[a-f0-9]{24}',meta['report_id']):raise SystemExit('Invalid report ID')
out=Path('approved-release');out.mkdir(exist_ok=False)
shutil.copy2(bundle/'dataset.zip',out/'dataset.zip');shutil.copy2(approval,out/'approval.json')
(out/'RELEASE.md').write_text('Reviewed ATLAS dataset for '+meta['report_date']+'.\n\nThe attached approval identifies the exact dataset bundle.\n')
with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('tag=briefing-'+meta['report_id']+'\n')
