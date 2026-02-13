@echo off
chcp 65001 >nul
echo ========================================
echo   太白说 - 打包脚本
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.7+
    pause
    exit /b 1
)

:: 检查 PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
)

:: 清理旧的构建文件
echo [1/3] 清理旧文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

:: 执行打包
echo [2/3] 开始打包...
pyinstaller taibai-talk.spec --noconfirm

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

:: 复制配置文件到输出目录
echo [3/3] 复制配置文件...
copy /y "hot-rule.txt" "dist\" >nul
copy /y "commands.txt" "dist\" >nul
copy /y "phrases.txt" "dist\" >nul

:: 创建使用说明
echo 太白说 使用说明> "dist\README.txt"
echo.>> "dist\README.txt"
echo 1. 双击 太白说.exe 启动程序>> "dist\README.txt"
echo 2. 手机扫描终端显示的二维码>> "dist\README.txt"
echo 3. 开始语音输入！>> "dist\README.txt"
echo.>> "dist\README.txt"
echo 配置文件说明:>> "dist\README.txt"
echo - hot-rule.txt: 正则替换规则>> "dist\README.txt"
echo - commands.txt: 快捷命令列表>> "dist\README.txt"
echo - phrases.txt: 常用语列表>> "dist\README.txt"
echo.>> "dist\README.txt"
echo 带密码启动: 太白说.exe --password 你的密码>> "dist\README.txt"
echo 指定端口: 太白说.exe -p 8888>> "dist\README.txt"
echo.>> "dist\README.txt"
echo 项目地址: https://github.com/jinny76/taibai-talk>> "dist\README.txt"

echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo 输出目录: dist\
echo 可执行文件: dist\太白说.exe
echo.
echo 按任意键打开输出目录...
pause >nul
explorer "dist"
