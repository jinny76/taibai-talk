// DesktopCapture.cpp - Desktop capture and input via Helper process
#include <windows.h>
#include <objidl.h>
#include <gdiplus.h>
#include <vector>
#include <stdio.h>
#include <stdarg.h>
#include <wtsapi32.h>
#include <userenv.h>
#include <tlhelp32.h>
#include "TaiBaiService.h"

#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "wtsapi32.lib")
#pragma comment(lib, "userenv.lib")

using namespace Gdiplus;

// Path to helper executable
static WCHAR g_HelperPath[MAX_PATH] = {0};

// Debug log
static void DebugLog(const char* fmt, ...)
{
    FILE* f = fopen("C:\\TaiBaiService.log", "a");
    if (f)
    {
        SYSTEMTIME st;
        GetLocalTime(&st);
        fprintf(f, "[%02d:%02d:%02d] [Capture] ", st.wHour, st.wMinute, st.wSecond);

        va_list args;
        va_start(args, fmt);
        vfprintf(f, fmt, args);
        va_end(args);

        fprintf(f, "\n");
        fclose(f);
    }
}

// Initialize helper path
void InitHelperPath()
{
    if (g_HelperPath[0] == 0)
    {
        // Get service executable directory
        GetModuleFileNameW(NULL, g_HelperPath, MAX_PATH);
        WCHAR* lastSlash = wcsrchr(g_HelperPath, L'\\');
        if (lastSlash) *(lastSlash + 1) = 0;
        wcscat_s(g_HelperPath, MAX_PATH, L"TaiBaiHelper.exe");
        DebugLog("Helper path: %ls", g_HelperPath);
    }
}

// GDI+ helpers
static ULONG_PTR g_GdiplusToken = 0;

void InitGdiPlus()
{
    if (g_GdiplusToken == 0)
    {
        GdiplusStartupInput input;
        GdiplusStartup(&g_GdiplusToken, &input, NULL);
    }
}

void ShutdownGdiPlus()
{
    if (g_GdiplusToken)
    {
        GdiplusShutdown(g_GdiplusToken);
        g_GdiplusToken = 0;
    }
}

// Find process by name and get its token
static HANDLE GetProcessToken(const WCHAR* processName, DWORD sessionId)
{
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnapshot == INVALID_HANDLE_VALUE) return NULL;

    PROCESSENTRY32W pe = { sizeof(pe) };
    HANDLE hToken = NULL;

    if (Process32FirstW(hSnapshot, &pe))
    {
        do
        {
            if (_wcsicmp(pe.szExeFile, processName) == 0)
            {
                HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, pe.th32ProcessID);
                if (hProcess)
                {
                    DWORD procSessionId = 0;
                    if (ProcessIdToSessionId(pe.th32ProcessID, &procSessionId) && procSessionId == sessionId)
                    {
                        if (OpenProcessToken(hProcess, TOKEN_DUPLICATE | TOKEN_QUERY, &hToken))
                        {
                            CloseHandle(hProcess);
                            DebugLog("Found %ls in session %d (pid=%d)", processName, sessionId, pe.th32ProcessID);
                            break;
                        }
                    }
                    CloseHandle(hProcess);
                }
            }
        } while (Process32NextW(hSnapshot, &pe));
    }

    CloseHandle(hSnapshot);
    return hToken;
}

