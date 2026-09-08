@echo off
title PlotChoice OCR & Verification Web Server
echo ==================================================
echo Starting PlotChoice OCR & Verification Web Server...
echo Web UI: http://localhost:8000
echo ==================================================
set PYTHONPATH=%~dp0
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
) else (
    py -m uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
)
pause
