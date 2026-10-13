$ErrorActionPreference = 'Stop'
Push-Location (Resolve-Path (Join-Path $PSScriptRoot '../../../..'))
try {
    py -3.14 agent/tasks/U12-06/execution/verify.py
    if ($LASTEXITCODE -ne 0) { throw 'U12-06 verification failed' }
} finally {
    Pop-Location
}
