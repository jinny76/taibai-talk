from flask import Flask, request, render_template, jsonify, session, redirect, url_for, Response, send_file
import pyautogui
import pyperclip
import socket
import re
import os
import time
import sys
import argparse
import secrets
import io
# 新增：导入二维码生成库
import qrcode
from qrcode.console_scripts import main as qr_main

# 处理 PyInstaller 打包时的路径
if getattr(sys, 'frozen', False):
    # 打包后：模板和静态资源在 _MEIPASS 临时目录
    BASE_PATH = sys._MEIPASS
    template_folder = os.path.join(BASE_PATH, 'templates')
else:
    # 开发环境
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    template_folder = os.path.join(BASE_PATH, 'templates')

app = Flask(__name__, template_folder=template_folder)
app.secret_key = secrets.token_hex(16)  # 用于 session 加密

# 密码配置（启动时通过参数设置）
AUTH_PASSWORD = None

# 暴力破解防护
LOGIN_ATTEMPTS = {}  # {ip: {"count": 次数, "lockout_until": 锁定截止时间}}
MAX_ATTEMPTS = 5  # 最大尝试次数
LOCKOUT_TIME = 300  # 锁定时间（秒）

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

# ------------ 密码验证辅助函数 ------------
def check_auth():
    """检查是否需要密码验证，以及是否已通过验证"""
    if AUTH_PASSWORD is None:
        return True  # 未设置密码，无需验证
    return session.get('authenticated', False)

@app.before_request
def require_auth():
    """所有 API 请求都需要认证（除了首页、登录、健康检测和图标接口）"""
    # 不需要认证的路由
    public_routes = ['/', '/auth', '/health', '/favicon.ico']
    if request.path in public_routes:
        return None
    # 检查认证
    if not check_auth():
        return jsonify({"status": "unauthorized", "msg": "请先登录"}), 401

# ------------ 原有接口部分 ------------
@app.route('/favicon.ico')
def favicon():
    """网站图标"""
    icon_path = os.path.join(BASE_PATH, 'icon.ico')
    return send_file(icon_path, mimetype='image/x-icon')

@app.route('/health')
def health():
    """健康检测端点，不需要认证"""
    return jsonify({"status": "ok", "authenticated": check_auth()})

@app.route('/')
def index():
    if not check_auth():
        return render_template('login.html')
    return render_template('index.html')

@app.route('/auth', methods=['POST'])
def auth():
    ip = request.remote_addr
    now = time.time()

    # 检查是否被锁定
    if ip in LOGIN_ATTEMPTS:
        attempt = LOGIN_ATTEMPTS[ip]
        if attempt.get("lockout_until", 0) > now:
            remaining = int(attempt["lockout_until"] - now)
            return jsonify({"status": "locked", "msg": f"尝试次数过多，请{remaining}秒后重试"}), 429

    data = request.get_json()
    password = data.get('password', '')

    if password == AUTH_PASSWORD:
        session['authenticated'] = True
        # 登录成功，清除失败记录
        if ip in LOGIN_ATTEMPTS:
            del LOGIN_ATTEMPTS[ip]
        return jsonify({"status": "success"})

    # 登录失败，记录尝试次数
    if ip not in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[ip] = {"count": 0}
    LOGIN_ATTEMPTS[ip]["count"] += 1

    # 超过最大尝试次数，锁定
    if LOGIN_ATTEMPTS[ip]["count"] >= MAX_ATTEMPTS:
        LOGIN_ATTEMPTS[ip]["lockout_until"] = now + LOCKOUT_TIME
        return jsonify({"status": "locked", "msg": f"尝试次数过多，请{LOCKOUT_TIME}秒后重试"}), 429

    remaining_attempts = MAX_ATTEMPTS - LOGIN_ATTEMPTS[ip]["count"]
    return jsonify({"status": "failed", "msg": f"密码错误，还剩{remaining_attempts}次机会"})

@app.route('/get_options')
def get_options():
    """获取命令和常用语配置"""
    return jsonify({"commands": COMMANDS, "phrases": PHRASES})

@app.route('/save_options', methods=['POST'])
def save_options():
    """保存命令和常用语配置到文件"""
    global COMMANDS, PHRASES
    data = request.get_json()
    commands = data.get('commands', [])
    phrases = data.get('phrases', [])

    # 确定配置文件目录
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        # 保存命令列表
        cmd_file = os.path.join(exe_dir, "commands.txt")
        with open(cmd_file, 'w', encoding='utf-8') as f:
            f.write("# Claude Code 常用命令和热键\n")
            f.write("# 每行一个命令，#开头为注释\n")
            f.write("# [KEY] 前缀表示热键，会直接发送按键而非文本\n\n")
            for cmd in commands:
                if cmd.strip():
                    f.write(cmd.strip() + '\n')

        # 保存常用语列表
        phrase_file = os.path.join(exe_dir, "phrases.txt")
        with open(phrase_file, 'w', encoding='utf-8') as f:
            f.write("# 常用语配置文件 - Vibe Coding 专用\n")
            f.write("# 每行一个常用语，#开头为注释\n\n")
            for phrase in phrases:
                if phrase.strip():
                    f.write(phrase.strip() + '\n')

        # 重新加载配置
        COMMANDS = [c.strip() for c in commands if c.strip()]
        PHRASES = [p.strip() for p in phrases if p.strip()]

        print(f"配置已保存：{len(COMMANDS)} 条命令，{len(PHRASES)} 条常用语")
        return jsonify({"status": "success"})

    except Exception as e:
        print(f"保存配置失败：{e}")
        return jsonify({"status": "failed", "msg": str(e)})

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

@app.route('/screenshot')
def screenshot():
    """截取当前屏幕并返回 JPEG 图片"""
    try:
        # 截取屏幕
        img = pyautogui.screenshot()
        # 转换为 JPEG 格式（比 PNG 小很多，传输更快）
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=75)
        buffer.seek(0)
        print("截屏成功")
        return Response(buffer.getvalue(), mimetype='image/jpeg')
    except Exception as e:
        print(f"截屏失败：{e}")
        return jsonify({"status": "failed", "msg": str(e)}), 500

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
    """获取本机局域网 IP，优先级：192.168.x.x > 10.x.x.x > 172.x.x.x"""
    import subprocess
    try:
        # Windows: 使用 ipconfig 获取所有 IP
        result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='gbk', errors='ignore')
        lines = result.stdout.split('\n')

        ips_192 = []  # 192.168.x.x
        ips_10 = []   # 10.x.x.x
        ips_172 = []  # 172.16-31.x.x

        for line in lines:
            if 'IPv4' in line or 'IP Address' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    ip = parts[-1].strip()
                    if ip.startswith('192.168.'):
                        ips_192.append(ip)
                    elif ip.startswith('10.'):
                        ips_10.append(ip)
                    elif ip.startswith('172.'):
                        # 检查是否在 172.16.0.0 - 172.31.255.255 范围
                        second_octet = int(ip.split('.')[1])
                        if 16 <= second_octet <= 31:
                            ips_172.append(ip)

        # 按优先级返回
        if ips_192:
            return ips_192[0]
        if ips_10:
            return ips_10[0]
        if ips_172:
            return ips_172[0]
    except Exception:
        pass

    # Fallback: 使用 socket 方法
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
    parser.add_argument('-p', '--port', type=int, default=57777, help='服务端口号 (默认: 57777)')
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

    # 打包版本禁用 HTTP 请求日志
    if getattr(sys, 'frozen', False):
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

    app.run(host=args.host, port=port, debug=False, threaded=True)