// Get session token for CreateProcessAsUser
// forWinlogon: if TRUE, prefer winlogon.exe token (for locked screen input)
static HANDLE GetSessionToken(BOOL forWinlogon)
{
    DWORD sessionId = WTSGetActiveConsoleSessionId();
    if (sessionId == 0xFFFFFFFF)
    {
        DebugLog("No active console session");
        return NULL;
    }

    HANDLE hToken = NULL;

    if (forWinlogon)
    {
        // For Winlogon desktop, use winlogon.exe token
        DebugLog("Getting winlogon.exe token for session %d", sessionId);
        hToken = GetProcessToken(L"winlogon.exe", sessionId);
        if (!hToken)
        {
            DebugLog("winlogon.exe token failed, trying user token...");
            WTSQueryUserToken(sessionId, &hToken);
        }
    }
    else
    {
        // For normal desktop, prefer user token
        if (WTSQueryUserToken(sessionId, &hToken))
        {
            DebugLog("Got token via WTSQueryUserToken for session %d", sessionId);
        }
        else
        {
            DWORD err = GetLastError();
            DebugLog("WTSQueryUserToken failed, error=%d, trying process token...", err);
            hToken = GetProcessToken(L"explorer.exe", sessionId);
            if (!hToken)
            {
                hToken = GetProcessToken(L"dwm.exe", sessionId);
            }
        }
    }

    if (!hToken)
    {
        DebugLog("Failed to get any token");
        return NULL;
    }

    // Duplicate token for CreateProcessAsUser
    HANDLE hDupToken = NULL;
    if (!DuplicateTokenEx(hToken, MAXIMUM_ALLOWED, NULL,
        SecurityImpersonation, TokenPrimary, &hDupToken))
    {
        DebugLog("DuplicateTokenEx failed, error=%d", GetLastError());
        CloseHandle(hToken);
        return NULL;
    }

    CloseHandle(hToken);

    // Set session ID on the token
    if (!SetTokenInformation(hDupToken, TokenSessionId, &sessionId, sizeof(sessionId)))
    {
        DebugLog("SetTokenInformation failed, error=%d", GetLastError());
        CloseHandle(hDupToken);
        return NULL;
    }

    DebugLog("Got token for session %d (forWinlogon=%d)", sessionId, forWinlogon);
    return hDupToken;
}

// Compatibility wrapper
static HANDLE GetUserSessionToken()
{
    return GetSessionToken(FALSE);
}

// Try running helper on a specific desktop
static BOOL TryRunHelperOnDesktop(HANDLE hToken, LPVOID pEnv, const WCHAR* cmdLine,
                                   const WCHAR* desktop, DWORD timeoutMs)
{
    STARTUPINFOW si = { sizeof(si) };
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.lpDesktop = (LPWSTR)desktop;
    PROCESS_INFORMATION pi = {0};

    DebugLog("Trying desktop: %ls", desktop);

    BOOL result = CreateProcessAsUserW(
        hToken, NULL, (LPWSTR)cmdLine, NULL, NULL, FALSE,
        CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
        pEnv, NULL, &si, &pi
    );

    if (!result)
    {
        DebugLog("CreateProcessAsUser failed on %ls, error=%d", desktop, GetLastError());
        return FALSE;
    }

    DWORD waitResult = WaitForSingleObject(pi.hProcess, timeoutMs);
    DWORD exitCode = 1;

    if (waitResult == WAIT_TIMEOUT)
    {
        DebugLog("Helper timed out on %ls", desktop);
        TerminateProcess(pi.hProcess, 1);
    }
    else
    {
        GetExitCodeProcess(pi.hProcess, &exitCode);
        DebugLog("Helper on %ls exit code=%d", desktop, exitCode);
    }

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return (exitCode == 0);
}

// Run helper process in user session
static BOOL RunHelperInUserSession(const WCHAR* args, DWORD timeoutMs = 10000)
{
    InitHelperPath();

    // Check if workstation is locked
    BOOL locked = IsWorkstationLocked();
    DebugLog("Workstation locked=%d", locked);

    // Build command line
    WCHAR cmdLine[4096];
    wsprintfW(cmdLine, L"\"%s\" %s", g_HelperPath, args);
    DebugLog("Running helper: %ls", cmdLine);

    BOOL result = FALSE;

    if (locked)
    {
        // Locked: use winlogon.exe token for Winlogon desktop
        HANDLE hToken = GetSessionToken(TRUE);  // forWinlogon = TRUE
        if (hToken)
        {
            LPVOID pEnv = NULL;
            CreateEnvironmentBlock(&pEnv, hToken, FALSE);

            result = TryRunHelperOnDesktop(hToken, pEnv, cmdLine, L"WinSta0\\Winlogon", timeoutMs);

            if (!result)
            {
                DebugLog("Winlogon desktop failed, trying Default...");
                result = TryRunHelperOnDesktop(hToken, pEnv, cmdLine, L"WinSta0\\Default", timeoutMs);
            }

            if (pEnv) DestroyEnvironmentBlock(pEnv);
            CloseHandle(hToken);
        }
    }
    else
    {
        // Unlocked: use user token for Default desktop
        HANDLE hToken = GetSessionToken(FALSE);  // forWinlogon = FALSE
        if (hToken)
        {
            LPVOID pEnv = NULL;
            CreateEnvironmentBlock(&pEnv, hToken, FALSE);

            result = TryRunHelperOnDesktop(hToken, pEnv, cmdLine, L"WinSta0\\Default", timeoutMs);

            if (pEnv) DestroyEnvironmentBlock(pEnv);
            CloseHandle(hToken);
        }
    }

    return result;
}

