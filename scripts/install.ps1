$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -c "import sys; assert sys.version_info >= (3,11), 'Use Python 3.11 or later'"
if ($LASTEXITCODE -ne 0) { throw "Python version check failed" }
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
& .\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation .
if ($LASTEXITCODE -ne 0) { throw "Package installation failed" }
& .\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
& .\.venv\Scripts\python.exe -m atlas.cli doctor
Write-Host "Activate with: .\.venv\Scripts\Activate.ps1"
