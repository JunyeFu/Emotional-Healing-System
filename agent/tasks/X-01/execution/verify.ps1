$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Push-Location $root
try {
    py -3.14 agent/tasks/X-01/execution/verify.py
    if ($LASTEXITCODE -ne 0) { throw 'X-01 verification failed' }
} finally { Pop-Location }
