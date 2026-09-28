#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${TSC:-tsc}" --noEmit --strict --skipLibCheck false --target ES2022 types/atlas.d.ts
