from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for
import pyautogui
import pyperclip
import socket
import re
import os
import sys
import argparse
import secrets
# 新增：导入二维码生成库
import qrcode
from qrcode.console_scripts import main as qr_main

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # 用于 session 加密

# 密码配置（启动时通过参数设置）
AUTH_PASSWORD = None

# 存储正则替换规则（key: 编译后的正则表达式，value: 替换式）
REPLACE_RULES = []

# ===== 重构历史记录：存储上一次操作的类型和内容 =====
# 格式: {"type": "text"/"enter"/"delete", "content": 文本内容/空字符串}
LAST_OPERATION = {"type": None, "content": ""}

def load_replace_rules():
    """加载 EXE 所在目录下的 hot-rule.txt 替换规则"""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))
    
    rule_file = os.path.join(exe_dir, "hot-rule.txt")
    if not os.path.exists(rule_file):
        print(f"警告：未找到规则文件 {rule_file}，跳过规则加载")
        return
    
    with open(rule_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = re.split(r'\s+=\s+', line, maxsplit=1)
        if len(parts) != 2:
            print(f"警告：第 {line_num} 行格式错误，跳过该规则")
            continue
        pattern_str, replace_str = parts[0].strip(), parts[1].strip()
        try:
            pattern = re.compile(pattern_str)
            REPLACE_RULES.append( (pattern, replace_str) )
            print(f"加载规则成功：{pattern_str} → {replace_str}")
        except re.error as e:
            print(f"警告：第 {line_num} 行正则错误 {e}，跳过该规则")

load_replace_rules()

# 存储命令和常用语配置
COMMANDS = []
PHRASES = []

def load_quick_options():
    """加载命令和常用语配置文件"""
    global COMMANDS, PHRASES
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))

    # 加载命令
    cmd_file = os.path.join(exe_dir, "commands.txt")
    if os.path.exists(cmd_file):
        with open(cmd_file, 'r', encoding='utf-8') as f:
            COMMANDS = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"加载命令配置：{len(COMMANDS)} 条")

    # 加载常用语
    phrase_file = os.path.join(exe_dir, "phrases.txt")
    if os.path.exists(phrase_file):
        with open(phrase_file, 'r', encoding='utf-8') as f:
            PHRASES = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"加载常用语配置：{len(PHRASES)} 条")

load_quick_options()

def apply_replace_rules(text):
    """应用所有替换规则到文本"""
    for pattern, replace_str in REPLACE_RULES:
        text = pattern.sub(replace_str, text)
    return text

def paste_text(text):
    """剪贴板粘贴方案，兼容中文"""
    original_clipboard = pyperclip.paste()
    try:
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
    finally:
        pyperclip.copy(original_clipboard)

# ===== 重构撤销函数：根据操作类型执行不同撤销逻辑 =====
def undo_last_operation():
    """
    根据 LAST_OPERATION 的类型执行撤销
    - text: 删除对应长度的字符
    - enter: 模拟删除换行（按一次 backspace，多数编辑器换行占1个删除单位）
    - delete: 无撤销（因为是主动删除PC端内容，无历史文本可恢复）
    """
    op_type = LAST_OPERATION["type"]
    content = LAST_OPERATION["content"]
    
    if op_type == "text":
        # 文本操作：删除替换后的文本长度
        replaced_len = len(apply_replace_rules(content))
        if replaced_len > 0:
            pyautogui.press('backspace', presses=replaced_len)
    elif op_type == "enter":
        # 回车操作：按一次 backspace 撤销换行
        pyautogui.press('backspace')
    elif op_type == "delete":
        # 删除操作：无撤销逻辑，直接清空历史
        pass

# ===== 新增：方向键控制接口 =====
@app.route('/move_cursor', methods=['POST'])
def move_cursor():
    direction = request.json.get('direction')
    # 使用 pyautogui 模拟方向键按下
    if direction in ['left', 'up', 'down', 'right']:
        pyautogui.press(direction)
        print(f"执行光标移动：{direction}")
    return jsonify({"status": "success"})

