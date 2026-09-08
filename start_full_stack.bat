@echo off
title PlotChoice Full Stack Launcher
echo ==================================================
echo Launching Full PlotChoice Real Estate AI Stack:
echo  1. Local AI Service (llama-server :8080)
echo  2. Web Application (FastAPI :8000)
echo ==================================================

start "Qwen 2.5 7B AI Service" cmd /k "%~dp0start_llama_server.bat"
timeout /t 3 /nobreak >nul
start "PlotChoice Web App" cmd /k "%~dp0start_app.bat"

echo.
echo Both services launched in separate windows!
echo Open http://localhost:8000 in your browser.
pause
