<div align="center">

# 太白说 TaiBai Talk

**程序员の躺平神器** 🛋️

*躺在人体工学椅上写代码*

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](#english) | [演示](#演示) | [快速开始](#快速使用) | [功能特性](#核心特性)

</div>

---

> 🎯 **手机语音输入，电脑实时上屏** — 让疲惫的程序员躺着也能敲代码

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
| ⌨️ **热键控制** | 支持 Ctrl+C、Escape 等快捷键，长按连续发送 |
| 🔧 **正则替换** | 自定义关键词替换规则，`男主` → `张无忌` |
| 🚀 **自动发送** | 停止说话后自动发送，真正解放双手 |
| 🔐 **安全防护** | 密码保护 + 暴力破解防护，局域网内安全使用 |

## 演示

<!-- 建议添加 GIF 演示图 -->
<!-- ![demo](docs/demo.gif) -->

```
手机说话 → 电脑上屏 → 就是这么简单
```

## 快速使用

### 1. 安装依赖
```bash
git clone https://github.com/jinny76/taibai-talk.git
cd taibai-talk
pip install -r requirement.txt
```

### 2. 启动服务
```bash
python main.py
```

### 3. 手机扫码访问
启动后会显示二维码，手机扫码即可使用。

### 带密码启动
```bash
python main.py --password yourpassword
```

## 使用场景

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

**躺着，也能优雅地写代码** 🛋️✨

Made with ❤️ by [jinny76](https://github.com/jinny76)

</div>
