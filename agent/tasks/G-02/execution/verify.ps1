$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '../../../..')
Push-Location $root
try {
    py -3.14 'agent/tasks/G-02/execution/verify.py'
    if ($LASTEXITCODE -ne 0) { throw 'G-02 verification failed' }
} finally {
    Pop-Location
}
