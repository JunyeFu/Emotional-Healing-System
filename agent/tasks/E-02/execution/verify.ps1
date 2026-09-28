$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../../..')).Path
Push-Location -LiteralPath $root
try {
    py -3.14 (Join-Path $PSScriptRoot 'verify.py')
    if ($LASTEXITCODE -ne 0) { throw 'E-02 verification failed' }
} finally {
    Pop-Location
}
