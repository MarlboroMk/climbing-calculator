# ============================================================
# 对开爬坡能力计算工具 — 自动环境配置 & 启动
# 兼容 PowerShell 5.1+
# ============================================================

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venvDir = "$scriptDir\venv"
$pythonExe = "$venvDir\Scripts\python.exe"
$requirementsFile = "$scriptDir\requirements.txt"
$appFile = "$scriptDir\app.py"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Split-mu Climbing Performance Tool" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---- Step 1: find system Python ----
Write-Host "[1/3] Checking Python..." -ForegroundColor White
$systemPython = $null

foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0) {
            $systemPython = $cmd
            Write-Host "  Found: $($ver.Trim())" -ForegroundColor Green
            break
        }
    }
    catch {
        # try next
    }
}

if (-not $systemPython) {
    Write-Host "  Python not found!" -ForegroundColor Red
    Write-Host "  Please install Python 3.9+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# ---- Step 2: create venv if needed ----
Write-Host "[2/3] Preparing virtual environment..." -ForegroundColor White
$needInstall = $false

if (Test-Path $pythonExe) {
    Write-Host "  venv already exists" -ForegroundColor Green
}
else {
    Write-Host "  Creating venv (first-time setup)..." -ForegroundColor Yellow
    & $systemPython -m venv $venvDir 2>&1 | Out-Null
    if (-not (Test-Path $pythonExe)) {
        Write-Host "  Failed to create venv" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "  venv created" -ForegroundColor Green
    $needInstall = $true
}

# ---- Step 3: install dependencies ----
Write-Host "[3/3] Checking dependencies..." -ForegroundColor White

if ($needInstall) {
    Write-Host "  Installing packages (1-2 minutes)..." -ForegroundColor Yellow
    & $pythonExe -m pip install -r $requirementsFile --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Retrying..." -ForegroundColor Yellow
        & $pythonExe -m pip install -r $requirementsFile
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  Installation failed" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
    }
    Write-Host "  Done" -ForegroundColor Green
}
else {
    & $pythonExe -c "import streamlit, plotly, pandas" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Dependencies broken, reinstalling..." -ForegroundColor Yellow
        & $pythonExe -m pip install -r $requirementsFile --quiet 2>&1 | Out-Null
        Write-Host "  Fixed" -ForegroundColor Green
    }
    else {
        Write-Host "  All good" -ForegroundColor Green
    }
}

# ---- Launch ----
Write-Host ""
Write-Host "Starting server..." -ForegroundColor Green
Write-Host "Open http://localhost:8501 in your browser" -ForegroundColor White
Write-Host "Press Ctrl+C to stop" -ForegroundColor White
Write-Host ""

& $pythonExe -m streamlit run $appFile --server.port 8501

Read-Host "`nPress Enter to exit"
