@echo off
setlocal
cd /d "%~dp0"
set "ROBOCUP_PYTHON=E:\RoboCup3D\.venv\Scripts\python.exe"
if not exist "%ROBOCUP_PYTHON%" (
  echo Missing environment: %ROBOCUP_PYTHON%
  pause
  exit /b 1
)
echo Starting RCSSServerMJ on localhost. Press Ctrl+C to stop.
echo Using the 2026 simulation rules for development.
"%ROBOCUP_PYTHON%" -m tools.run_server --host 127.0.0.1 --aport 60000 --mport 60001 --rules ssim26 %*
if errorlevel 1 pause
