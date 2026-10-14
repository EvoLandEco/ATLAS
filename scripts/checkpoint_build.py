"""Reuse a validated checkpoint for the same files, code and build parameters."""
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import file_digest, sha256
from importlib.metadata import distributions
import json
from pathlib import Path
import sys

from filelock import FileLock


def file_reference(path):
    path = Path(path).resolve(strict=True)
    with path.open('rb') as stream:
        fingerprint = file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'sha256': fingerprint, 'bytes': path.stat().st_size}


def save(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


@contextmanager
def checkpoint(root, inputs, parameters):
    """The caller must finish validation before leaving the build context."""
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with FileLock(root / '.checkpoint-build.lock', timeout=0):
        identity = {'inputs': {name: file_reference(path) for name, path in sorted(inputs.items())},
                    'parameters': parameters, 'python': sys.version,
                    'packages': sorted([d.metadata['Name'], d.version] for d in distributions())}
        key = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        out = root / ('checkpoint-' + key)
        receipt = out / 'checkpoint-build.json'
        if out.exists():
            saved = json.loads(receipt.read_text()) if receipt.exists() else {}
            if saved.get('status') != 'validated' or saved.get('identity') != identity:
                raise ValueError(f'Incomplete checkpoint retained for inspection: {out}')
            for name, expected in saved['outputs'].items():
                if file_reference(out / name) != expected:
                    raise ValueError(f'Output changed: {out / name}')
            yield out, True
            return
        out.mkdir()
        record = {'checkpoint_version': '1.0.0', 'identity': identity, 'status': 'running',
                  'started_at': datetime.now(timezone.utc).isoformat()}
        save(receipt, record)
        try:
            yield out, False
            if identity['inputs'] != {name: file_reference(path) for name, path in sorted(inputs.items())}:
                raise ValueError('Inputs changed during the build; outputs were not cached')
            record.update(status='validated', completed_at=datetime.now(timezone.utc).isoformat(),
                          outputs={str(p.relative_to(out)): file_reference(p)
                                   for p in sorted(out.rglob('*')) if p.is_file() and p != receipt})
        except BaseException as error:
            record.update(status='failed', error=str(error))
            raise
        finally:
            save(receipt, record)