# ===== 新增：PC端删除接口 =====
@app.route('/delete_pc', methods=['POST'])
def delete_pc():
    global LAST_OPERATION
    # 执行 PC 端删除（backspace）
    pyautogui.press('backspace')
    # 记录删除操作，且标记为不可撤销（避免和撤销逻辑冲突）
    LAST_OPERATION = {"type": "delete", "content": ""}
    print("执行PC端删除操作")
    return jsonify({"status": "success"})

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>太白说</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600&display=swap');

        :root {
            --bg-primary: #0a0a0a;
            --bg-secondary: #111111;
            --bg-card: #161616;
            --bg-input: #1a1a1a;
            --border-color: #2a2a2a;
            --border-hover: #3a3a3a;
            --gold-primary: #c9a962;
            --gold-light: #d4b87a;
            --gold-dark: #a68b4b;
            --text-primary: #e8e8e8;
            --text-secondary: #888888;
            --text-muted: #555555;
            --success: #4a9f6e;
            --danger: #9f4a4a;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            background: var(--bg-primary);
            font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
            padding: 20px 15px 40px;
            --btn-gap: 10px;
            --btn-radius: 8px;
            --input-height: 160px;
            --btn-font: 1rem;
            --btn-padding: 14px 12px;
        }
        body.large-mode {
            --btn-gap: 12px;
            --btn-radius: 10px;
            --input-height: 200px;
            --btn-font: 1.2rem;
            --btn-padding: 18px 14px;
        }
        .header {
            width: 100%;
            max-width: 500px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            color: var(--text-primary);
        }
        .logo-icon {
            width: 38px;
            height: 38px;
            background: var(--bg-card);
            border: 1px solid var(--gold-primary);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .logo-icon svg { width: 20px; height: 20px; fill: var(--gold-primary); }
        .logo-text {
            font-size: 18px;
            font-weight: 600;
            letter-spacing: 2px;
            color: var(--text-primary);
        }
        #mode-btn {
            padding: 8px 16px;
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        #mode-btn:hover, #fullscreen-btn:hover {
            border-color: var(--gold-primary);
            color: var(--gold-primary);
        }
        #fullscreen-btn {
            padding: 8px 16px;
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-left: 8px;
        }
        .auto-send-bar {
            width: 100%;
            max-width: 500px;
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
            padding: 12px 16px;
            background: var(--bg-card);
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }
        .auto-send-bar label {
            color: var(--text-secondary);
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            white-space: nowrap;
        }
        .toggle-switch {
            position: relative;
            width: 40px;
            height: 22px;
        }
        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        .toggle-slider {
            position: absolute;
            cursor: pointer;
            inset: 0;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 22px;
            transition: 0.2s;
        }
        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 2px;
            bottom: 2px;
            background: var(--text-secondary);
            border-radius: 50%;
            transition: 0.2s;
        }
        .toggle-switch input:checked + .toggle-slider {
            background: var(--gold-dark);
            border-color: var(--gold-primary);
        }
        .toggle-switch input:checked + .toggle-slider:before {
            transform: translateX(18px);
            background: var(--gold-light);
        }
        .delay-select {
            padding: 6px 10px;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-secondary);
            font-size: 12px;
            cursor: pointer;
            flex-shrink: 0;
        }
        .delay-select:focus { outline: none; border-color: var(--gold-primary); }
        .delay-select option { background: var(--bg-card); color: var(--text-primary); }
        .countdown-indicator {
            padding: 4px 10px;
            background: var(--gold-dark);
            border-radius: 4px;
            font-size: 11px;
            color: var(--bg-primary);
            font-weight: 600;
            opacity: 0;
            transition: opacity 0.2s;
            flex-shrink: 0;
        }
        .countdown-indicator.active { opacity: 1; }
        .bar-spacer { flex: 1; }
        .btn-enter-small {
            padding: 7px 14px;
            background: var(--success);
            border: none;
            border-radius: 6px;
            color: #fff;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            flex-shrink: 0;
            white-space: nowrap;
        }
        .btn-enter-small:hover { background: #5ab07e; }
        .btn-enter-small:active { transform: scale(0.95); }
        .btn-enter-inline {
            padding: 12px 20px;
            background: var(--gold-primary);
            border: none;
            border-radius: 8px;
            color: var(--bg-primary);
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            flex-shrink: 0;
            white-space: nowrap;
        }
        .btn-enter-inline:hover { background: var(--gold-light); }
        .btn-enter-inline:active { transform: scale(0.96); }
        .quick-selects {
            display: flex;
            gap: 10px;
            margin-top: 14px;
            width: 100%;
            position: relative;
        }
        .quick-select {
            flex: 1;
            min-width: 0;
            padding: 12px 14px;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-secondary);
            font-size: 13px;
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' fill='%23888' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10l-5 5z'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 12px center;
            padding-right: 32px;
            box-sizing: border-box;
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
            transition: all 0.2s;
        }
        .quick-select:hover { border-color: var(--border-hover); }
        .quick-select:focus { outline: none; border-color: var(--gold-primary); }
        .quick-select option {
            background: var(--bg-card);
            color: var(--text-primary);
            padding: 10px;
        }

        /* 自定义下拉框 */
        .custom-dropdown {
            position: relative;
            flex: 1;
            min-width: 0;
        }
        .dropdown-toggle {
            width: 100%;
            padding: 12px 14px;
            padding-right: 32px;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-secondary);
            font-size: 13px;
            cursor: pointer;
            text-align: left;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' fill='%23888' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10l-5 5z'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 12px center;
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
            transition: all 0.2s;
        }
        .dropdown-toggle:hover { border-color: var(--border-hover); }
        .dropdown-toggle.active { border-color: var(--gold-primary); }
        .dropdown-menu {
            display: none;
            position: fixed;
            max-height: 45vh;
            width: 80vw;
            max-width: 400px;
            overflow-y: auto;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            z-index: 2000;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }
        .dropdown-menu.show { display: block; }
        .dropdown-item {
            padding: 12px 14px;
            color: var(--text-primary);
            cursor: pointer;
            border-bottom: 1px solid var(--border-color);
            font-size: 13px;
            transition: background 0.15s;
            user-select: none;
            -webkit-user-select: none;
        }
        .dropdown-item:last-child { border-bottom: none; }
        .dropdown-item:hover, .dropdown-item:active {
            background: var(--bg-input);
        }
        .dropdown-item.hotkey {
            color: var(--gold-primary);
        }
        .dropdown-item.pressing {
            background: var(--gold-dark);
        }

        .container {
            width: 100%;
            max-width: 500px;
            background: var(--bg-card);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border-color);
        }
        #input-box {
            width: 100%;
            height: var(--input-height);
            padding: 16px;
            padding-right: 48px; /* 避开右上角图标 */
            border: 1px solid var(--border-color);
            border-radius: 8px;
            resize: none;
            font-size: 15px;
            background: var(--bg-input);
            color: var(--text-primary);
            transition: all 0.2s;
            font-family: inherit;
        }
        #input-box:focus {
            outline: none;
            border-color: var(--gold-primary);
            box-shadow: 0 0 0 3px rgba(201, 169, 98, 0.1);
        }
        #input-box::placeholder { color: var(--text-muted); }

        /* 输入区域容器 */
        .input-area {
            position: relative;
            width: 100%;
        }
        .mode-toggle {
            position: absolute;
            top: 8px;
            right: 8px;
            width: 28px;
            height: 28px;
            background: transparent;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            opacity: 0.3;
            transition: all 0.2s;
            z-index: 10;
        }
        .mode-toggle:hover {
            opacity: 0.7;
        }

        /* 触控板样式 - 全屏模式 */
        #touchpad-area {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: var(--bg-primary);
            z-index: 1000;
        }
        #touchpad-area.active {
            display: block;
        }
        #touchpad {
            width: 100%;
            height: 100%;
            background: var(--bg-input);
            touch-action: none;
            cursor: crosshair;
            position: relative;
        }
        #touchpad:active {
            background: var(--bg-card);
        }
        #touchpad::after {
            content: '单指点击=左键 | 双指点击=右键 | 快速双击=双击';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: var(--text-muted);
            font-size: 14px;
            pointer-events: none;
            text-align: center;
            line-height: 2;
        }
        .touchpad-exit {
            position: absolute;
            top: 16px;
            right: 16px;
            width: 48px;
            height: 48px;
            background: var(--bg-card);
            border: 1px solid var(--gold-primary);
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            z-index: 1001;
            color: var(--gold-primary);
        }
        .touchpad-exit:active {
            background: var(--gold-dark);
        }

        .btn-section {
            margin-top: 16px;
        }
        .section-label {
            color: var(--text-muted);
            font-size: 11px;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: 500;
        }
        .btn-row {
            display: flex;
            gap: var(--btn-gap);
        }
        .btn-row + .btn-row { margin-top: var(--btn-gap); }
        .btn {
            flex: 1;
            padding: var(--btn-padding);
            border: none;
            border-radius: var(--btn-radius);
            cursor: pointer;
            color: var(--text-primary);
            font-size: var(--btn-font);
            font-weight: 500;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            min-height: 48px;
            font-family: inherit;
        }
        .btn:active { transform: scale(0.97); }
        .btn-send {
            background: var(--gold-primary);
            color: var(--bg-primary);
            font-weight: 600;
        }
        .btn-send:hover { background: var(--gold-light); }
        .btn-enter {
            background: var(--success);
            color: #fff;
        }
        .btn-enter:hover { background: #5ab07e; }
        .btn-undo {
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
        }
        .btn-undo:hover { border-color: var(--border-hover); }
        .btn-undo.enabled {
            background: var(--bg-input);
            border-color: var(--gold-primary);
            color: var(--gold-primary);
        }
        .btn-undo:disabled { opacity: 0.3; cursor: not-allowed; }
        .btn-clear {
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
        }
        .btn-clear:hover {
            border-color: var(--danger);
            color: var(--danger);
        }
        .btn-dir {
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 1.2rem;
        }
        .btn-dir:hover {
            border-color: var(--border-hover);
            color: var(--text-primary);
        }
        .btn-symbol {
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
        }
        .btn-symbol:hover {
            border-color: var(--gold-primary);
            color: var(--gold-primary);
        }
        /* Modal */
        #symbol-modal {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.85);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            padding: 20px;
        }
        .modal-box {
            width: 100%;
            max-width: 380px;
            background: var(--bg-card);
            border-radius: 12px;
            padding: 28px;
            border: 1px solid var(--border-color);
        }
        .modal-title {
            color: var(--text-primary);
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 20px;
            text-align: center;
            letter-spacing: 1px;
        }
        #symbol-input {
            width: 100%;
            padding: 14px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: var(--bg-input);
            color: var(--text-primary);
            font-size: 15px;
            margin-bottom: 16px;
            transition: border-color 0.2s;
            font-family: inherit;
        }
        #symbol-input:focus {
            outline: none;
            border-color: var(--gold-primary);
        }
        #symbol-input::placeholder { color: var(--text-muted); }
        #confirm-symbol {
            width: 100%;
            padding: 14px;
            background: var(--gold-primary);
            color: var(--bg-primary);
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            font-family: inherit;
        }
        #confirm-symbol:hover { background: var(--gold-light); }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <div class="logo-icon">
                <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
            </div>
            <span class="logo-text">太白说</span>
            <span class="countdown-indicator" id="countdown">3s</span>
        </div>
        <button id="mode-btn" onclick="toggleMode()">放大</button>
        <button id="fullscreen-btn" onclick="toggleFullscreen()">全屏</button>
    </div>

    <div class="auto-send-bar">
        <label>
            <span class="toggle-switch">
                <input type="checkbox" id="auto-send-toggle">
                <span class="toggle-slider"></span>
            </span>
            自动发送
        </label>
        <select class="delay-select" id="delay-select">
            <option value="1000">1秒</option>
            <option value="2000">2秒</option>
            <option value="3000" selected>3秒</option>
            <option value="5000">5秒</option>
        </select>
    </div>

    <!-- 全屏触控板覆盖层 -->
    <div id="touchpad-area">
        <div id="touchpad"></div>
        <button class="touchpad-exit" onclick="toggleInputMode()">⌨️</button>
    </div>

    <div class="container">
        <div class="input-area">
            <button class="mode-toggle" id="mode-toggle" onclick="toggleInputMode()" title="切换触控板">🖱️</button>
            <textarea id="input-box" placeholder="输入内容，停止后自动发送..."></textarea>
        </div>

        <div class="quick-selects">
            <div class="custom-dropdown" id="cmd-dropdown">
                <button class="dropdown-toggle" onclick="toggleDropdown('cmd')">⚡</button>
                <div class="dropdown-menu" id="cmd-menu"></div>
            </div>
            <div class="custom-dropdown" id="phrase-dropdown">
                <button class="dropdown-toggle" onclick="toggleDropdown('phrase')">💬</button>
                <div class="dropdown-menu" id="phrase-menu"></div>
            </div>
            <div class="custom-dropdown" id="history-dropdown">
                <button class="dropdown-toggle" onclick="toggleDropdown('history')">🕐</button>
                <div class="dropdown-menu" id="history-menu"></div>
            </div>
            <button class="btn-enter-inline" onclick="sendEnter()">回车</button>
        </div>

        <div class="btn-section">
            <div class="btn-row">
                <button class="btn btn-send" onclick="sendText()">发送</button>
                <button class="btn btn-undo" id="undo-btn" onclick="undoLast()" disabled>撤销</button>
                <button class="btn btn-clear" onclick="clearInput()">清空</button>
            </div>
        </div>

        <div class="btn-section">
            <div class="section-label">光标控制</div>
            <div class="btn-row">
                <button class="btn btn-dir" id="btn-left" data-key="left">←</button>
                <button class="btn btn-dir" id="btn-up" data-key="up">↑</button>
                <button class="btn btn-dir" id="btn-down" data-key="down">↓</button>
                <button class="btn btn-dir" id="btn-right" data-key="right">→</button>
                <button class="btn btn-dir" id="btn-backspace" data-key="backspace">⌫</button>
            </div>
        </div>

        <div class="btn-section">
            <div class="section-label">快捷符号</div>
            <div class="btn-row">
                <button class="btn btn-symbol" onclick="openSymbolModal('()')">（）</button>
                <button class="btn btn-symbol" onclick="openSymbolModal('""')">""</button>
                <button class="btn btn-symbol" onclick="openSymbolModal('「」')">「」</button>
                <button class="btn btn-symbol" onclick="insertAtCursor('/')">/</button>
            </div>
            <div class="btn-row">
                <button class="btn btn-symbol" onclick="openSymbolModal('《》')">《》</button>
                <button class="btn btn-symbol" onclick="openSymbolModal('【】')">【】</button>
                <button class="btn btn-symbol" onclick="openSymbolModal('{}')">{ }</button>
                <button class="btn btn-symbol" onclick="openSymbolModal('[]')">[ ]</button>
            </div>
        </div>

    </div>

    <div id="symbol-modal">
        <div class="modal-box">
            <div class="modal-title">输入内容</div>
            <input type="text" id="symbol-input" placeholder="输入要包裹的文字...">
            <button id="confirm-symbol" onclick="confirmSymbol()">确认</button>
        </div>
    </div>

    <script>
        let hasHistory = false;
        let currentSymbol = "";
        let isLargeMode = false;
        let autoSendTimer = null;
        let countdownTimer = null;
        let countdownValue = 0;
        let isTouchpadMode = false;

        // 触控板相关
        const touchpad = document.getElementById('touchpad');
        const touchpadArea = document.getElementById('touchpad-area');
        const inputBox = document.getElementById('input-box');
        const modeToggleBtn = document.getElementById('mode-toggle');
        let touchStartX = 0;
        let touchStartY = 0;
        let touchStartTime = 0;
        let totalMoveDistance = 0;
        let isTouching = false;
        let touchCount = 0;
        let lastTapTime = 0;
        const SENSITIVITY = 4; // 灵敏度
        const TAP_THRESHOLD = 15; // 点击判定：移动距离小于此值
        const TAP_TIME = 250; // 点击判定：触摸时间小于此值(ms)
        const DOUBLE_TAP_TIME = 300; // 双击间隔时间(ms)

        function toggleInputMode() {
            isTouchpadMode = !isTouchpadMode;
            if (isTouchpadMode) {
                touchpadArea.classList.add('active');
            } else {
                touchpadArea.classList.remove('active');
            }
        }

        // 触控板事件处理
        function handleTouchStart(e) {
            e.preventDefault();
            isTouching = true;
            touchStartTime = Date.now();
            totalMoveDistance = 0;
            touchCount = e.touches ? e.touches.length : 1;
            const touch = e.touches ? e.touches[0] : e;
            touchStartX = touch.clientX;
            touchStartY = touch.clientY;
        }

        function handleTouchMove(e) {
            if (!isTouching) return;
            e.preventDefault();
            const touch = e.touches ? e.touches[0] : e;
            const rawDx = touch.clientX - touchStartX;
            const rawDy = touch.clientY - touchStartY;
            totalMoveDistance += Math.abs(rawDx) + Math.abs(rawDy);

            const dx = Math.round(rawDx * SENSITIVITY);
            const dy = Math.round(rawDy * SENSITIVITY);

            if (dx !== 0 || dy !== 0) {
                touchStartX = touch.clientX;
                touchStartY = touch.clientY;
                sendMouseMove(dx, dy);
            }
        }

        function handleTouchEnd(e) {
            if (!isTouching) return;
            const touchDuration = Date.now() - touchStartTime;
            const now = Date.now();

            // 判断是否为点击（移动距离小且时间短）
            if (totalMoveDistance < TAP_THRESHOLD && touchDuration < TAP_TIME) {
                if (touchCount >= 2) {
                    // 双指点击 = 右键
                    mouseClick('right', 1);
                } else {
                    // 单指点击，检测是否双击
                    if (now - lastTapTime < DOUBLE_TAP_TIME) {
                        mouseClick('left', 2); // 双击
                        lastTapTime = 0;
                    } else {
                        mouseClick('left', 1); // 单击
                        lastTapTime = now;
                    }
                }
            }
            isTouching = false;
            touchCount = 0;
        }

        // 节流发送鼠标移动
        let lastMoveTime = 0;
        const MOVE_THROTTLE = 16; // ~60fps

        function sendMouseMove(dx, dy) {
            const now = Date.now();
            if (now - lastMoveTime < MOVE_THROTTLE) return;
            lastMoveTime = now;

            fetch('/mouse_move', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({dx: dx, dy: dy})
            }).catch(err => console.log('Mouse move error:', err));
        }

        function mouseClick(button, clicks) {
            fetch('/mouse_click', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({button: button, clicks: clicks})
            }).catch(err => console.log('Mouse click error:', err));
        }

        // 绑定触控板事件
        touchpad.addEventListener('touchstart', handleTouchStart, {passive: false});
        touchpad.addEventListener('touchmove', handleTouchMove, {passive: false});
        touchpad.addEventListener('touchend', handleTouchEnd);
        touchpad.addEventListener('mousedown', handleTouchStart);
        touchpad.addEventListener('mousemove', handleTouchMove);
        touchpad.addEventListener('mouseup', handleTouchEnd);
        touchpad.addEventListener('mouseleave', handleTouchEnd);

        // 自动发送相关
        const autoSendToggle = document.getElementById('auto-send-toggle');
        const delaySelect = document.getElementById('delay-select');
        const countdownEl = document.getElementById('countdown');
        const MAX_HISTORY = 20;

        // 自定义下拉框元素
        const cmdMenu = document.getElementById('cmd-menu');
        const phraseMenu = document.getElementById('phrase-menu');
        const historyMenu = document.getElementById('history-menu');
        let activeDropdown = null;

        // 缓存数据
        let cachedCommands = [];
        let cachedPhrases = [];

        // 长按重复发送
        let repeatTimer = null;
        let currentPressItem = null;
        const REPEAT_INTERVAL = 500;
        const LONG_PRESS_DELAY = 300;

        // 切换下拉框
        function toggleDropdown(type) {
            const menuId = type + '-menu';
            const menu = document.getElementById(menuId);
            const wasOpen = menu.classList.contains('show');

            // 关闭所有下拉框
            closeAllDropdowns();

            // 如果之前是关闭的，则打开
            if (!wasOpen) {
                // 居中显示
                menu.style.left = '50%';
                menu.style.top = '50%';
                menu.style.transform = 'translate(-50%, -50%)';
                menu.classList.add('show');
                activeDropdown = type;
            }
        }

        function closeAllDropdowns() {
            document.querySelectorAll('.dropdown-menu').forEach(m => {
                m.classList.remove('show');
            });
            activeDropdown = null;
        }

        // 点击外部关闭下拉框
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.custom-dropdown')) {
                closeAllDropdowns();
            }
        });

        // 历史记录
        function getHistory() {
            return JSON.parse(localStorage.getItem('taibai_history') || '[]');
        }

        function addToHistory(text) {
            if (!text.trim()) return;
            let history = getHistory();
            history = history.filter(h => h !== text);
            history.unshift(text);
            if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY);
            localStorage.setItem('taibai_history', JSON.stringify(history));
            refreshHistoryMenu();
        }

        // 使用频率
        function getUsageCount(key) {
            const data = JSON.parse(localStorage.getItem('taibai_usage') || '{}');
            return data[key] || 0;
        }

        function incrementUsage(key) {
            const data = JSON.parse(localStorage.getItem('taibai_usage') || '{}');
            data[key] = (data[key] || 0) + 1;
            localStorage.setItem('taibai_usage', JSON.stringify(data));
        }

        function sortByUsage(items) {
            return [...items].sort((a, b) => getUsageCount(b) - getUsageCount(a));
        }

        function getDisplayText(str) {
            const text = str.startsWith('[KEY]') ? str.substring(5) : str;
            return text.length > 18 ? text.substring(0, 18) + '...' : text;
        }

        // 发送热键
        function sendHotkey(hotkey) {
            fetch('/send_hotkey', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({hotkey: hotkey})
            }).then(() => {
                hasHistory = true;
                updateUndoBtn();
            });
        }

        // 长按开始重复
        function startRepeat(hotkey, item) {
            currentPressItem = item;
            item.classList.add('pressing');
            sendHotkey(hotkey);
            repeatTimer = setInterval(() => sendHotkey(hotkey), REPEAT_INTERVAL);
        }

        function stopRepeat() {
            if (repeatTimer) {
                clearInterval(repeatTimer);
                repeatTimer = null;
            }
            if (currentPressItem) {
                currentPressItem.classList.remove('pressing');
                currentPressItem = null;
            }
        }

        // 创建下拉项
        function createDropdownItem(value, isHotkey, onClick) {
            const item = document.createElement('div');
            item.className = 'dropdown-item' + (isHotkey ? ' hotkey' : '');
            item.textContent = getDisplayText(value);
            item.dataset.value = value;

            let longPressTimer = null;
            let didLongPress = false;
            let startY = 0;
            let isCancelled = false;

            if (isHotkey) {
                // 热键支持长按，但要区分滑动
                const startPress = (e) => {
                    didLongPress = false;
                    isCancelled = false;
                    startY = e.touches ? e.touches[0].clientY : e.clientY;
                    const hotkey = value.substring(5);
                    longPressTimer = setTimeout(() => {
                        if (!isCancelled) {
                            didLongPress = true;
                            startRepeat(hotkey, item);
                        }
                    }, LONG_PRESS_DELAY);
                };

                const movePress = (e) => {
                    const currentY = e.touches ? e.touches[0].clientY : e.clientY;
                    // 滑动超过10px就取消
                    if (Math.abs(currentY - startY) > 10) {
                        isCancelled = true;
                        if (longPressTimer) {
                            clearTimeout(longPressTimer);
                            longPressTimer = null;
                        }
                        stopRepeat();
                    }
                };

                const endPress = (e) => {
                    if (longPressTimer) {
                        clearTimeout(longPressTimer);
                        longPressTimer = null;
                    }
                    stopRepeat();
                    if (!didLongPress && !isCancelled) {
                        // 短按且没滑动，发送一次
                        onClick(value);
                    }
                    didLongPress = false;
                    isCancelled = false;
                };

                item.addEventListener('touchstart', startPress, {passive: true});
                item.addEventListener('touchmove', movePress, {passive: true});
                item.addEventListener('touchend', endPress);
                item.addEventListener('touchcancel', endPress);
                item.addEventListener('mousedown', startPress);
                item.addEventListener('mousemove', movePress);
                item.addEventListener('mouseup', endPress);
                item.addEventListener('mouseleave', endPress);
            } else {
                // 普通文本，直接点击
                item.addEventListener('click', () => onClick(value));
            }

            return item;
        }

        // 刷新命令菜单
        function refreshCmdMenu() {
            cmdMenu.innerHTML = '';
            sortByUsage(cachedCommands).forEach(cmd => {
                const isHotkey = cmd.startsWith('[KEY]');
                const item = createDropdownItem(cmd, isHotkey, (val) => {
                    closeAllDropdowns();
                    clearAutoSendTimer();
                    incrementUsage(val);
                    if (isHotkey) {
                        sendHotkey(val.substring(5));
                    } else {
                        addToHistory(val);
                        fetch('/send', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({text: val})
                        }).then(() => fetch('/send_enter', {method: 'POST'}))
                          .then(() => { hasHistory = true; updateUndoBtn(); });
                    }
                    refreshCmdMenu();
                });
                cmdMenu.appendChild(item);
            });
        }

        // 刷新常用语菜单
        function refreshPhraseMenu() {
            phraseMenu.innerHTML = '';
            sortByUsage(cachedPhrases).forEach(phrase => {
                const item = createDropdownItem(phrase, false, (val) => {
                    closeAllDropdowns();
                    clearAutoSendTimer();
                    incrementUsage(val);
                    addToHistory(val);
                    fetch('/send', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({text: val})
                    }).then(() => fetch('/send_enter', {method: 'POST'}))
                      .then(() => { hasHistory = true; updateUndoBtn(); });
                    refreshPhraseMenu();
                });
                phraseMenu.appendChild(item);
            });
        }

        // 刷新历史菜单
        function refreshHistoryMenu() {
            historyMenu.innerHTML = '';
            getHistory().forEach(text => {
                const item = document.createElement('div');
                item.className = 'dropdown-item';
                item.textContent = text.length > 18 ? text.substring(0, 18) + '...' : text;
                item.addEventListener('click', () => {
                    closeAllDropdowns();
                    document.getElementById('input-box').value = text;
                    document.getElementById('input-box').focus();
                });
                historyMenu.appendChild(item);
            });
        }

        // 加载选项
        function loadOptions() {
            fetch('/get_options').then(r => r.json()).then(data => {
                cachedCommands = data.commands;
                cachedPhrases = data.phrases;
                refreshCmdMenu();
                refreshPhraseMenu();
            });
        }
        loadOptions();
        refreshHistoryMenu();

        function getDelay() {
            return parseInt(delaySelect.value);
        }

        function startAutoSendTimer() {
            if (!autoSendToggle.checked) return;
            const text = document.getElementById('input-box').value.trim();
            if (!text) return;

            clearAutoSendTimer();
            const delay = getDelay();
            countdownValue = delay / 1000;
            countdownEl.textContent = countdownValue + 's';
            countdownEl.classList.add('active');

            // 倒计时显示
            countdownTimer = setInterval(() => {
                countdownValue--;
                if (countdownValue > 0) {
                    countdownEl.textContent = countdownValue + 's';
                }
            }, 1000);

            // 自动发送
            autoSendTimer = setTimeout(() => {
                clearAutoSendTimer();
                sendText();
            }, delay);
        }

        function clearAutoSendTimer() {
            if (autoSendTimer) { clearTimeout(autoSendTimer); autoSendTimer = null; }
            if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
            countdownEl.classList.remove('active');
        }

        function toggleMode() {
            const body = document.body;
            const btn = document.getElementById('mode-btn');
            if (isLargeMode) {
                body.classList.remove('large-mode');
                btn.textContent = '放大';
                isLargeMode = false;
            } else {
                body.classList.add('large-mode');
                btn.textContent = '紧凑';
                isLargeMode = true;
            }
        }

        function toggleFullscreen() {
            const btn = document.getElementById('fullscreen-btn');
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().then(() => {
                    btn.textContent = '退出';
                }).catch(err => {
                    console.log('全屏失败:', err);
                });
            } else {
                document.exitFullscreen().then(() => {
                    btn.textContent = '全屏';
                });
            }
        }

        // 监听全屏状态变化
        document.addEventListener('fullscreenchange', () => {
            const btn = document.getElementById('fullscreen-btn');
            btn.textContent = document.fullscreenElement ? '退出' : '全屏';
        });

        function updateUndoBtn() {
            const btn = document.getElementById('undo-btn');
            btn.classList.toggle('enabled', hasHistory);
            btn.disabled = !hasHistory;
        }

        function sendText() {
            clearAutoSendTimer();
            const text = document.getElementById('input-box').value.trim();
            if (!text) return;
            addToHistory(text); // 保存到历史记录
            fetch('/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text})
            }).then(() => {
                hasHistory = true;
                updateUndoBtn();
                document.getElementById('input-box').value = '';
            });
        }

        function sendEnter() {
            const text = document.getElementById('input-box').value.trim();
            if (text) {
                // 先发送文本，再发送回车
                clearAutoSendTimer();
                addToHistory(text); // 保存到历史记录
                fetch('/send', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                }).then(() => {
                    document.getElementById('input-box').value = '';
                    return fetch('/send_enter', {method: 'POST'});
                }).then(() => {
                    hasHistory = true;
                    updateUndoBtn();
                });
            } else {
                // 文本框为空，直接发送回车
                fetch('/send_enter', {method: 'POST'}).then(() => {
                    hasHistory = true;
                    updateUndoBtn();
                });
            }
        }

        function undoLast() {
            fetch('/undo', {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.status === 'success') {
                    document.getElementById('input-box').value = data.content || '';
                    hasHistory = false;
                    updateUndoBtn();
                }
            });
        }

        function clearInput() {
            clearAutoSendTimer();
            document.getElementById('input-box').value = '';
        }

        function moveCursor(direction) {
            fetch('/move_cursor', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({direction: direction})
            }).then(() => {
                hasHistory = false;
                updateUndoBtn();
            });
        }

        function sendDelete() {
            fetch('/delete_pc', {method: 'POST'}).then(() => {
                hasHistory = false;
                updateUndoBtn();
            });
        }

        // 方向键和退格键长按支持
        function setupDirButton(btn) {
            const key = btn.dataset.key;
            let pressTimer = null;
            let repeatTimer = null;
            let didLongPress = false;

            const doAction = () => {
                if (key === 'backspace') {
                    sendDelete();
                } else {
                    moveCursor(key);
                }
            };

            const startPress = (e) => {
                e.preventDefault();
                didLongPress = false;
                doAction(); // 立即执行一次
                pressTimer = setTimeout(() => {
                    didLongPress = true;
                    repeatTimer = setInterval(doAction, 100); // 长按时100ms重复
                }, 300);
            };

            const endPress = () => {
                if (pressTimer) { clearTimeout(pressTimer); pressTimer = null; }
                if (repeatTimer) { clearInterval(repeatTimer); repeatTimer = null; }
            };

            btn.addEventListener('touchstart', startPress, {passive: false});
            btn.addEventListener('touchend', endPress);
            btn.addEventListener('touchcancel', endPress);
            btn.addEventListener('mousedown', startPress);
            btn.addEventListener('mouseup', endPress);
            btn.addEventListener('mouseleave', endPress);
        }

        // 初始化所有方向键按钮
        document.querySelectorAll('.btn-dir[data-key]').forEach(setupDirButton);

        function openSymbolModal(symbol) {
            currentSymbol = symbol;
            document.getElementById('symbol-modal').style.display = 'flex';
            const input = document.getElementById('symbol-input');
            input.value = '';
            setTimeout(() => input.focus(), 100);
        }

        function insertAtCursor(text) {
            const input = document.getElementById('input-box');
            const start = input.selectionStart, end = input.selectionEnd;
            input.value = input.value.substring(0, start) + text + input.value.substring(end);
            input.selectionStart = input.selectionEnd = start + text.length;
            input.focus();
        }

        function confirmSymbol() {
            const content = document.getElementById('symbol-input').value.trim();
            document.getElementById('symbol-modal').style.display = 'none';
            if (!content) return;
            const mid = currentSymbol.length / 2;
            insertAtCursor(currentSymbol.substring(0, mid) + content + currentSymbol.substring(mid));
        }

        document.getElementById('symbol-input').addEventListener('keydown', e => {
            if (e.key === 'Enter') { e.preventDefault(); confirmSymbol(); }
        });

        document.getElementById('symbol-modal').addEventListener('click', function(e) {
            if (e.target === this) this.style.display = 'none';
        });

        document.getElementById('input-box').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.value.trim() ? sendText() : sendEnter();
            }
            if (e.key === 'Backspace' && !this.value.trim()) {
                e.preventDefault();
                sendDelete();
            }
        });

        // 输入时触发自动发送倒计时
        document.getElementById('input-box').addEventListener('input', startAutoSendTimer);
        // 切换自动发送时保存设置并清除倒计时
        autoSendToggle.addEventListener('change', function() {
            localStorage.setItem('taibai_auto_send', this.checked ? '1' : '0');
            clearAutoSendTimer();
        });
        // 延迟时间改变时保存设置
        delaySelect.addEventListener('change', function() {
            localStorage.setItem('taibai_auto_delay', this.value);
        });

        // 页面加载时恢复设置
        (function loadSettings() {
            const savedAutoSend = localStorage.getItem('taibai_auto_send');
            const savedDelay = localStorage.getItem('taibai_auto_delay');
            if (savedAutoSend === '1') {
                autoSendToggle.checked = true;
            }
            if (savedDelay) {
                delaySelect.value = savedDelay;
            }
        })();
    </script>
