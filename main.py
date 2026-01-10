from flask import Flask, request, render_template_string, jsonify
import pyautogui
import pyperclip
import socket
import re
import os

app = Flask(__name__)

# 存储正则替换规则（key: 编译后的正则表达式，value: 替换式）
REPLACE_RULES = []

def load_replace_rules():
    """加载 EXE 所在目录下的 hot-rule.txt 替换规则"""
    # ===== 核心修复：获取 EXE 实际运行目录 =====
    if getattr(sys, 'frozen', False):
        # 情况1：打包成 EXE 运行
        exe_dir = os.path.dirname(sys.executable)  # EXE 所在文件夹路径
    else:
        # 情况2：源码运行（Python main.py）
        exe_dir = os.path.dirname(os.path.abspath(__file__))  # 源码所在文件夹
    
    # 拼接规则文件路径：EXE目录 + hot-rule.txt
    rule_file = os.path.join(exe_dir, "hot-rule.txt")

    # 后续逻辑不变
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

# 程序启动时加载规则
load_replace_rules()

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

# 网页前端模板（保持原有按钮布局不变）
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>手机-电脑输入同步（支持正则替换）</title>
    <style>
        body {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 50px;
            background-color: #f0f0f0;
        }
        #input-box {
            width: 90%;
            height: 150px;
            padding: 15px;
            font-size: 18px;
            border: 2px solid #4CAF50;
            border-radius: 8px;
            resize: none;
        }
        .btn-group {
            width: 90%;
            margin-top: 20px;
            display: flex;
            gap: 10px;
        }
        .func-btn {
            flex: 1;
            padding: 15px;
            font-size: 20px;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        #send-text-btn {
            background-color: #4CAF50;
        }
        #send-enter-btn {
            background-color: #2196F3;
        }
        .func-btn:active {
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <textarea id="input-box" placeholder="请输入内容（支持正则替换，规则在 hot-rule.txt 中配置）..."></textarea>
    <div class="btn-group">
        <button class="func-btn" id="send-text-btn" onclick="sendText()">发送文本</button>
        <button class="func-btn" id="send-enter-btn" onclick="sendEnter()">发送回车</button>
    </div>

    <script>
        function sendText() {
            const text = document.getElementById('input-box').value.trim();
            if (!text) return;
            fetch('/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({text: text})
            }).then(() => {
                document.getElementById('input-box').value = '';
            });
        }

        function sendEnter() {
            fetch('/send_enter', {
                method: 'POST'
            });
        }

        document.getElementById('input-box').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendText();
            }
        });
    </script>
</body>
</html>
'''

# ------------ 接口部分 ------------
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/send', methods=['POST'])
def send_text():
    data = request.get_json()
    text = data.get('text', '').strip()
    if text:
        # 关键步骤：先应用替换规则，再粘贴
        replaced_text = apply_replace_rules(text)
        paste_text(replaced_text)
        print(f"原始文本：{text} → 替换后：{replaced_text}")
    return jsonify({"status": "success"})

@app.route('/send_enter', methods=['POST'])
def send_enter():
    pyautogui.press('enter')
    return jsonify({"status": "success"})

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    finally:
        s.close()
    return local_ip

if __name__ == '__main__':
    local_ip = get_local_ip()
    port = 5000
    print(f"\n服务器已启动！")
    print(f"手机访问地址：http://{local_ip}:{port}")
    print(f"已加载 {len(REPLACE_RULES)} 条替换规则")
    print(f"注意：手机和电脑需在同一局域网下\n")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
