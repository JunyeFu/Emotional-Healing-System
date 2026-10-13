$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Push-Location $root
try {
    py -3.14 agent/tasks/Q-02/execution/verify.py
    if ($LASTEXITCODE -ne 0) { throw 'Q-02 verification failed' }
} finally { Pop-Location }
