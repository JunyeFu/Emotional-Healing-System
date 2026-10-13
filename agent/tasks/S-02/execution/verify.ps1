$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path (Split-Path (Split-Path $PSScriptRoot)))
Push-Location $repo
try {
    py -3.14 "$PSScriptRoot/verify.py"
    if ($LASTEXITCODE -ne 0) { throw 'S-02 software verification failed' }
} finally { Pop-Location }
