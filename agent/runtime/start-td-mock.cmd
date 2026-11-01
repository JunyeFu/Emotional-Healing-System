@echo off
title SRP TD Mock
cd /d "%~dp0..\.."
py -3.14 agent/tasks/T-01/execution/run_manual_mock.py
if errorlevel 1 pause
