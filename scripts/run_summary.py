import json,os
from pathlib import Path
p=Path('.runtime-state/latest.json')
if p.exists():
    item=json.loads(p.read_text())
    print('# ATLAS Wednesday run\n')
    print('Report date:',item['report_date'],'  ')
    print('Report ID:',item['report_id'],'  ')
    print('Private state repository:',os.environ.get('ATLAS_STATE_REPO','configured private repository'),'  ')
    print('Bundle location:',str(Path(item['path']).parent/'dataset.zip'))
else:print('The run has no sealed report. Inspect the private state and workflow result.')
