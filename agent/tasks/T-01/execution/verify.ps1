$ErrorActionPreference = 'Stop'
py -3.14 (Join-Path $PSScriptRoot 'verify.py')
if ($LASTEXITCODE -ne 0) { throw 'T-01 verification failed' }
