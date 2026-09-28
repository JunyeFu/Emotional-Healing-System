$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path (Split-Path (Split-Path $PSScriptRoot)))
Push-Location $repo
try {
    py -3.14 "$PSScriptRoot/verify.py"
    if ($LASTEXITCODE -ne 0) { throw 'A-03 normalization verification failed' }
} finally { Pop-Location }
