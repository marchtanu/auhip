@echo off
title AUHIP - Gemini Multimodal Live Voice Assistant
color 0b
echo ================================================================
echo    AUHIP JARVIS - GEMINI MULTIMODAL LIVE AUDIO (BIDIRECTIONAL)
echo ================================================================
echo.
python -m auhip.tools.gemini_live %*
pause
