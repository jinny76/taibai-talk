<div align="center">

# 太白说 TaiBai Talk

**Lounge Coding 标准装备** 🛋️

*躺平，但高效*

https://github.com/user-attachments/assets/5a1a726a-b71f-454a-b8db-d5b7aa57475a

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](#english) | [快速开始](#快速使用) | [使用场景](#使用场景) | [功能特性](#核心特性)

</div>

---

## 从 Vibe Coding 到 Lounge Coding

**Vibe Coding** = 和 AI 聊天写代码（打字）

但 Vibe Coding 有两个痛点：
- 😫 还是要打字，手腕照样酸
- 🏠 只能在电脑前，出门就断了

**Lounge Coding** = 躺平式 AI 编程（语音 + 随时随地）

| 对比 | Vibe Coding | Lounge Coding |
|------|-------------|---------------|
| 输入方式 | 打字 | 语音 |
| 姿势 | 坐着 | 躺平 |
| 场所 | 电脑前 | 随时随地 |

**太白说** = Lounge Coding 标准装备 = 程序员躺平神器

---

## 核心特性

| 特性 | 描述 |
|------|------|
| 📱 **语音转文字** | 借助手机输入法语音识别，说话即上屏 |
| 🖱️ **全屏触控板** | 手机变身触控板，躺着控制鼠标 |
| 🖥️ **远程模式** | 手机查看电脑屏幕，在外也能干活 |
| ⌨️ **热键控制** | Ctrl+C、Escape 等快捷键，长按连续发送 |
| 🚀 **快捷操作** | Tab 切换、继续、回滚、编译、提交一键搞定 |
| 🔧 **正则替换** | 自定义关键词替换规则 |
| ⚙️ **设定中心** | 自定义命令和常用语 |
| ⚡ **即开即用** | 不用装 App，浏览器打开就用，1 秒进入工作状态 |

---

## 使用场景

### 场景 A：日常开发

```
09:00  躺在椅子上，语音说"我要实现一个用户营销功能"
09:05  AI 问需求细节，语音讨论，敲定方案
09:30  语音说"开始实现"，AI 写代码，你躺着看
10:00  语音说"跑一下测试"，看结果，有 bug
10:05  语音说"第三个测试失败了，帮我修一下"
10:20  测试全过，语音说"提交"
18:00  下班回家 🎉
```

**全程躺平，全程高效。**

### 场景 B：紧急救火

```
19:30  地铁上，挤得要死
19:35  老板打电话："线上挂了！紧急修复！"
19:36  掏出手机，打开太白说，进入远程模式
19:40  语音说"把这个判断条件改一下"，AI 修复
19:45  语音说"部署到生产"
19:50  老板："好了，辛苦了"
19:51  收起手机，开心到家 🏠
```

**没背电脑，照样救火。**

### 更多场景

- 🏨 **出差酒店** - 没带电脑，远程连上公司电脑，语音操作
- 🩹 **身体抗议** - 手腕疼，语音代替打字，手腕得救
- 👶 **带娃遛狗** - 娃在旁边玩，语音改代码，娃没丢，代码写完了

---

## 快速使用

### 方式一：Windows 免安装版（推荐）

1. 从 [Releases](https://github.com/jinny76/taibai-talk/releases) 下载 `太白说.zip`
2. 解压后双击 `太白说.exe`
3. 手机扫描二维码
4. 开始 Lounge Coding！

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

# 公网部署（配合反向代理）
python main.py --url https://your-domain.com

# 组合使用
python main.py -p 8888 --password mypass --url https://example.com
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-p, --port` | 服务端口号 | 57777 |
| `--host` | 监听地址 | 0.0.0.0 |
| `--password` | 访问密码 | 无 |
| `--url` | 外部访问地址 | 无 |
| `--no-qrcode` | 不显示二维码 | 显示 |

---

## 功能详解

### 语音输入
1. 手机打开网页，切换到豆包输入法
2. 语音输入内容
3. 点击发送，内容出现在电脑光标处

### 全屏触控板
- 🖱️ 滑动 = 移动鼠标
- 👆 单指点击 = 左键
- ✌️ 双指点击 = 右键
- 👆👆 快速双击 = 双击

### 远程模式

点击 🖥️ 按钮进入远程模式：

**屏幕预览**
- 电脑屏幕实时显示在手机上
- 红色十字标记鼠标位置
- 每 2 秒自动刷新

**触控操作**
- 点击 🖱️ 开启触控板
- 在截图上滑动控制鼠标
- 操作后自动刷新

**快捷面板**
- 点击 ⚡ 展开快捷操作
- 🏠 返回主界面

### 快捷操作栏

适配 Claude Code 工作流：
- **←Tab / Tab→** - 切换编辑器标签页
- **继续** - 发送"继续"指令
- **ESC** - 发送 Escape 键
- **回滚 / 新任务 / 编译 / 提交** - 常用命令

### 正则替换

编辑 `hot-rule.txt`：
```txt
男主 = 张无忌
女主 = 赵敏
\s+ =                    # 去除空格
```

---

## 配置文件

| 文件 | 说明 |
|------|------|
| `hot-rule.txt` | 正则替换规则 |
| `commands.txt` | 快捷命令 |
| `phrases.txt` | 常用语列表 |

---

## 技术栈

- **Flask** - Web 服务器
- **pyautogui** - 键盘鼠标模拟
- **pyperclip** - 剪贴板管理
- **qrcode** - 二维码生成

## 环境要求

- Python 3.7+
- 手机和电脑在同一网络（或公网部署）
- 推荐豆包输入法（语音识别更准确）

---

## 自行打包

```bash
pip install pyinstaller
.\build.ps1       # PowerShell
# 或
build.bat         # CMD
```

---

## Star History

如果这个项目对你有帮助，请给个 ⭐️ 支持一下！

## 致谢

本项目最初基于 [ChaserSu/DBInputSync](https://github.com/ChaserSu/DBInputSync) 开发。

## License

[MIT](LICENSE)

---

<div align="center">

**Lounge Coding — 躺平，但高效** 🛋️

Made with ❤️ by [jinny76](https://github.com/jinny76)

</div>
