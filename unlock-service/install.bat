@echo off
chcp 65001 >nul
echo ==========================================
echo TaiBai Unlock Service Install
echo ==========================================

:: Check admin
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Please run as Administrator
    pause
    exit /b 1
)

set SERVICE_EXE=%~dp0build\bin\Release\TaiBaiService.exe
set HELPER_EXE=%~dp0build\bin\Release\TaiBaiHelper.exe
set TARGET_PATH=C:\Windows\System32\TaiBaiService.exe
set HELPER_TARGET=C:\Windows\System32\TaiBaiHelper.exe

if not exist "%SERVICE_EXE%" (
    echo [ERROR] TaiBaiService.exe not found, please build first
    pause
    exit /b 1
)

if not exist "%HELPER_EXE%" (
    echo [ERROR] TaiBaiHelper.exe not found, please build first
    pause
    exit /b 1
)

echo.
echo [1/4] Stopping existing service...
"%TARGET_PATH%" /stop 2>nul
timeout /t 2 /nobreak >nul

echo [2/4] Uninstalling old service...
"%TARGET_PATH%" /uninstall 2>nul
timeout /t 1 /nobreak >nul

echo [3/4] Copying files to System32...
copy /Y "%SERVICE_EXE%" "%TARGET_PATH%"
if errorlevel 1 (
    echo [ERROR] Failed to copy service
    pause
    exit /b 1
)
copy /Y "%HELPER_EXE%" "%HELPER_TARGET%"
if errorlevel 1 (
    echo [ERROR] Failed to copy helper
    pause
    exit /b 1
)

echo [4/4] Installing and starting service...
"%TARGET_PATH%" /install
if errorlevel 1 (
    echo [ERROR] Failed to install service
    pause
    exit /b 1
)

"%TARGET_PATH%" /start
if errorlevel 1 (
    echo [WARNING] Failed to start service, try manual start
)

echo.
echo ==========================================
echo Service installed successfully!
echo ==========================================
pause
