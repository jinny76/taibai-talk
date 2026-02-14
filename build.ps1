# TaiBai Talk - PowerShell Build Script

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TaiBai Talk Builder" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location -Path $PSScriptRoot

Write-Host "[1/4] Checking dependencies..." -ForegroundColor Yellow
python -m pip install pyinstaller -q
Write-Host "[OK] PyInstaller ready" -ForegroundColor Green

Write-Host ""
Write-Host "[2/4] Cleaning..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
Write-Host "[OK] Clean done" -ForegroundColor Green

Write-Host ""
Write-Host "[3/4] Building..." -ForegroundColor Yellow
python -m PyInstaller taibai-talk.spec --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] Build failed\!" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Build done" -ForegroundColor Green

Write-Host ""
Write-Host "[4/4] Copying config files..." -ForegroundColor Yellow
Copy-Item "hot-rule.txt" "dist\" -Force
Copy-Item "commands.txt" "dist\" -Force
Copy-Item "phrases.txt" "dist\" -Force
Write-Host "[OK] Config files copied" -ForegroundColor Green

$exeSize = (Get-Item "dist\太白说.exe").Length / 1MB
$exeSizeStr = "{0:N2} MB" -f $exeSize

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Build Complete\! ($exeSizeStr)" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

explorer dist
