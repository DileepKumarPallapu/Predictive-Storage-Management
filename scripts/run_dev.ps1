# AEGISSTOR Windows Developer Quickstart Script
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "AEGISSTOR — Storage Resilience Intelligence Platform" -ForegroundColor Cyan
Write-Host "Predictive Storage Capacity and Performance Management" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan

$CurrentDir = Split-Path -Parent $PSScriptRoot

# 1. Start Backend in new process
Write-Host "[1/2] Starting AEGISSTOR FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
$BackendProcess = Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" -WorkingDirectory "$CurrentDir\backend" -PassThru

# 2. Start Frontend in new process
Write-Host "[2/2] Starting Obsidian Aurora React Frontend on http://localhost:5173..." -ForegroundColor Green
$FrontendProcess = Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "$CurrentDir\frontend" -PassThru

Write-Host "`nPlatform running successfully!" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "Backend API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "`nPress Ctrl+C or close the opened terminal windows to terminate." -ForegroundColor Gray
