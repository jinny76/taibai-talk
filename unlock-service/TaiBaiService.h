// TaiBaiService.h - TaiBai Unlock Service Header
#pragma once

#include <windows.h>
#include <string>

#define SERVICE_NAME L"TaiBaiUnlockService"
#define SERVICE_DISPLAY_NAME L"TaiBai Unlock Service"
#define SERVICE_DESCRIPTION L"Provides lock screen access for TaiBai Talk"

#define PIPE_NAME L"\\\\.\\pipe\\TaiBaiUnlockService"

// Command types
#define CMD_SCREENSHOT      1
#define CMD_KEY_INPUT       2
#define CMD_KEY_COMBO       3
#define CMD_MOUSE_MOVE      4
#define CMD_MOUSE_CLICK     5
#define CMD_MOUSE_MOVE_ABS  6
#define CMD_TYPE_TEXT       7
#define CMD_GET_STATUS      8
#define CMD_UNLOCK          9

// Response codes
#define RESP_OK             0
#define RESP_ERROR          1
#define RESP_LOCKED         2
#define RESP_UNLOCKED       3

#pragma pack(push, 1)
// Command header
struct CommandHeader {
    DWORD cmdType;
    DWORD dataSize;
};

// Screenshot response
struct ScreenshotResponse {
    DWORD result;
    DWORD width;
    DWORD height;
    DWORD dataSize;  // JPEG data follows
};

// Key input command
struct KeyInputCmd {
    WORD vkCode;
    BOOL keyUp;
};

// Key combo command (e.g., Ctrl+Alt+Del)
struct KeyComboCmd {
    DWORD keyCount;
    WORD vkCodes[8];
};

// Mouse move command (relative)
struct MouseMoveCmd {
    int dx;
    int dy;
};

// Mouse move absolute command
struct MouseMoveAbsCmd {
    int x;
    int y;
};

// Mouse click command
struct MouseClickCmd {
    DWORD button;  // 0=left, 1=right, 2=middle
    BOOL doubleClick;
};

// Type text command
struct TypeTextCmd {
    DWORD length;  // Unicode chars, text follows
};

// Unlock command
struct UnlockCmd {
    DWORD length;  // Password length, password follows
};

// Status response
struct StatusResponse {
    DWORD result;
    BOOL isLocked;
    DWORD sessionId;
};
#pragma pack(pop)

// Service control functions
void WINAPI ServiceMain(DWORD argc, LPWSTR* argv);
void WINAPI ServiceCtrlHandler(DWORD ctrlCode);
DWORD WINAPI ServiceWorkerThread(LPVOID lpParam);

// Desktop functions
HDESK OpenSecureDesktop();
BOOL CaptureDesktop(HDESK hDesktop, BYTE** ppData, DWORD* pSize, DWORD* pWidth, DWORD* pHeight);
BOOL SendInputToDesktop(HDESK hDesktop, INPUT* pInputs, UINT count);
BOOL SendKeyInput(WORD vkCode, BOOL keyUp);
BOOL IsWorkstationLocked();

// Unlock
BOOL UnlockScreenWithPassword(const WCHAR* password);

// Pipe server
DWORD WINAPI PipeServerThread(LPVOID lpParam);
void HandleClient(HANDLE hPipe);
