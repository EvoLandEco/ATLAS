"""Snapshot installed dependency closures after an isolated environment passes validation."""
from pathlib import Path
from importlib import metadata
from packaging.requirements import Requirement
from packaging.markers import default_environment
import tomllib
ROOT=Path(__file__).resolve().parents[1]
project=tomllib.loads((ROOT/'pyproject.toml').read_text())
env={**default_environment(),'extra':''}
def closure(roots):
    todo=list(roots);result={}
    while todo:
        req=Requirement(todo.pop())
        if req.marker and not req.marker.evaluate(env):continue
        dist=metadata.distribution(req.name);name=dist.metadata['Name'];key=name.lower().replace('_','-')
        if key in result:continue
        result[key]=f'{name}=={dist.version}'
        todo.extend(dist.requires or [])
    return result
runtime=closure(project['project']['dependencies']+project['build-system']['requires'])
dev=closure(project['project']['optional-dependencies']['dev'])
header='# Exact installed dependency closure used for experimental validation.\n# Refresh inside an isolated, tested environment; inspect the diff before committing.\n'
(ROOT/'requirements.lock').write_text(header+'\n'.join(runtime[k] for k in sorted(runtime))+'\n')
(ROOT/'requirements-dev.lock').write_text(header+'-r requirements.lock\n'+'\n'.join(dev[k] for k in sorted(dev) if k not in runtime)+'\n')
print(f'{len(runtime)} runtime/build pins; {len(set(dev)-set(runtime))} additional test pins.')
