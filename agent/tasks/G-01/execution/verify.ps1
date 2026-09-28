$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '../../../..')
Push-Location $root
try {
    py -3.14 'agent/tasks/G-01/execution/verify.py'
    if ($LASTEXITCODE -ne 0) { throw 'G-01 current-use verification failed' }
} finally {
    Pop-Location
}
