# Civil Complaint Chatbot Project Run Script
# Usage: .\run-app.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Civil Complaint Chatbot" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed." -ForegroundColor Red
    exit 1
}

# Check uv installation
try {
    $uvVersion = uv --version 2>&1
    Write-Host "[OK] uv: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "[WARN] uv is not installed. Using python directly." -ForegroundColor Yellow
}

# Check app.py exists
$appPath = Join-Path $ProjectRoot "app.py"
if (-not (Test-Path $appPath)) {
    Write-Host "[ERROR] app.py not found." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] app.py found" -ForegroundColor Green

# Check .env file
$envPath = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "[WARN] .env file not found. API keys may not be configured." -ForegroundColor Yellow
} else {
    Write-Host "[OK] .env file found" -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting Flask server..." -ForegroundColor Yellow
Write-Host "URL: http://localhost:5000" -ForegroundColor Green
Write-Host "Exit: Ctrl+C" -ForegroundColor Gray
Write-Host ""

# Run Flask app
try {
    Push-Location $ProjectRoot

    # Try uv first, fallback to python
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv run python app.py
    } else {
        python app.py
    }
} finally {
    Pop-Location
    Write-Host ""
    Write-Host "Returned to project root." -ForegroundColor Gray
}
