# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

太白说（TaiBai Talk）是一个局域网输入同步工具，实现手机输入/语音转文字在电脑端实时上屏。主要用于解决豆包输入法暂无 PC 版的痛点。

## 常用命令

```bash
# 安装依赖
pip install -r requirement.txt

# 基本启动
python main.py

# 带参数启动
python main.py -p 5000 --host 0.0.0.0 --url https://your-domain.com --password yourpassword

# PowerShell 启动脚本（包含虚拟环境激活）
.\start.ps1
```

### 启动参数
- `-p, --port`: 端口号（默认 5000）
- `--host`: 监听地址（默认 0.0.0.0）
- `--url`: 外部访问 URL（用于反向代理场景）
- `--password`: 访问密码
- `--no-qrcode`: 不显示终端二维码

## 架构概览

这是一个单文件 Flask 应用（`main.py`），包含：

### 后端（Python/Flask）
- **Web 服务器**：Flask 提供 HTTP API 和 HTML 页面
- **键鼠控制**：pyautogui 模拟键盘输入、鼠标移动和点击
- **剪贴板**：pyperclip 处理中文粘贴
- **二维码**：qrcode_terminal 在终端显示二维码

### 前端（templates 目录）
- 响应式移动端界面，模板文件位于 `templates/` 目录
- `index.html`：主界面
- `login.html`：密码登录页面
- 触控板模式：全屏触控区域，支持鼠标移动和点击手势
- 截屏查看：支持双指缩放（0.5x ~ 5x）和拖动
- 快捷操作栏：Tab 切换、继续、ESC、回滚、新任务、编译、提交
- 设定弹窗：Logo 点击可编辑自动发送、命令列表、常用语列表
- 自定义下拉框：命令、常用语、历史记录菜单
- 长按重复：方向键和热键支持长按连续触发

### API 端点
| 路由 | 方法 | 功能 |
|------|------|------|
| `/send` | POST | 发送文本到电脑光标处 |
| `/send_enter` | POST | 发送回车键 |
| `/send_hotkey` | POST | 发送热键组合 |
| `/move_cursor` | POST | 方向键控制 |
| `/delete_pc` | POST | 退格删除 |
| `/mouse_move` | POST | 鼠标相对移动 |
| `/mouse_click` | POST | 鼠标点击 |
| `/screenshot` | GET | 截取屏幕返回 JPEG 图片 |
| `/undo` | POST | 撤销上次操作 |
| `/auth` | POST | 密码验证 |
| `/get_options` | GET | 获取命令和常用语配置 |
| `/save_options` | POST | 保存命令和常用语配置 |
| `/favicon.ico` | GET | 网站图标 |
| `/health` | GET | 健康检测端点 |

## 配置文件

| 文件 | 说明 |
|------|------|
| `hot-rule.txt` | 正则替换规则，格式：`pattern = replacement` |
| `commands.txt` | 快捷命令列表，`[KEY]` 前缀表示热键 |
| `phrases.txt` | 常用语列表 |

## 关键实现

- **正则替换**：`REPLACE_RULES` 列表存储编译后的正则表达式，`apply_replace_rules()` 应用替换
- **操作历史**：`LAST_OPERATION` 记录最后一次操作类型（text/enter/delete/hotkey），用于撤销
- **粘贴中文**：`paste_text()` 先保存剪贴板、复制文本、Ctrl+V 粘贴、再恢复剪贴板
- **Session 认证**：使用 Flask session 存储登录状态，前端 localStorage 缓存密码
