$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$projectPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $projectPython)) {
    python -m venv .venv
}

& $projectPython -c "import ifc_compliance_mvd" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $projectPython -m pip install -r requirements.lock
    & $projectPython -m pip install -e . --no-deps
}

& $projectPython -m ifc_compliance_mvd.cli serve
