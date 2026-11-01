@echo off
setlocal
if "%~1"=="" (
  call "%~dp0bigrun.cmd" capture --help
  exit /b 0
)
call "%~dp0bigrun.cmd" capture --td %*
exit /b %errorlevel%
