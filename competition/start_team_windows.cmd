@echo off
setlocal
cd /d "%~dp0"
"E:\RoboCup3D\.venv\Scripts\python.exe" -m team.launch %*
if errorlevel 1 pause
