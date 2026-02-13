# -*- mode: python ; coding: utf-8 -*-
# 太白说 PyInstaller 打包配置
# 使用方法: pyinstaller taibai-talk.spec

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 配置文件 - 打包到 exe 同目录
        ('hot-rule.txt', '.'),
        ('commands.txt', '.'),
        ('phrases.txt', '.'),
        ('icon.ico', '.'),
        # HTML 模板文件
        ('templates', 'templates'),
    ],
    hiddenimports=[
        # Flask 相关
        'flask',
        'flask.json',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.debug',
        'jinja2',
        'markupsafe',
        'click',
        'itsdangerous',
        'blinker',
        # 功能依赖
        'pyautogui',
        'pyperclip',
        'qrcode',
        'qrcode.image',
        'qrcode.image.base',
        'qrcode.image.pil',
        'qrcode.image.pure',
        'qrcode.image.styles',
        'qrcode.constants',
        'qrcode_terminal',
        'PIL',
        'PIL.Image',
        # PyAutoGUI 依赖
        'pyscreeze',
        'pytweening',
        'pymsgbox',
        'pygetwindow',
        'pyrect',
        'mouseinfo',
        # 网络相关
        'requests',
        'urllib3',
        'certifi',
        'charset_normalizer',
        # Windows 相关
        'ctypes',
        'win32api',
        'win32con',
        'colorama',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块减小体积（谨慎排除）
        'tkinter',
        'unittest',
        'pydoc',
        'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='太白说',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台显示二维码
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    version='version_info.txt',
)
