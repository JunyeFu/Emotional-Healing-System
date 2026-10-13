$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Push-Location $root
try { py -3.14 agent/tasks/E-05/execution/verify.py; if ($LASTEXITCODE -ne 0) { throw "E-05 verification failed" } }
finally { Pop-Location }
