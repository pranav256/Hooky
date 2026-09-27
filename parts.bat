@echo off
setlocal
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [parts] Missing .venv. See README.md Setup.
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -m reelclip.parts %*
exit /b %errorlevel%
