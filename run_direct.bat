@echo off
title AUHIP Assistant — Method 1 (Direct Interactive GUI)

echo ===================================================
echo Starting AUHIP Assistant (Method 1: Direct GUI Mode)
echo Ideal for noisy environments / keyboard control
echo ===================================================

echo.
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
python main.py --direct

echo.
echo AUHIP application closed.
pause
