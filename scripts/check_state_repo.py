"""Validate a configured GitHub state repository before writing operational data."""
import json,os,re,urllib.request
name=os.environ.get('EPIWEEKLY_STATE_REPO','');token=os.environ.get('EPIWEEKLY_STATE_TOKEN','')
if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',name) or not token:
    raise SystemExit('Configure EPIWEEKLY_STATE_REPO and EPIWEEKLY_STATE_TOKEN')
request=urllib.request.Request('https://api.github.com/repos/'+name,
    headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'EpiWeekly-deployment'})
with urllib.request.urlopen(request,timeout=30) as response:data=json.load(response)
if data.get('private') is not True:raise SystemExit('Operational state requires a private repository')
print('Private state repository verified.')
