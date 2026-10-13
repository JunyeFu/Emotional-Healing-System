$ErrorActionPreference = 'Stop'
py -3.14 "$PSScriptRoot/verify.py"
exit $LASTEXITCODE
