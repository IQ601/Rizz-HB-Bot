@echo off
cd /d "%~dp0"

echo ========================================
echo   Rizz HB Bot - Starting up...
echo ========================================
echo.

:: Activate virtual environment
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Run this first: python -m venv venv
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

:: Check .env exists
if not exist ".env" (
    echo [ERROR] .env file not found.
    echo Create one with your TELEGRAM_BOT_TOKEN and GROQ_API_KEY.
    pause
    exit /b 1
)

echo [OK] Starting bot...
echo [OK] Logs will appear below. Press Ctrl+C to stop.
echo.

python -m src.bot

echo.
echo Bot stopped.
pause