// Read file contents
static BYTE* ReadFileContents(const WCHAR* path, DWORD* pSize)
{
    HANDLE hFile = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL,
        OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile == INVALID_HANDLE_VALUE)
    {
        return NULL;
    }

    DWORD size = GetFileSize(hFile, NULL);
    if (size == 0 || size == INVALID_FILE_SIZE)
    {
        CloseHandle(hFile);
        return NULL;
    }

    BYTE* data = (BYTE*)malloc(size);
    if (!data)
    {
        CloseHandle(hFile);
        return NULL;
    }

    DWORD read = 0;
    if (!ReadFile(hFile, data, size, &read, NULL) || read != size)
    {
        free(data);
        CloseHandle(hFile);
        return NULL;
    }

    CloseHandle(hFile);
    *pSize = size;
    return data;
}

// Get JPEG image dimensions
static BOOL GetJpegDimensions(const BYTE* data, DWORD size, DWORD* pWidth, DWORD* pHeight)
{
    *pWidth = 0;
    *pHeight = 0;

    InitGdiPlus();

    // Create stream from memory
    IStream* pStream = NULL;
    HGLOBAL hMem = GlobalAlloc(GMEM_MOVEABLE, size);
    if (!hMem) return FALSE;

    void* pMem = GlobalLock(hMem);
    memcpy(pMem, data, size);
    GlobalUnlock(hMem);

    if (FAILED(CreateStreamOnHGlobal(hMem, TRUE, &pStream)))
    {
        GlobalFree(hMem);
        return FALSE;
    }

    Bitmap* bitmap = Bitmap::FromStream(pStream);
    if (bitmap && bitmap->GetLastStatus() == Ok)
    {
        *pWidth = bitmap->GetWidth();
        *pHeight = bitmap->GetHeight();
        delete bitmap;
        pStream->Release();
        return TRUE;
    }

    if (bitmap) delete bitmap;
    pStream->Release();
    return FALSE;
}

// Capture desktop using Helper process
BOOL CaptureDesktop(HDESK hDesktop, BYTE** ppData, DWORD* pSize, DWORD* pWidth, DWORD* pHeight)
{
    (void)hDesktop;  // Not used, helper captures from user session

    *ppData = NULL;
    *pSize = 0;
    *pWidth = 0;
    *pHeight = 0;

    // Generate temp file path
    WCHAR tempPath[MAX_PATH];
    WCHAR tempFile[MAX_PATH];
    GetTempPathW(MAX_PATH, tempPath);
    wsprintfW(tempFile, L"%sTaiBaiScreen_%d.jpg", tempPath, GetTickCount());

    DebugLog("Capturing screen to: %ls", tempFile);

    // Run helper to capture screenshot
    WCHAR args[MAX_PATH * 2];
    wsprintfW(args, L"screenshot \"%s\"", tempFile);

    if (!RunHelperInUserSession(args))
    {
        DebugLog("Failed to run helper for screenshot");
        DeleteFileW(tempFile);
        return FALSE;
    }

    // Read the screenshot file
    DWORD size = 0;
    BYTE* data = ReadFileContents(tempFile, &size);
    DeleteFileW(tempFile);

    if (!data)
    {
        DebugLog("Failed to read screenshot file");
        return FALSE;
    }

    // Get dimensions
    DWORD width = 0, height = 0;
    GetJpegDimensions(data, size, &width, &height);

    *ppData = data;
    *pSize = size;
    *pWidth = width;
    *pHeight = height;

    DebugLog("Screenshot captured: %dx%d, %d bytes", width, height, size);
    return TRUE;
}

