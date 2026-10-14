#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert sys.version_info >= (3,11), "Use Python 3.11 or later"'
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation .
npm ci --ignore-scripts
.venv/bin/python -m pytest -q
node --test tests/test_json_file.mjs
.venv/bin/python -m atlas.cli doctor
printf '\nActivate with: source .venv/bin/activate\n'
