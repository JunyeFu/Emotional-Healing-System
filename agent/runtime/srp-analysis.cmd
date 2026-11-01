@echo off
setlocal
set "PYTHON=%~dp0..\local\venvs\analysis\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo Analysis environment missing. See agent/modules/srp_analysis/README.md
  exit /b 1
)
"%PYTHON%" "%~dp0srp-analysis.py" %*
exit /b %errorlevel%
