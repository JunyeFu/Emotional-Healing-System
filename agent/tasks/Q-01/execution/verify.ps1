$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '../../../..')
Push-Location $root
try {
    py -3.14 (Join-Path $PSScriptRoot 'verify.py')
    if ($LASTEXITCODE -ne 0) { throw 'Q-01 verification failed' }
} finally { Pop-Location }
