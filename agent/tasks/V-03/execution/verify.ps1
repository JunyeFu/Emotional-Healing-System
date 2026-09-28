$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '../../../..')
Push-Location $root
try {
    py -3.14 'agent/tasks/V-03/execution/verify.py'
    if ($LASTEXITCODE -ne 0) { throw 'V-03 verification failed' }
} finally { Pop-Location }