</body>
</html>
'''

# ------------ 密码验证页面模板 ------------
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>密码验证 - 太白说</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600&display=swap');

        :root {
            --bg-primary: #0a0a0a;
            --bg-card: #161616;
            --bg-input: #1a1a1a;
            --border-color: #2a2a2a;
            --gold-primary: #c9a962;
            --gold-light: #d4b87a;
            --text-primary: #e8e8e8;
            --text-secondary: #888888;
            --text-muted: #555555;
            --danger: #9f4a4a;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: var(--bg-primary);
            font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
            padding: 20px;
        }
        .login-card {
            background: var(--bg-card);
            padding: 50px 40px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            width: 100%;
            max-width: 380px;
            text-align: center;
        }
        .logo {
            width: 70px;
            height: 70px;
            background: var(--bg-input);
            border: 1px solid var(--gold-primary);
            border-radius: 12px;
            margin: 0 auto 25px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .logo svg {
            width: 36px;
            height: 36px;
            fill: var(--gold-primary);
        }
        h1 {
            font-size: 22px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 8px;
            letter-spacing: 2px;
        }
        .subtitle {
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 35px;
        }
        .input-group {
            position: relative;
            margin-bottom: 25px;
        }
        .input-group input {
            width: 100%;
            padding: 16px 20px 16px 50px;
            font-size: 15px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: var(--bg-input);
            transition: all 0.2s ease;
            color: var(--text-primary);
            font-family: inherit;
        }
        .input-group input:focus {
            outline: none;
            border-color: var(--gold-primary);
            box-shadow: 0 0 0 3px rgba(201, 169, 98, 0.1);
        }
        .input-group input::placeholder {
            color: var(--text-muted);
        }
        .input-group .icon {
            position: absolute;
            left: 18px;
            top: 50%;
            transform: translateY(-50%);
            width: 18px;
            height: 18px;
            fill: var(--text-muted);
            transition: fill 0.2s;
        }
        .input-group input:focus + .icon {
            fill: var(--gold-primary);
        }
        button {
            width: 100%;
            padding: 16px;
            font-size: 14px;
            font-weight: 600;
            background: var(--gold-primary);
            color: var(--bg-primary);
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-family: inherit;
            letter-spacing: 2px;
        }
        button:hover {
            background: var(--gold-light);
        }
        button:active {
            transform: scale(0.98);
        }
        .error-msg {
            background: rgba(159, 74, 74, 0.1);
            color: #cf6b6b;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 13px;
            margin-bottom: 20px;
            display: none;
            border: 1px solid rgba(159, 74, 74, 0.3);
        }
        .error-msg.show { display: block; }
        .shake {
            animation: shake 0.4s ease-in-out;
        }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-6px); }
            75% { transform: translateX(6px); }
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="logo">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
        </div>
        <h1>太白说</h1>
        <p class="subtitle">请输入访问密码以继续</p>
        <div class="error-msg" id="error-msg">密码错误，请重试</div>
        <form id="login-form">
            <div class="input-group">
                <input type="password" id="password" placeholder="输入密码" autofocus>
                <svg class="icon" viewBox="0 0 24 24">
                    <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/>
                </svg>
            </div>
            <button type="submit">验 证</button>
        </form>
    </div>
    <script>
        const form = document.getElementById('login-form');
        const card = document.querySelector('.login-card');
        const errorMsg = document.getElementById('error-msg');
        const passwordInput = document.getElementById('password');
        const STORAGE_KEY = 'taibai_auth_pwd';

        function tryLogin(pwd) {
            fetch('/auth', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({password: pwd})
            }).then(r => r.json()).then(data => {
                if (data.status === 'success') {
                    localStorage.setItem(STORAGE_KEY, pwd);
                    window.location.href = '/';
                } else {
                    localStorage.removeItem(STORAGE_KEY);
                    errorMsg.classList.add('show');
                    card.classList.add('shake');
                    passwordInput.value = '';
                    passwordInput.focus();
                    setTimeout(() => card.classList.remove('shake'), 500);
                }
            });
        }

        // 页面加载时尝试自动登录
        const savedPwd = localStorage.getItem(STORAGE_KEY);
        if (savedPwd) {
            passwordInput.value = savedPwd;
            tryLogin(savedPwd);
        }

        form.addEventListener('submit', function(e) {
            e.preventDefault();
            tryLogin(passwordInput.value);
        });

        passwordInput.addEventListener('input', () => {
            errorMsg.classList.remove('show');
        });
    </script>
</body>
</html>
'''

