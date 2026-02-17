@echo off
chcp 65001 >nul
echo ==========================================
echo TaiBai Unlock Service Build
echo ==========================================

set CMAKE_PATH=J:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe

if not exist build mkdir build
cd build

echo.
echo [1/2] Running CMake configure...
"%CMAKE_PATH%" -G "Visual Studio 17 2022" -A x64 ..
if errorlevel 1 (
    echo [ERROR] CMake configure failed
    pause
    exit /b 1
)

echo.
echo [2/2] Building Release...
"%CMAKE_PATH%" --build . --config Release
if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Build successful!
echo Output: %cd%\bin\Release\TaiBaiService.exe
echo ==========================================
pause
