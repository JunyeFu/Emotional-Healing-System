@echo off
setlocal
set "PYTHON=%~dp0..\local\venvs\bigrun\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo BigRun environment missing. See agent/modules/acquisition/bigrun/README.md
  exit /b 1
)
"%PYTHON%" "%~dp0bigrun.py" %*
exit /b %errorlevel%
