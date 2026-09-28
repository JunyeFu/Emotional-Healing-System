$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '../../../..')
Push-Location $root
try {
    py -3.14 'agent/tasks/D-01/execution/verify.py'
    if ($LASTEXITCODE -ne 0) { throw 'D-01 normalization verification failed' }
} finally { Pop-Location }
