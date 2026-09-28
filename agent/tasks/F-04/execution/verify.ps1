$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '../../../..')
Push-Location $root
try {
    py -3.14 (Join-Path $PSScriptRoot 'verify_host.py')
    if ($LASTEXITCODE -ne 0) { throw 'F04_HOST_VERIFICATION_FAILED' }
} finally {
    Pop-Location
}
