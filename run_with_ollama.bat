@echo off
title AUHIP Launcher (Ollama + Main)

echo ===================================================
echo Starting AUHIP Assistant with Ollama Server
echo ===================================================

echo.
echo [1/2] Starting Ollama server in the background...
start /b ollama serve

echo.
echo [2/2] Launching AUHIP main application...
call .venv\Scripts\activate.bat
python main.py

echo.
echo AUHIP application closed.
pause
