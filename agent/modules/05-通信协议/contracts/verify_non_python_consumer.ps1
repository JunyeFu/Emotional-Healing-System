$ErrorActionPreference = 'Stop'

$fixtures = Join-Path $PSScriptRoot 'fixtures\valid'
$baseline = Get-Content -Raw -Encoding UTF8 (Join-Path $fixtures 'telemetry-frame.json') | ConvertFrom-Json
$forward = Get-Content -Raw -Encoding UTF8 (Join-Path $fixtures 'telemetry-forward-compatible.json') | ConvertFrom-Json

if ($baseline.message_type -ne 'telemetry_frame' -or $baseline.frame_seq -ne 10) {
    throw 'Baseline telemetry fixture was not read as expected.'
}
if ($forward.message_type -ne 'telemetry_frame' -or $forward.frame_seq -ne 11) {
    throw 'Forward-compatible telemetry fixture was not read as expected.'
}
if (-not $forward.future_display_hint.ignored) {
    throw 'Forward-compatible extension field was not readable.'
}

Write-Output 'PASS_NON_PYTHON_CONSUMER: PowerShell ConvertFrom-Json; frame_seq=10,11'
