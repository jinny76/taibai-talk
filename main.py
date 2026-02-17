from flask import Flask, request, render_template, jsonify, session, redirect, url_for, Response, send_file
import pyautogui
import pyperclip
import socket
import re
import os
import time
import sys
import argparse
import threading
import secrets
import io
import ctypes
import subprocess
import shutil
import hashlib
import getpass
# 新增：导入二维码生成库
import qrcode
# 导入解锁服务客户端
try:
    import unlock_service_client
    UNLOCK_SERVICE_AVAILABLE = True
except ImportError:
    UNLOCK_SERVICE_AVAILABLE = False
    print("警告：unlock_service_client 未找到，锁屏截图功能不可用")
from qrcode.console_scripts import main as qr_main

# ===== 版本号（打包时同步更新）=====
VERSION = "1.0.0"

# ===== 解锁密码（启动时输入，不存储）=====
UNLOCK_PASSWORD = None

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

# ===== 服务管理函数 =====
SERVICE_NAME = "TaiBaiService"
SERVICE_FILES = ["TaiBaiService.exe", "TaiBaiHelper.exe"]
VERSION_FILE = "TaiBaiService.version"

def is_admin():
    """检测是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin_and_restart():
    """请求管理员权限并重启程序"""
    if sys.platform != 'win32':
        return False

    try:
        # 使用 ShellExecute 以管理员身份重新运行
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)
    except Exception as e:
        print(f"请求管理员权限失败: {e}")
        return False

def get_file_hash(filepath):
    """计算文件的 MD5 哈希"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def get_service_dir():
    """获取服务文件应该安装的目录"""
    return os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')

def get_bundled_service_path():
    """获取打包的服务文件路径"""
    if getattr(sys, 'frozen', False):
        # 打包后：服务文件在 _MEIPASS 目录下的 unlock-service 子目录
        return os.path.join(sys._MEIPASS, 'unlock-service')
    else:
        # 开发环境：服务文件在 unlock-service/build/bin/Release
        return os.path.join(BASE_PATH, 'unlock-service', 'build', 'bin', 'Release')

def check_service_version():
    """检查已安装的服务版本是否匹配当前版本"""
    service_dir = get_service_dir()
    bundled_dir = get_bundled_service_path()

    # 检查打包的服务文件是否存在
    if not os.path.exists(bundled_dir):
        print(f"警告：服务文件目录不存在: {bundled_dir}")
        return True  # 开发环境可能没有编译，跳过检查

    for filename in SERVICE_FILES:
        bundled_file = os.path.join(bundled_dir, filename)
        installed_file = os.path.join(service_dir, filename)

        if not os.path.exists(bundled_file):
            print(f"警告：打包的服务文件不存在: {bundled_file}")
            return True  # 跳过检查

        if not os.path.exists(installed_file):
            print(f"服务文件未安装: {filename}")
            return False

        # 比较文件哈希
        bundled_hash = get_file_hash(bundled_file)
        installed_hash = get_file_hash(installed_file)

        if bundled_hash != installed_hash:
            print(f"服务文件版本不匹配: {filename}")
            return False

    return True

def stop_service():
    """停止服务"""
    try:
        # 先尝试通过服务控制停止
        subprocess.run(
            [os.path.join(get_service_dir(), 'TaiBaiService.exe'), '/stop'],
            capture_output=True, timeout=10
        )
    except:
        pass

    # 强制结束进程
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'TaiBaiService.exe'],
                      capture_output=True, timeout=5)
        subprocess.run(['taskkill', '/F', '/IM', 'TaiBaiHelper.exe'],
                      capture_output=True, timeout=5)
    except:
        pass

    time.sleep(1)

