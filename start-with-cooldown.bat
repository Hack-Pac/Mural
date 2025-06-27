@echo off
echo Mural - Quick Start with Custom Cooldown
echo ========================================
echo.

if "%1"=="" (
    echo Usage: %0 [cooldown_seconds]
    echo.
    echo Examples:
    echo   %0 30    - Set 30 second cooldown
    echo   %0 300   - Set 5 minute cooldown
    echo   %0 60    - Set 1 minute cooldown
    echo.
    echo Starting with default cooldown...
    set PIXEL_COOLDOWN=60
) else (
    echo Setting pixel cooldown to %1 seconds
    set PIXEL_COOLDOWN=%1
)

echo.
echo Activating virtual environment...
call venv\Scripts\activate

echo Installing/updating dependencies...
pip install -r requirements.txt --quiet

echo.
echo Starting Mural with %PIXEL_COOLDOWN% second cooldown...
echo Press Ctrl+C to stop the server
echo.
python app.py
