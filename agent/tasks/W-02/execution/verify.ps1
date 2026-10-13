$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Push-Location $root
try {
    py -3.14 (Join-Path $PSScriptRoot 'verify.py')
    if ($LASTEXITCODE -ne 0) { throw 'W-02 verification failed' }
} finally { Pop-Location }
