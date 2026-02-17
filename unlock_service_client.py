# unlock_service_client.py - Client for TaiBai Unlock Service
"""
与 TaiBaiService 通信的客户端，用于锁屏状态下的截图和输入控制
"""

import struct
import ctypes
from ctypes import wintypes
import io

PIPE_NAME = r"\\.\pipe\TaiBaiUnlockService"

# Command types
CMD_SCREENSHOT = 1
CMD_KEY_INPUT = 2
CMD_KEY_COMBO = 3
CMD_MOUSE_MOVE = 4
CMD_MOUSE_CLICK = 5
CMD_MOUSE_MOVE_ABS = 6
CMD_TYPE_TEXT = 7
CMD_GET_STATUS = 8
CMD_UNLOCK = 9

# Response codes
RESP_OK = 0
RESP_ERROR = 1

# Windows API
kernel32 = ctypes.windll.kernel32
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
PIPE_READMODE_BYTE = 0
INVALID_HANDLE_VALUE = -1


class UnlockServiceClient:
    """与 TaiBai Unlock Service 通信的客户端"""

    def __init__(self):
        self.pipe = None

    def connect(self):
        """连接到服务"""
        try:
            self.pipe = kernel32.CreateFileW(
                PIPE_NAME,
                GENERIC_READ | GENERIC_WRITE,
                0,
                None,
                OPEN_EXISTING,
                0,
                None
            )
            if self.pipe == INVALID_HANDLE_VALUE:
                self.pipe = None
                return False

            # Set pipe mode
            mode = wintypes.DWORD(PIPE_READMODE_BYTE)
            kernel32.SetNamedPipeHandleState(self.pipe, ctypes.byref(mode), None, None)
            return True
        except Exception as e:
            print(f"[UnlockServiceClient] Connect error: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.pipe:
            kernel32.CloseHandle(self.pipe)
            self.pipe = None

    def _send_command(self, cmd_type, data=b""):
        """发送命令"""
        if not self.pipe:
            if not self.connect():
                return None

        # Command header: cmd_type (4 bytes) + data_size (4 bytes)
        header = struct.pack("<II", cmd_type, len(data))

        written = wintypes.DWORD()
        if not kernel32.WriteFile(self.pipe, header, len(header), ctypes.byref(written), None):
            self.disconnect()
            return None

        if data:
            if not kernel32.WriteFile(self.pipe, data, len(data), ctypes.byref(written), None):
                self.disconnect()
                return None

        return True

    def _read_bytes(self, size):
        """读取指定字节数"""
        if not self.pipe:
            return None

        buffer = ctypes.create_string_buffer(size)
        read = wintypes.DWORD()
        total_read = 0

        while total_read < size:
            remaining = size - total_read
            if not kernel32.ReadFile(
                self.pipe,
                ctypes.byref(buffer, total_read),
                remaining,
                ctypes.byref(read),
                None
            ):
                return None
            if read.value == 0:
                return None
            total_read += read.value

        return buffer.raw

    def get_status(self):
        """获取锁屏状态"""
        try:
            if not self._send_command(CMD_GET_STATUS):
                return None

            # StatusResponse: result (4) + isLocked (4) + sessionId (4)
            data = self._read_bytes(12)
            if not data:
                return None

            result, is_locked, session_id = struct.unpack("<III", data)
            return {
                "result": result,
                "is_locked": bool(is_locked),
                "session_id": session_id
            }
        except Exception as e:
            print(f"[UnlockServiceClient] get_status error: {e}")
            return None

    def screenshot(self):
        """截取屏幕（锁屏状态下也能工作）"""
        try:
            if not self._send_command(CMD_SCREENSHOT):
                return None

            # ScreenshotResponse: result (4) + width (4) + height (4) + dataSize (4)
            header = self._read_bytes(16)
            if not header:
                return None

            result, width, height, data_size = struct.unpack("<IIII", header)
            if result != RESP_OK or data_size == 0:
                return None

            # Read JPEG data
            jpeg_data = self._read_bytes(data_size)
            if not jpeg_data:
                return None

            return {
                "width": width,
                "height": height,
                "data": jpeg_data
            }
        except Exception as e:
            print(f"[UnlockServiceClient] screenshot error: {e}")
            return None

    def type_text(self, text):
        """输入文本"""
        try:
            text_bytes = text.encode('utf-16-le')
            # TypeTextCmd: length (4) + text data
            data = struct.pack("<I", len(text)) + text_bytes

            if not self._send_command(CMD_TYPE_TEXT, data):
                return False

            resp = self._read_bytes(4)
            if not resp:
                return False

            result = struct.unpack("<I", resp)[0]
            return result == RESP_OK
        except Exception as e:
            print(f"[UnlockServiceClient] type_text error: {e}")
            return False

    def key_input(self, vk_code, key_up=False):
        """发送单个按键"""
        try:
            # KeyInputCmd: vkCode (WORD=2) + keyUp (BOOL=4) = 6 bytes
            data = struct.pack("<HI", vk_code, 1 if key_up else 0)

            if not self._send_command(CMD_KEY_INPUT, data):
                return False

            resp = self._read_bytes(4)
            if not resp:
                return False

            result = struct.unpack("<I", resp)[0]
            return result == RESP_OK
        except Exception as e:
            print(f"[UnlockServiceClient] key_input error: {e}")
            return False

    def key_combo(self, *vk_codes):
        """发送组合键"""
        try:
            count = len(vk_codes)
            if count == 0 or count > 8:
                return False

            # KeyComboCmd: keyCount (4) + vkCodes (8 * 2)
            codes = list(vk_codes) + [0] * (8 - count)
            data = struct.pack("<I8H", count, *codes)

            if not self._send_command(CMD_KEY_COMBO, data):
                return False

            resp = self._read_bytes(4)
            if not resp:
                return False

            result = struct.unpack("<I", resp)[0]
            return result == RESP_OK
        except Exception as e:
            print(f"[UnlockServiceClient] key_combo error: {e}")
            return False

    def mouse_move(self, dx, dy):
        """相对移动鼠标"""
        try:
            data = struct.pack("<ii", dx, dy)

            if not self._send_command(CMD_MOUSE_MOVE, data):
                return False

            resp = self._read_bytes(4)
            if not resp:
                return False

            result = struct.unpack("<I", resp)[0]
            return result == RESP_OK
        except Exception as e:
            print(f"[UnlockServiceClient] mouse_move error: {e}")
            return False

    def mouse_move_abs(self, x, y):
        """绝对移动鼠标"""
        try:
            data = struct.pack("<ii", x, y)

            if not self._send_command(CMD_MOUSE_MOVE_ABS, data):
                return False

            resp = self._read_bytes(4)
            if not resp:
                return False

            result = struct.unpack("<I", resp)[0]
            return result == RESP_OK
        except Exception as e:
            print(f"[UnlockServiceClient] mouse_move_abs error: {e}")
            return False

    def mouse_click(self, button=0, double_click=False):
        """
        鼠标点击
        button: 0=左键, 1=右键, 2=中键
        """
        try:
            data = struct.pack("<II", button, 1 if double_click else 0)

            if not self._send_command(CMD_MOUSE_CLICK, data):
                return False

            resp = self._read_bytes(4)
            if not resp:
                return False

            result = struct.unpack("<I", resp)[0]
            return result == RESP_OK
        except Exception as e:
            print(f"[UnlockServiceClient] mouse_click error: {e}")
            return False

    def press_enter(self):
        """按回车键"""
        VK_RETURN = 0x0D
        return self.key_input(VK_RETURN, False) and self.key_input(VK_RETURN, True)

    def press_tab(self):
        """按 Tab 键"""
        VK_TAB = 0x09
        return self.key_input(VK_TAB, False) and self.key_input(VK_TAB, True)

    def press_escape(self):
        """按 ESC 键"""
        VK_ESCAPE = 0x1B
        return self.key_input(VK_ESCAPE, False) and self.key_input(VK_ESCAPE, True)

    def unlock(self, password):
        """解锁屏幕（输入密码并按回车）"""
        try:
            password_bytes = password.encode('utf-16-le')
            # UnlockCmd: length (4) + password data
            data = struct.pack("<I", len(password)) + password_bytes

            if not self._send_command(CMD_UNLOCK, data):
                return False

            resp = self._read_bytes(4)
            if not resp:
                return False

            result = struct.unpack("<I", resp)[0]
            return result == RESP_OK
        except Exception as e:
            print(f"[UnlockServiceClient] unlock error: {e}")
            return False


# Singleton instance
_client = None


def get_client():
    """获取客户端单例"""
    global _client
    if _client is None:
        _client = UnlockServiceClient()
    return _client


def is_service_available():
    """检查服务是否可用"""
    client = get_client()
    status = client.get_status()
    return status is not None


def is_locked():
    """检查是否锁屏"""
    client = get_client()
    status = client.get_status()
    if status:
        return status.get("is_locked", False)
    return False


def get_screenshot():
    """获取截图（锁屏也能用）"""
    client = get_client()
    return client.screenshot()


def type_text(text):
    """输入文本"""
    client = get_client()
    return client.type_text(text)


def click(x, y, button=0, double_click=False):
    """点击指定位置"""
    client = get_client()
    if client.mouse_move_abs(x, y):
        return client.mouse_click(button, double_click)
    return False


def press_enter():
    """按回车"""
    client = get_client()
    return client.press_enter()


def unlock_screen(password):
    """解锁屏幕"""
    client = get_client()
    return client.unlock(password)


# Test
if __name__ == "__main__":
    print("Testing TaiBai Unlock Service Client...")

    client = UnlockServiceClient()

    print("\n1. Getting status...")
    status = client.get_status()
    if status:
        print(f"   Status: {status}")
    else:
        print("   Failed to get status (service may not be running)")

    print("\n2. Taking screenshot...")
    result = client.screenshot()
    if result:
        print(f"   Screenshot: {result['width']}x{result['height']}, {len(result['data'])} bytes")
        # Save to file for testing
        with open("test_screenshot.jpg", "wb") as f:
            f.write(result['data'])
        print("   Saved to test_screenshot.jpg")
    else:
        print("   Failed to take screenshot")

    client.disconnect()
    print("\nDone!")
