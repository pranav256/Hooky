@echo off
REM reelclip - lean Instagram Reel workflow
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [reelclip] Missing .venv. Create it with:
    echo            py -3 -m venv .venv
    echo            .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

if "%~1"=="" (
    echo Usage:
    echo   run.bat video.mp4 --no-post
    echo   run.bat --links --no-post
    echo   run.bat --post-now
    echo   run.bat --queue-status
    exit /b 0
)

.venv\Scripts\python -m reelclip %*
exit /b %errorlevel%
