$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '../../../..')
Push-Location $root
try {
    py -3.14 'agent/tasks/P-02/execution/verify.py'
    if ($LASTEXITCODE -ne 0) { throw 'P-02 verification failed' }
} finally {
    Pop-Location
}
