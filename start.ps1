# 太白说 启动脚本
$ErrorActionPreference = "Stop"

# 切换到项目目录
Set-Location -Path $PSScriptRoot

# 激活虚拟环境
& ".\venv\Scripts\Activate.ps1"

# 启动应用
python main.py -p 57777 --url https://ime.kingfisher.live --password kingfisher123
