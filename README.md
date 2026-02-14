<div align="center">

# 太白说 TaiBai Talk

**Vibe Coding 标准装备** 🛋️

*躺在人体工学椅上，用语音写代码*

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](#english) | [演示](#演示) | [快速开始](#快速使用) | [功能特性](#核心特性)

</div>

---

## 什么是 Vibe Coding？

**Vibe Coding** 是 AI 时代的新型开发方式：

> 🎯 **躺着 + 语音 + AI = 高效编程**

- 👨‍💻 你躺在人体工学椅上，眼睛盯着屏幕
- 🗣️ 用手机语音输入，告诉 AI 你想要什么
- 🤖 AI（如 Claude Code）自动生成代码、执行命令
- 📱 用太白说发送指令、切换标签、查看截屏

**太白说**正是为 Vibe Coding 而生的工具！

---

> 🎯 **手机语音输入，电脑实时上屏** — 让程序员躺着也能高效写代码

你是否曾经：
- 😫 长时间打字手腕酸痛，想躺下休息但还要继续写代码？
- 🤔 羡慕手机语音输入的便捷，却无法在电脑上使用？
- 😤 需要频繁输入重复内容，却找不到好用的替换工具？

**太白说**，你的救星来了！

## 核心特性

| 特性 | 描述 |
|------|------|
| 📱 **语音转文字** | 借助豆包输入法语音识别，说话就能写代码 |
| 🖱️ **全屏触控板** | 手机变身触控板，躺着也能控制电脑鼠标 |
| 📷 **屏幕截图** | 一键截取电脑屏幕，手机查看支持双指缩放 |
| ⌨️ **热键控制** | 支持 Ctrl+C、Escape 等快捷键，长按连续发送 |
| 🚀 **快捷操作** | Tab 切换、继续、回滚、编译、提交等一键操作 |
| 🔧 **正则替换** | 自定义关键词替换规则，`男主` → `张无忌` |
| ⚙️ **设定中心** | 点击 Logo 进入设定，自定义命令和常用语 |
| 🔐 **安全防护** | 密码保护 + 暴力破解防护，局域网内安全使用 |

## 演示

<!-- 建议添加 GIF 演示图 -->
<!-- ![demo](docs/demo.gif) -->

```
手机说话 → 电脑上屏 → 就是这么简单
```

## 快速使用

### 方式一：Windows 免安装版（推荐）

1. 从 [Releases](https://github.com/jinny76/taibai-talk/releases) 下载 `太白说.zip`
2. 解压后双击 `太白说.exe`
3. 手机扫描二维码即可使用

### 方式二：Python 运行

```bash
git clone https://github.com/jinny76/taibai-talk.git
cd taibai-talk
pip install -r requirement.txt
python main.py
```

### 命令行参数

```bash
# 基本启动
python main.py

# 指定端口（默认 57777）
python main.py -p 8888

# 带密码保护
python main.py --password yourpassword

# 指定监听地址（默认 0.0.0.0）
python main.py --host 127.0.0.1

# 外部 URL（用于反向代理/内网穿透）
python main.py --url https://your-domain.com

# 不显示二维码
python main.py --no-qrcode

# 组合使用
python main.py -p 8888 --password mypass --url https://example.com
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-p, --port` | 服务端口号 | 57777 |
| `--host` | 监听地址 | 0.0.0.0 |
| `--password` | 访问密码（不设则无需验证） | 无 |
| `--url` | 外部访问地址（用于反向代理） | 无 |
| `--no-qrcode` | 不在终端显示二维码 | 显示 |

### 自行打包 EXE

```bash
pip install pyinstaller
.\build.ps1       # PowerShell
# 或
build.bat         # CMD
```

## 使用场景

- 🤖 **Vibe Coding** - 躺着用语音指挥 AI 写代码（推荐搭配 Claude Code）
- 💻 **写代码** - 语音输入注释、日志、字符串
- 📝 **写文档** - 躺着口述，电脑记录
- 💬 **回复消息** - 远程输入聊天内容
- 🎮 **远程控制** - 触控板模式控制电脑

## 功能详解

### 文本输入
1. 手机打开网页，切换到豆包输入法
2. 语音或手动输入内容
3. 点击发送，内容出现在电脑光标处

### 全屏触控板
- 🖱️ 滑动 = 移动鼠标
- 👆 单指点击 = 左键
- ✌️ 双指点击 = 右键
- 👆👆 快速双击 = 双击

### 屏幕截图
- 📷 点击截屏按钮，抓取电脑屏幕
- 🔍 双指缩放查看细节（0.5x ~ 5x）
- 🔄 点击刷新按钮重新截取
- 👆👆 双击图片切换 1x/2x 缩放

### 快捷操作栏
顶部快捷按钮，适配 Claude Code 工作流：
- **←Tab / Tab→** - 切换编辑器标签页
- **继续** - 发送"继续"指令
- **ESC** - 发送 Escape 键
- **回滚 / 新任务 / 编译 / 提交** - 常用命令一键发送

### 正则替换规则
编辑 `hot-rule.txt`：
```txt
男主 = 张无忌
女主 = 赵敏
\s+ =                    # 去除空格
(\d{4})年 = $1-          # 日期格式转换
```

## 配置文件

| 文件 | 说明 |
|------|------|
| `hot-rule.txt` | 正则替换规则 |
| `commands.txt` | 快捷命令（支持 `[KEY]` 前缀发送热键） |
| `phrases.txt` | 常用语列表 |

## 技术栈

- **Flask** - 轻量级 Web 服务器
- **pyautogui** - 键盘鼠标模拟
- **pyperclip** - 剪贴板管理
- **qrcode** - 二维码生成

## 环境要求

- Python 3.7+
- 手机和电脑在同一局域网
- 推荐安装豆包输入法（语音识别更准确）

## Star History

如果这个项目对你有帮助，请给个 ⭐️ 支持一下！

## 致谢

本项目最初基于 [ChaserSu/DBInputSync](https://github.com/ChaserSu/DBInputSync) 开发。

## License

[MIT](LICENSE)

---

<div align="center">

**Vibe Coding — 躺着，也能优雅地写代码** 🛋️✨

Made with ❤️ by [jinny76](https://github.com/jinny76)

</div>