# ------------ 密码验证辅助函数 ------------
def check_auth():
    """检查是否需要密码验证，以及是否已通过验证"""
    if AUTH_PASSWORD is None:
        return True  # 未设置密码，无需验证
    return session.get('authenticated', False)

# ------------ 原有接口部分 ------------
@app.route('/')
def index():
    if not check_auth():
        return render_template_string(LOGIN_TEMPLATE)
    return render_template_string(HTML_TEMPLATE)

@app.route('/auth', methods=['POST'])
def auth():
    data = request.get_json()
    password = data.get('password', '')
    if password == AUTH_PASSWORD:
        session['authenticated'] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "failed"})

@app.route('/get_options')
def get_options():
    """获取命令和常用语配置"""
    return jsonify({"commands": COMMANDS, "phrases": PHRASES})

@app.route('/send', methods=['POST'])
def send_text():
    global LAST_OPERATION
    data = request.get_json()
    text = data.get('text', '').strip()
    if text:
        # 记录文本类型操作
        LAST_OPERATION = {"type": "text", "content": text}
        replaced_text = apply_replace_rules(text)
        paste_text(replaced_text)
        print(f"原始文本：{text} → 替换后：{replaced_text}")
    return jsonify({"status": "success"})

@app.route('/send_enter', methods=['POST'])
def send_enter():
    global LAST_OPERATION
    # 记录回车类型操作
    LAST_OPERATION = {"type": "enter", "content": ""}
    pyautogui.press('enter')
    print("执行回车操作，已记录历史")
    return jsonify({"status": "success"})

