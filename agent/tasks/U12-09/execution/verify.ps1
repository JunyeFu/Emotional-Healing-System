$ErrorActionPreference = 'Stop'
py -3.14 (Join-Path $PSScriptRoot 'verify.py')
exit $LASTEXITCODE
