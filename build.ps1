# 太白说 - PowerShell 打包脚本
# 使用方法: .\build.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  太白说 - 打包脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 切换到脚本所在目录
Set-Location -Path $PSScriptRoot

# 检查 Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[√] Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[×] 未找到 Python，请先安装 Python 3.7+" -ForegroundColor Red
    exit 1
}

# 检查/安装 PyInstaller
$pyinstallerInstalled = pip show pyinstaller 2>$null
if (-not $pyinstallerInstalled) {
    Write-Host "[!] 正在安装 PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[×] PyInstaller 安装失败" -ForegroundColor Red
        exit 1
    }
}
Write-Host "[√] PyInstaller 已就绪" -ForegroundColor Green

# 清理旧文件
Write-Host ""
Write-Host "[1/4] 清理旧文件..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
Write-Host "[√] 清理完成" -ForegroundColor Green

# 执行打包
Write-Host ""
Write-Host "[2/4] 开始打包..." -ForegroundColor Yellow
pyinstaller taibai-talk.spec --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[×] 打包失败！" -ForegroundColor Red
    exit 1
}
Write-Host "[√] 打包完成" -ForegroundColor Green

# 复制配置文件
Write-Host ""
Write-Host "[3/4] 复制配置文件..." -ForegroundColor Yellow
Copy-Item "hot-rule.txt" "dist\" -Force
Copy-Item "commands.txt" "dist\" -Force
Copy-Item "phrases.txt" "dist\" -Force
Write-Host "[√] 配置文件已复制" -ForegroundColor Green

# 创建使用说明
Write-Host ""
Write-Host "[4/4] 生成说明文件..." -ForegroundColor Yellow
@"
太白说 使用说明
================

1. 双击 太白说.exe 启动程序
2. 手机扫描终端显示的二维码
3. 开始语音输入！

配置文件说明:
- hot-rule.txt: 正则替换规则
- commands.txt: 快捷命令列表
- phrases.txt: 常用语列表

命令行参数:
- 带密码启动: 太白说.exe --password 你的密码
- 指定端口: 太白说.exe -p 8888
- 自定义URL: 太白说.exe --url https://your-domain.com

项目地址: https://github.com/jinny76/taibai-talk
"@ | Out-File -FilePath "dist\README.txt" -Encoding UTF8
Write-Host "[√] 说明文件已生成" -ForegroundColor Green

# 统计文件大小
$exeSize = (Get-Item "dist\太白说.exe").Length / 1MB
$exeSizeStr = "{0:N2} MB" -f $exeSize

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  打包完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "输出目录: dist\"
Write-Host "可执行文件: dist\太白说.exe ($exeSizeStr)"
Write-Host ""

# 询问是否打开目录
$openDir = Read-Host "是否打开输出目录? (Y/n)"
if ($openDir -ne "n" -and $openDir -ne "N") {
    explorer "dist"
}
