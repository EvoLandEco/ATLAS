import importlib.util
from pathlib import Path

import pytest
from filelock import Timeout


def test_checkpoint_reuses_verified_outputs_and_retains_failed_build(tmp_path):
    spec = importlib.util.spec_from_file_location('checkpoint_build', Path('scripts/checkpoint_build.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / 'input.json'
    source.write_text('{"value": 1}')
    root = tmp_path / 'builds'
    with module.checkpoint(root, {'snapshot': source}, {'version': 1}) as (first, reused):
        assert not reused
        with pytest.raises(Timeout):
            with module.checkpoint(root, {'snapshot': source}, {'version': 1}):
                pytest.fail('Overlapping builders must not write')
        (first / 'result.json').write_text('checked output')
    with module.checkpoint(root, {'snapshot': source}, {'version': 1}) as (second, reused):
        assert reused and second == first
    assert len(list(root.glob('checkpoint-*'))) == 1
    with module.checkpoint(root, {'snapshot': source}, {'version': 2}) as (versioned, reused):
        assert not reused and versioned != first
        (versioned / 'result.json').write_text('different build parameters')
    (first / 'result.json').write_text('corrupted')
    with pytest.raises(ValueError, match='Output changed'):
        with module.checkpoint(root, {'snapshot': source}, {'version': 1}):
            pytest.fail('A changed output must not be reused')
    source.write_text('{"value": 2}')
    with pytest.raises(RuntimeError, match='validation failed'):
        with module.checkpoint(root, {'snapshot': source}, {'version': 1}) as (failed, reused):
            assert failed != first and not reused
            (failed / 'diagnostic.txt').write_text('retained')
            raise RuntimeError('validation failed')
    with pytest.raises(ValueError, match='Incomplete checkpoint'):
        with module.checkpoint(root, {'snapshot': source}, {'version': 1}):
            pytest.fail('A failed build must not dispatch twice')
    assert (failed / 'diagnostic.txt').read_text() == 'retained'
    source.write_text('{"value": 3}')
    with pytest.raises(ValueError, match='Inputs changed'):
        with module.checkpoint(root, {'snapshot': source}, {'version': 1}):
            source.write_text('{"value": 4}')