def install_service():
    """安装/更新服务"""
    service_dir = get_service_dir()
    bundled_dir = get_bundled_service_path()

    if not os.path.exists(bundled_dir):
        print(f"错误：服务文件目录不存在: {bundled_dir}")
        return False

    print("正在安装解锁服务...")

    # 停止现有服务
    stop_service()

    # 卸载旧服务（如果存在）
    service_exe = os.path.join(service_dir, 'TaiBaiService.exe')
    if os.path.exists(service_exe):
        try:
            subprocess.run([service_exe, '/uninstall'], capture_output=True, timeout=10)
            time.sleep(1)
        except:
            pass

    # 复制服务文件
    for filename in SERVICE_FILES:
        src = os.path.join(bundled_dir, filename)
        dst = os.path.join(service_dir, filename)

        if not os.path.exists(src):
            print(f"错误：源文件不存在: {src}")
            return False

        try:
            shutil.copy2(src, dst)
            print(f"  已复制: {filename}")
        except Exception as e:
            print(f"错误：复制 {filename} 失败: {e}")
            return False

    # 安装服务
    try:
        result = subprocess.run(
            [os.path.join(service_dir, 'TaiBaiService.exe'), '/install'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print(f"服务安装返回: {result.returncode}")
    except Exception as e:
        print(f"警告：服务安装命令执行异常: {e}")

    # 启动服务
    try:
        result = subprocess.run(
            [os.path.join(service_dir, 'TaiBaiService.exe'), '/start'],
            capture_output=True, text=True, timeout=10
        )
        print("解锁服务已启动")
    except Exception as e:
        print(f"警告：服务启动异常: {e}")

    return True

def ensure_service_installed():
    """确保服务已安装且版本正确"""
    if sys.platform != 'win32':
        print("解锁服务仅支持 Windows")
        return False

    # 检查版本
    if check_service_version():
        # 版本匹配，检查服务是否在运行
        try:
            result = subprocess.run(
                ['sc', 'query', SERVICE_NAME],
                capture_output=True, text=True, timeout=5
            )
            if 'RUNNING' in result.stdout:
                print("解锁服务已在运行")
                return True
            else:
                # 服务已安装但未运行，启动它
                subprocess.run(
                    [os.path.join(get_service_dir(), 'TaiBaiService.exe'), '/start'],
                    capture_output=True, timeout=10
                )
                print("解锁服务已启动")
                return True
        except:
            pass

    # 需要安装或更新服务
    if not is_admin():
        print("\n需要管理员权限来安装解锁服务...")
        print("程序将请求管理员权限并重启。\n")
        input("按 Enter 继续...")
        request_admin_and_restart()
        return False

    return install_service()

def get_unlock_password_from_user():
    """从控制台获取解锁密码"""
    global UNLOCK_PASSWORD
    print("\n" + "="*50)
    print("解锁密码设置")
    print("="*50)
    print("此密码用于远程解锁电脑屏幕。")
    print("密码不会被存储，每次启动都需要输入。")
    print("如果不需要远程解锁功能，直接按 Enter 跳过。")
    print("="*50)

    try:
        password = getpass.getpass("请输入 Windows 登录密码（输入时不显示）: ")
        if password:
            UNLOCK_PASSWORD = password
            print("✓ 解锁密码已设置")
        else:
            print("- 跳过解锁密码设置，远程解锁功能不可用")
    except Exception as e:
        print(f"密码输入异常: {e}")
        UNLOCK_PASSWORD = None

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

# ===== 锁屏检测功能 =====
def is_screen_locked():
    """检测 Windows 屏幕是否锁定"""
    try:
        user32 = ctypes.windll.user32
        # 尝试打开默认桌面
        hDesk = user32.OpenDesktopW("default", 0, False, 0x0100)  # DESKTOP_SWITCHDESKTOP
        if hDesk:
            # 尝试切换到该桌面
            result = user32.SwitchDesktop(hDesk)
            user32.CloseDesktop(hDesk)
            return not result  # 切换失败说明锁屏
        return True
    except Exception as e:
        print(f"锁屏检测异常: {e}")
        return False


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

        # 使用 pyautogui 发送文本
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

@app.route('/mouse_move_to', methods=['POST'])
def mouse_move_to():
    """移动鼠标到绝对位置"""
    data = request.get_json()
    x = data.get('x', 0)
    y = data.get('y', 0)
    try:
        # 获取屏幕尺寸，确保坐标在范围内
        screen_width, screen_height = pyautogui.size()
        x = max(0, min(x, screen_width - 1))
        y = max(0, min(y, screen_height - 1))
        pyautogui.moveTo(x, y, _pause=False)
        print(f"鼠标移动到: ({x}, {y})")
        return jsonify({"status": "success", "x": x, "y": y})
    except Exception as e:
        return jsonify({"status": "failed", "msg": str(e)})

@app.route('/screen_size')
def screen_size():
    """获取屏幕尺寸"""
    try:
        width, height = pyautogui.size()
        return jsonify({"width": width, "height": height})
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

@app.route('/check_locked')
def check_locked():
    """检测屏幕是否锁定"""
    try:
        locked = is_screen_locked()
        print(f"[锁屏检测] locked={locked}")
        return jsonify({"status": "success", "locked": locked})
    except Exception as e:
        print(f"[锁屏检测] 异常: {e}")
        return jsonify({"status": "failed", "msg": str(e)}), 500

@app.route('/unlock', methods=['POST'])
def unlock_screen():
    """远程解锁屏幕 - 使用服务直接在锁屏界面输入密码"""
    print("[解锁] 收到解锁请求")

    # 使用启动时设置的密码
    if not UNLOCK_PASSWORD:
        return jsonify({"status": "failed", "msg": "未设置解锁密码，请重启程序并设置密码"})

    password = UNLOCK_PASSWORD
    print(f"[解锁] 密码长度: {len(password)}")

    # 先检测是否锁屏
    locked = is_screen_locked()
    print(f"[解锁] 当前锁屏状态: {locked}")
    if not locked:
        return jsonify({"status": "success", "msg": "屏幕未锁定"})

    # 使用服务解锁
    if not UNLOCK_SERVICE_AVAILABLE:
        return jsonify({"status": "failed", "msg": "解锁服务不可用"})

    print("[解锁] 使用 Helper 解锁...")
    try:
        client = unlock_service_client.get_client()
        # 调用统一的 unlock 命令（唤醒、清空、输入密码、回车）
        if client.unlock(password):
            print("[解锁] 解锁命令已发送")
            return jsonify({"status": "success", "msg": "解锁命令已发送"})
        else:
            return jsonify({"status": "failed", "msg": "解锁失败"})
    except Exception as e:
        print(f"[解锁] 服务异常: {e}")
        return jsonify({"status": "failed", "msg": str(e)})

@app.route('/screenshot')
def screenshot():
    """截取当前屏幕并返回 JPEG 图片，带鼠标位置标记"""
    try:
        # 检查是否锁屏，锁屏时使用服务截图
        locked = is_screen_locked()
        if locked and UNLOCK_SERVICE_AVAILABLE:
            print("[截屏] 屏幕已锁定，使用服务截图")
            result = unlock_service_client.get_screenshot()
            if result and result.get('data'):
                print(f"[截屏] 服务截图成功: {result['width']}x{result['height']}")
                return Response(result['data'], mimetype='image/jpeg')
            else:
                print("[截屏] 服务截图失败")
                return jsonify({"status": "failed", "msg": "锁屏截图失败"}), 500

        from PIL import ImageDraw
        # 截取屏幕
        img = pyautogui.screenshot()
        # 获取鼠标位置并绘制标记
        mouse_x, mouse_y = pyautogui.position()
        draw = ImageDraw.Draw(img)
        # 绘制红色十字光标
        size = 15
        width = 3
        draw.line([(mouse_x - size, mouse_y), (mouse_x + size, mouse_y)], fill='red', width=width)
        draw.line([(mouse_x, mouse_y - size), (mouse_x, mouse_y + size)], fill='red', width=width)
        # 绘制红色圆圈
        draw.ellipse([(mouse_x - 8, mouse_y - 8), (mouse_x + 8, mouse_y + 8)], outline='red', width=2)
        # 转换为 JPEG 格式
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

# 防锁屏：定期微移鼠标
def keep_awake_loop(interval=60):
    """后台线程：每隔 interval 秒微移鼠标防止锁屏"""
    while True:
        time.sleep(interval)
        try:
            x, y = pyautogui.position()
            pyautogui.moveRel(1, 0, duration=0)
            pyautogui.moveRel(-1, 0, duration=0)
        except:
            pass


if __name__ == '__main__':
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='太白说 - 手机输入同步到电脑')
    parser.add_argument('-p', '--port', type=int, default=57777, help='服务端口号 (默认: 57777)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址 (默认: 0.0.0.0)')
    parser.add_argument('--url', type=str, default=None, help='外部访问地址 (用于反向代理，如: https://example.com)')
    parser.add_argument('--password', type=str, default=None, help='访问密码 (不设置则无需验证)')
    parser.add_argument('--no-qrcode', action='store_true', help='不显示二维码')
    parser.add_argument('--keep-awake', type=int, default=0, metavar='SEC', help='防锁屏：每隔 N 秒微移鼠标 (0=禁用)')
    parser.add_argument('--no-unlock', action='store_true', help='禁用解锁服务（跳过服务安装和密码输入）')
    args = parser.parse_args()

    print(f"\n太白说 v{VERSION}")
    print("="*50)

    # 设置密码
    AUTH_PASSWORD = args.password

    # 安装/检查解锁服务（Windows only）
    if sys.platform == 'win32' and not args.no_unlock:
        if UNLOCK_SERVICE_AVAILABLE:
            ensure_service_installed()
            # 获取解锁密码
            get_unlock_password_from_user()
        else:
            print("警告：解锁服务模块未加载，跳过服务安装")
    elif args.no_unlock:
        print("解锁服务：已禁用 (--no-unlock)")

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

    # 启动防锁屏线程
    if args.keep_awake > 0:
        awake_thread = threading.Thread(target=keep_awake_loop, args=(args.keep_awake,), daemon=True)
        awake_thread.start()
        print(f"防锁屏：已启用 (每 {args.keep_awake} 秒)")

    # 打包版本禁用 HTTP 请求日志
    if getattr(sys, 'frozen', False):
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

    app.run(host=args.host, port=port, debug=False, threaded=True)
