$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '../../../..')
Push-Location $root
try {
    $result = Invoke-Pester -Script (Join-Path $PSScriptRoot 'tests/F03Environment.Tests.ps1') -PassThru
    if ($result.FailedCount -gt 0 -or $result.TotalCount -ne 6) { throw 'F03_HELPER_TEST_FAILED' }
    & (Join-Path $PSScriptRoot 'Invoke-F03.ps1') -Mode all
} finally {
    Pop-Location
}
