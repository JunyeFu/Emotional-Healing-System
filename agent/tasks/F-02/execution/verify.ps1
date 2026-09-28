$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '../../../..')
Push-Location $root
try {
    py -3.14 'agent/tasks/F-02/execution/build_current_measurement.py' --check
    if ($LASTEXITCODE -ne 0) { throw 'F-02 current measurement alignment failed' }
    py -3.14 '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/99_验证与清单/validate_f02_package.py'
    if ($LASTEXITCODE -ne 0) { throw 'F-02 historical candidate check failed' }
    py -3.14 '02-技术研发/srp_step_measurement/build_evidence.py' --check
    if ($LASTEXITCODE -ne 0) { throw 'Step measurement evidence check failed' }
    py -3.14 -m pytest -q '02-技术研发/tests/step_measurement'
    if ($LASTEXITCODE -ne 0) { throw 'Step measurement regression failed' }
} finally {
    Pop-Location
}
