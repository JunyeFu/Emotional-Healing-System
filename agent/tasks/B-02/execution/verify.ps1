$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Push-Location $root
try {
    & py -3.14 (Join-Path $PSScriptRoot 'verify.py')
    if ($LASTEXITCODE -ne 0) { throw 'B-02 normalization verification failed' }
} finally { Pop-Location }