@app.route('/send_hotkey', methods=['POST'])
def send_hotkey():
    """发送热键组合或单个按键"""
    global LAST_OPERATION
    data = request.get_json()
    hotkey_str = data.get('hotkey', '').strip()
    if not hotkey_str:
        return jsonify({"status": "failed", "msg": "热键为空"})

    try:
        if '+' in hotkey_str:
            # 组合键，如 "Ctrl+Shift+P" -> ['ctrl', 'shift', 'p']
            keys = [k.strip().lower() for k in hotkey_str.split('+')]
            # 映射特殊键名
            key_map = {'ctrl': 'ctrl', 'shift': 'shift', 'alt': 'alt', 'win': 'win', 'cmd': 'command', '`': 'backquote'}
            mapped_keys = [key_map.get(k, k) for k in keys]
            pyautogui.hotkey(*mapped_keys)
        else:
            # 单个按键，如 "Up", "Down", "Enter"
            key_map = {
                'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
                'home': 'home', 'end': 'end', 'pageup': 'pageup', 'pagedown': 'pagedown',
                'enter': 'enter', 'tab': 'tab', 'escape': 'escape', 'esc': 'escape',
                'backspace': 'backspace', 'delete': 'delete', 'space': 'space'
            }
            key = key_map.get(hotkey_str.lower(), hotkey_str.lower())
            pyautogui.press(key)

        LAST_OPERATION = {"type": "hotkey", "content": hotkey_str}
        print(f"执行热键：{hotkey_str}")
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"热键执行失败：{e}")
        return jsonify({"status": "failed", "msg": str(e)})

