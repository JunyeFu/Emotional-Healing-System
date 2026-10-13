$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '../../../..')
Push-Location $root
try {
    py -3.14 'agent/tasks/R-01/execution/verify.py'
    if ($LASTEXITCODE -ne 0) { throw 'R-01 verification failed' }
} finally { Pop-Location }
