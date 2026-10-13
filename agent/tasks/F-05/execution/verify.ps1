$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Push-Location $root
try {
    & (Join-Path $PSScriptRoot 'Invoke-F05.ps1') -Action all
    py -3.14 (Join-Path $PSScriptRoot 'f05_evidence.py') verify --evidence-dir 'agent/validation/evidence/F-05'
    if ($LASTEXITCODE -ne 0) { throw 'F05_HISTORICAL_EVIDENCE_FAILED' }
    py -3.14 (Join-Path $PSScriptRoot 'f05_evidence.py') verify --evidence-dir 'agent/validation/evidence/F-05' --git-tree HEAD --repo-root $root
    if ($LASTEXITCODE -ne 0) { throw 'F05_HISTORICAL_GIT_EVIDENCE_FAILED' }
} finally {
    Pop-Location
}