// Send input to desktop (not used directly, kept for compatibility)
BOOL SendInputToDesktop(HDESK hDesktop, INPUT* pInputs, UINT count)
{
    (void)hDesktop;
    (void)pInputs;
    (void)count;

    // This function is not used when using Helper
    DebugLog("SendInputToDesktop called (not implemented with Helper)");
    return FALSE;
}

// Send a single key using Helper
BOOL SendKeyInput(WORD vkCode, BOOL keyUp)
{
    WCHAR args[256];
    if (keyUp)
    {
        wsprintfW(args, L"key %d up", vkCode);
    }
    else
    {
        wsprintfW(args, L"key %d", vkCode);
    }

    DebugLog("SendKeyInput: vk=%d, up=%d", vkCode, keyUp);
    return RunHelperInUserSession(args);
}

// Type a unicode string using Helper
BOOL TypeUnicodeString(HDESK hDesktop, const WCHAR* text, DWORD length)
{
    (void)hDesktop;

    if (!text || length == 0) return FALSE;

    // Build command line - text should be null-terminated
    WCHAR args[8192];
    wsprintfW(args, L"text \"%s\"", text);

    DebugLog("TypeUnicodeString: length=%d, text=%ls", length, text);

    if (!RunHelperInUserSession(args))
    {
        DebugLog("Failed to run helper for text input");
        return FALSE;
    }

    DebugLog("Text input sent successfully");
    return TRUE;
}

// Press a key combination using Helper
BOOL PressKeyCombo(HDESK hDesktop, WORD* vkCodes, DWORD count)
{
    (void)hDesktop;

    if (!vkCodes || count == 0) return FALSE;

    // For each key, send press then release
    for (DWORD i = 0; i < count; i++)
    {
        WCHAR args[256];
        wsprintfW(args, L"key %d", vkCodes[i]);
        if (!RunHelperInUserSession(args))
        {
            return FALSE;
        }
    }

    // Release in reverse order
    for (DWORD i = count; i > 0; i--)
    {
        WCHAR args[256];
        wsprintfW(args, L"key %d up", vkCodes[i - 1]);
        if (!RunHelperInUserSession(args))
        {
            return FALSE;
        }
    }

    DebugLog("Key combo sent: %d keys", count);
    return TRUE;
}

// Move mouse relative
BOOL MoveMouseRelative(HDESK hDesktop, int dx, int dy)
{
    (void)hDesktop;

    WCHAR args[256];
    wsprintfW(args, L"mouse_move %d %d", dx, dy);

    return RunHelperInUserSession(args);
}

// Move mouse absolute
BOOL MoveMouseAbsolute(HDESK hDesktop, int x, int y)
{
    (void)hDesktop;

    WCHAR args[256];
    wsprintfW(args, L"mouse_move %d %d abs", x, y);

    return RunHelperInUserSession(args);
}

// Click mouse
BOOL ClickMouse(HDESK hDesktop, DWORD button, BOOL doubleClick)
{
    (void)hDesktop;

    WCHAR args[256];
    if (doubleClick)
    {
        wsprintfW(args, L"mouse_click %d double", button);
    }
    else
    {
        wsprintfW(args, L"mouse_click %d", button);
    }

    return RunHelperInUserSession(args);
}

// Unlock screen with password
BOOL UnlockScreenWithPassword(const WCHAR* password)
{
    if (!password || wcslen(password) == 0) return FALSE;

    WCHAR args[1024];
    wsprintfW(args, L"unlock \"%s\"", password);

    DebugLog("Attempting unlock...");
    return RunHelperInUserSession(args, 5000);
}
