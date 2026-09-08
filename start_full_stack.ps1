# PowerShell Launcher for PlotChoice Full Stack
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Launching Full PlotChoice Real Estate AI Stack:" -ForegroundColor Green
Write-Host " 1. Local AI Service (llama-server :8080)" -ForegroundColor Yellow
Write-Host " 2. Web Application (FastAPI :8000)" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start Qwen 2.5 7B AI Service
Start-Process cmd.exe -ArgumentList "/k `"$scriptDir\start_llama_server.bat`""

Start-Sleep -Seconds 3

# Start FastAPI Web Server
Start-Process cmd.exe -ArgumentList "/k `"$scriptDir\start_app.bat`""

Write-Host "`nBoth services launched in separate windows!" -ForegroundColor Green
Write-Host "Open http://localhost:8000 in your browser.`n" -ForegroundColor Cyan