@app.route('/mouse_move', methods=['POST'])
def mouse_move():
    """移动鼠标（相对位移）"""
    data = request.get_json()
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    try:
        pyautogui.moveRel(dx, dy, _pause=False)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "failed", "msg": str(e)})

@app.route('/mouse_click', methods=['POST'])
def mouse_click():
    """鼠标点击"""
    data = request.get_json()
    button = data.get('button', 'left')  # left/right
    clicks = data.get('clicks', 1)       # 1=单击, 2=双击
    try:
        pyautogui.click(button=button, clicks=clicks)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "failed", "msg": str(e)})

@app.route('/undo', methods=['POST'])
def undo_last():
    global LAST_OPERATION
    if not LAST_OPERATION["type"]:
        return jsonify({"status": "failed", "msg": "无历史操作可撤销"})
    
    # 执行对应类型的撤销动作
    undo_last_operation()
    # 提取要恢复的内容（文本操作返回原文本，回车操作返回空）
    recover_content = LAST_OPERATION["content"]
    # 清空历史操作，防止重复撤销
    LAST_OPERATION = {"type": None, "content": ""}
    
    return jsonify({
        "status": "success",
        "content": recover_content
    })

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    finally:
        s.close()
    return local_ip

# 新增：生成终端二维码函数
# def generate_cli_qrcode(url):
#     qr_main(['--factory', 'qrcode.terminal.Basic', url])

