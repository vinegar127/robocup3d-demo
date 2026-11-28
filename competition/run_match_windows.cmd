@echo off
setlocal
cd /d "%~dp0"
"E:\RoboCup3D\.venv\Scripts\python.exe" -m tools.evaluate --scenario match --half 300 --players 7 --render --realtime %*
if errorlevel 1 pause
