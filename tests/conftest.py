from pathlib import Path
import pytest
from epiweekly.store import Store
from epiweekly.demo import demo_config,demo
from epiweekly.util import read_json

@pytest.fixture
def store(tmp_path):
    s=Store(tmp_path/'state')
    yield s
    s.close()

@pytest.fixture
def config():return demo_config()

@pytest.fixture(scope='session')
def demo_run(tmp_path_factory):
    root=tmp_path_factory.mktemp('demo')
    result=demo(root)
    return root,result,[read_json(Path(p)/'report.json') for p in result['reports']]
