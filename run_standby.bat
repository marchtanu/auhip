@echo off
title AUHIP Assistant — Method 2 (Background Snap/Voice Standby)

echo ===================================================
echo Starting AUHIP Assistant (Method 2: Standby Listener Mode)
echo Waits in background for double-snap or "daddy home"
echo ===================================================

echo.
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
python main.py --standby

echo.
echo AUHIP application closed.
pause