import qrcode_terminal
def generate_cli_qrcode(url):
    qrcode_terminal.draw(url)


if __name__ == '__main__':
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='太白说 - 手机输入同步到电脑')
    parser.add_argument('-p', '--port', type=int, default=5000, help='服务端口号 (默认: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址 (默认: 0.0.0.0)')
    parser.add_argument('--url', type=str, default=None, help='外部访问地址 (用于反向代理，如: https://example.com)')
    parser.add_argument('--password', type=str, default=None, help='访问密码 (不设置则无需验证)')
    parser.add_argument('--no-qrcode', action='store_true', help='不显示二维码')
    args = parser.parse_args()

    # 设置密码
    AUTH_PASSWORD = args.password

    local_ip = get_local_ip()
    port = args.port
    # 如果指定了外部 URL 则使用，否则使用局域网地址
    if args.url:
        access_url = args.url.rstrip('/')  # 移除末尾斜杠
    else:
        access_url = f"http://{local_ip}:{port}"

    # 生成并输出终端二维码
    if not args.no_qrcode:
        generate_cli_qrcode(access_url)
    print(f"\n服务器已启动！")
    print(f"手机访问地址（或扫描上面的二维码）：{access_url}")
    print(f"已加载 {len(REPLACE_RULES)} 条替换规则")
    if args.password:
        print(f"密码保护：已启用")
    else:
        print(f"密码保护：未启用")
    if args.url:
        print(f"使用外部地址模式（反向代理）")
    else:
        print(f"注意：手机和电脑需在同一局域网下")

    app.run(host=args.host, port=port, debug=False, threaded=True)
