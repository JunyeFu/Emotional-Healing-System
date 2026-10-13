$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Push-Location -LiteralPath $projectRoot
try {
    py -3.14 -m pytest 'agent/modules/communication/tests/contract/test_runtime_contract.py' 'agent/modules/communication/tests/test_csv_logger.py' -q
    if ($LASTEXITCODE -ne 0) { throw 'F01_TEST_FAILED' }
    pwsh -NoProfile -File 'agent/modules/communication/contracts/verify_non_python_consumer.ps1'
    if ($LASTEXITCODE -ne 0) { throw 'F01_CONSUMER_FAILED' }
} finally {
    Pop-Location
}
