@echo off
setlocal
cd /d "%~dp0"
"E:\RoboCup3D\.venv\Scripts\python.exe" -m tools.evaluate --scenario match --players 7 --half 300 --opponent my3d --seed 61 --require-legal-opening --render --realtime %*
if errorlevel 1 pause
