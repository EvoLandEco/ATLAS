from pathlib import Path
import tomllib


def test_declared_dependencies_match_validated_lockfiles():
    root = Path(__file__).parents[1]
    project = tomllib.loads((root / 'pyproject.toml').read_text())
    locked = set((root / 'requirements.lock').read_text().splitlines())
    locked.update((root / 'requirements-dev.lock').read_text().splitlines())
    declared = project['build-system']['requires'] + project['project']['dependencies']
    declared += project['project']['optional-dependencies']['dev']
    assert set(declared) <= locked, sorted(set(declared) - locked)
