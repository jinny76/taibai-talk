// TaiBaiHelper.cpp - Helper process that runs in user session
// Used by TaiBaiService to capture screen and send input from Session 0
#include <windows.h>
#include <objidl.h>
#include <gdiplus.h>
#include <d3d11.h>
#include <dxgi1_2.h>
#include <stdio.h>
#include <string>
#include <vector>

#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")
#pragma comment(lib, "ole32.lib")

using namespace Gdiplus;

static ULONG_PTR g_GdiplusToken = 0;

void InitGdiPlus()
{
    if (g_GdiplusToken == 0)
    {
        GdiplusStartupInput input;
        GdiplusStartup(&g_GdiplusToken, &input, NULL);
    }
}

int GetEncoderClsid(const WCHAR* format, CLSID* pClsid)
{
    UINT num = 0, size = 0;
    GetImageEncodersSize(&num, &size);
    if (size == 0) return -1;

    ImageCodecInfo* pImageCodecInfo = (ImageCodecInfo*)malloc(size);
    if (!pImageCodecInfo) return -1;

    GetImageEncoders(num, size, pImageCodecInfo);

    for (UINT j = 0; j < num; ++j)
    {
        if (wcscmp(pImageCodecInfo[j].MimeType, format) == 0)
        {
            *pClsid = pImageCodecInfo[j].Clsid;
            free(pImageCodecInfo);
            return j;
        }
    }

    free(pImageCodecInfo);
    return -1;
}

// Capture screen using GDI
BOOL CaptureScreenGDI(const WCHAR* outputPath)
{
    InitGdiPlus();

    int screenWidth = GetSystemMetrics(SM_CXSCREEN);
    int screenHeight = GetSystemMetrics(SM_CYSCREEN);

    if (screenWidth == 0 || screenHeight == 0)
    {
        screenWidth = GetSystemMetrics(SM_CXVIRTUALSCREEN);
        screenHeight = GetSystemMetrics(SM_CYVIRTUALSCREEN);
    }

    if (screenWidth == 0 || screenHeight == 0)
    {
        return FALSE;
    }

    HDC hScreenDC = GetDC(NULL);
    if (!hScreenDC) return FALSE;

    HDC hMemDC = CreateCompatibleDC(hScreenDC);
    HBITMAP hBitmap = CreateCompatibleBitmap(hScreenDC, screenWidth, screenHeight);
    HBITMAP hOldBitmap = (HBITMAP)SelectObject(hMemDC, hBitmap);

    BitBlt(hMemDC, 0, 0, screenWidth, screenHeight, hScreenDC, 0, 0, SRCCOPY);

    // Draw cursor
    CURSORINFO ci = { sizeof(ci) };
    if (GetCursorInfo(&ci) && ci.flags == CURSOR_SHOWING)
    {
        ICONINFO ii;
        if (GetIconInfo(ci.hCursor, &ii))
        {
            DrawIcon(hMemDC, ci.ptScreenPos.x - ii.xHotspot, ci.ptScreenPos.y - ii.yHotspot, ci.hCursor);
            if (ii.hbmMask) DeleteObject(ii.hbmMask);
            if (ii.hbmColor) DeleteObject(ii.hbmColor);
        }
    }

    SelectObject(hMemDC, hOldBitmap);

    // Save to JPEG
    BOOL success = FALSE;
    Bitmap* bitmap = Bitmap::FromHBITMAP(hBitmap, NULL);
    if (bitmap)
    {
        CLSID clsidJpeg;
        if (GetEncoderClsid(L"image/jpeg", &clsidJpeg) >= 0)
        {
            EncoderParameters params;
            params.Count = 1;
            params.Parameter[0].Guid = EncoderQuality;
            params.Parameter[0].Type = EncoderParameterValueTypeLong;
            params.Parameter[0].NumberOfValues = 1;
            ULONG quality = 75;
            params.Parameter[0].Value = &quality;

            if (bitmap->Save(outputPath, &clsidJpeg, &params) == Ok)
            {
                success = TRUE;
            }
        }
        delete bitmap;
    }

    DeleteObject(hBitmap);
    DeleteDC(hMemDC);
    ReleaseDC(NULL, hScreenDC);

    return success;
}

// Send unicode text input (one character at a time with delay)
BOOL SendText(const WCHAR* text)
{
    if (!text) return FALSE;

    size_t len = wcslen(text);
    if (len == 0) return FALSE;

    // Send one character at a time with delay
    for (size_t i = 0; i < len; i++)
    {
        INPUT inputs[2] = {0};

        // Key down
        inputs[0].type = INPUT_KEYBOARD;
        inputs[0].ki.wScan = text[i];
        inputs[0].ki.dwFlags = KEYEVENTF_UNICODE;

        // Key up
        inputs[1].type = INPUT_KEYBOARD;
        inputs[1].ki.wScan = text[i];
        inputs[1].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP;

        if (SendInput(2, inputs, sizeof(INPUT)) != 2)
        {
            return FALSE;
        }

        // Delay between characters
        Sleep(50);
    }

    return TRUE;
}

// Send a key press
BOOL SendKey(WORD vkCode, BOOL keyUp)
{
    INPUT input = {0};
    input.type = INPUT_KEYBOARD;
    input.ki.wVk = vkCode;
    input.ki.dwFlags = keyUp ? KEYEVENTF_KEYUP : 0;

    return SendInput(1, &input, sizeof(INPUT)) == 1;
}

// Send Enter key
BOOL SendEnter()
{
    INPUT inputs[2] = {0};
    inputs[0].type = INPUT_KEYBOARD;
    inputs[0].ki.wVk = VK_RETURN;
    inputs[0].ki.dwFlags = 0;

    inputs[1].type = INPUT_KEYBOARD;
    inputs[1].ki.wVk = VK_RETURN;
    inputs[1].ki.dwFlags = KEYEVENTF_KEYUP;

    return SendInput(2, inputs, sizeof(INPUT)) == 2;
}

// Unlock screen: type password and press Enter
BOOL UnlockScreen(const WCHAR* password)
{
    if (!password || wcslen(password) == 0) return FALSE;

    // First, wake up the lock screen by pressing Space or Enter
    // This brings up the password input field
    INPUT wake = {0};
    wake.type = INPUT_KEYBOARD;
    wake.ki.wVk = VK_SPACE;
    SendInput(1, &wake, sizeof(INPUT));
    wake.ki.dwFlags = KEYEVENTF_KEYUP;
    SendInput(1, &wake, sizeof(INPUT));

    // Wait for the password field to appear
    Sleep(500);

    // Clear any existing input: Ctrl+A then Delete
    INPUT inputs[4] = {0};

    // Ctrl down
    inputs[0].type = INPUT_KEYBOARD;
    inputs[0].ki.wVk = VK_CONTROL;

    // A down
    inputs[1].type = INPUT_KEYBOARD;
    inputs[1].ki.wVk = 'A';

    // A up
    inputs[2].type = INPUT_KEYBOARD;
    inputs[2].ki.wVk = 'A';
    inputs[2].ki.dwFlags = KEYEVENTF_KEYUP;

    // Ctrl up
    inputs[3].type = INPUT_KEYBOARD;
    inputs[3].ki.wVk = VK_CONTROL;
    inputs[3].ki.dwFlags = KEYEVENTF_KEYUP;

    SendInput(4, inputs, sizeof(INPUT));
    Sleep(30);

    // Delete selected text
    INPUT del = {0};
    del.type = INPUT_KEYBOARD;
    del.ki.wVk = VK_DELETE;
    SendInput(1, &del, sizeof(INPUT));
    del.ki.dwFlags = KEYEVENTF_KEYUP;
    SendInput(1, &del, sizeof(INPUT));
    Sleep(30);

    // Type password
    if (!SendText(password))
    {
        return FALSE;
    }

    // Small delay before Enter
    Sleep(100);

    // Press Enter
    return SendEnter();
}

// Move mouse
BOOL MoveMouse(int x, int y, BOOL absolute)
{
    INPUT input = {0};
    input.type = INPUT_MOUSE;

    if (absolute)
    {
        int screenWidth = GetSystemMetrics(SM_CXSCREEN);
        int screenHeight = GetSystemMetrics(SM_CYSCREEN);
        input.mi.dx = (x * 65535) / screenWidth;
        input.mi.dy = (y * 65535) / screenHeight;
        input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE;
    }
    else
    {
        input.mi.dx = x;
        input.mi.dy = y;
        input.mi.dwFlags = MOUSEEVENTF_MOVE;
    }

    return SendInput(1, &input, sizeof(INPUT)) == 1;
}

// Click mouse
BOOL ClickMouse(int button, BOOL doubleClick)
{
    INPUT inputs[4] = {0};
    int count = 0;

    DWORD downFlag, upFlag;
    switch (button)
    {
    case 1: downFlag = MOUSEEVENTF_RIGHTDOWN; upFlag = MOUSEEVENTF_RIGHTUP; break;
    case 2: downFlag = MOUSEEVENTF_MIDDLEDOWN; upFlag = MOUSEEVENTF_MIDDLEUP; break;
    default: downFlag = MOUSEEVENTF_LEFTDOWN; upFlag = MOUSEEVENTF_LEFTUP; break;
    }

    inputs[count].type = INPUT_MOUSE;
    inputs[count++].mi.dwFlags = downFlag;
    inputs[count].type = INPUT_MOUSE;
    inputs[count++].mi.dwFlags = upFlag;

    if (doubleClick)
    {
        inputs[count].type = INPUT_MOUSE;
        inputs[count++].mi.dwFlags = downFlag;
        inputs[count].type = INPUT_MOUSE;
        inputs[count++].mi.dwFlags = upFlag;
    }

    return SendInput(count, inputs, sizeof(INPUT)) == (UINT)count;
}

void PrintUsage()
{
    wprintf(L"TaiBaiHelper.exe - Helper for TaiBai Unlock Service\n\n");
    wprintf(L"Usage:\n");
    wprintf(L"  TaiBaiHelper.exe screenshot <output_file>\n");
    wprintf(L"  TaiBaiHelper.exe text <unicode_text>\n");
    wprintf(L"  TaiBaiHelper.exe enter\n");
    wprintf(L"  TaiBaiHelper.exe key <vk_code> [up]\n");
    wprintf(L"  TaiBaiHelper.exe mouse_move <x> <y> [abs]\n");
    wprintf(L"  TaiBaiHelper.exe mouse_click <button> [double]\n");
    wprintf(L"  TaiBaiHelper.exe unlock <password>\n");
}

// Debug log for Helper
static void HelperLog(const char* fmt, ...)
{
    FILE* f = fopen("C:\\TaiBaiHelper.log", "a");
    if (f)
    {
        SYSTEMTIME st;
        GetLocalTime(&st);
        fprintf(f, "[%02d:%02d:%02d] ", st.wHour, st.wMinute, st.wSecond);
        va_list args;
        va_start(args, fmt);
        vfprintf(f, fmt, args);
        va_end(args);
        fprintf(f, "\n");
        fclose(f);
    }
}

// Try to switch to the active input desktop (Winlogon when locked)
HDESK SwitchToInputDesktop()
{
    HelperLog("SwitchToInputDesktop called");

    // First try to open the input desktop directly
    HDESK hDesk = OpenInputDesktop(0, FALSE, DESKTOP_SWITCHDESKTOP | GENERIC_ALL);
    if (hDesk)
    {
        HelperLog("OpenInputDesktop succeeded");
        if (SetThreadDesktop(hDesk))
        {
            HelperLog("SetThreadDesktop(InputDesktop) succeeded");
            return hDesk;
        }
        HelperLog("SetThreadDesktop(InputDesktop) failed, error=%d", GetLastError());
        CloseDesktop(hDesk);
    }
    else
    {
        HelperLog("OpenInputDesktop failed, error=%d", GetLastError());
    }

    // If that fails, try Winlogon desktop explicitly
    hDesk = OpenDesktopW(L"Winlogon", 0, FALSE, DESKTOP_SWITCHDESKTOP | GENERIC_ALL);
    if (hDesk)
    {
        HelperLog("OpenDesktop(Winlogon) succeeded");
        if (SetThreadDesktop(hDesk))
        {
            HelperLog("SetThreadDesktop(Winlogon) succeeded");
            return hDesk;
        }
        HelperLog("SetThreadDesktop(Winlogon) failed, error=%d", GetLastError());
        CloseDesktop(hDesk);
    }
    else
    {
        HelperLog("OpenDesktop(Winlogon) failed, error=%d", GetLastError());
    }

    // Try Default desktop as fallback
    hDesk = OpenDesktopW(L"Default", 0, FALSE, DESKTOP_SWITCHDESKTOP | GENERIC_ALL);
    if (hDesk)
    {
        HelperLog("OpenDesktop(Default) succeeded");
        if (SetThreadDesktop(hDesk))
        {
            HelperLog("SetThreadDesktop(Default) succeeded");
            return hDesk;
        }
        HelperLog("SetThreadDesktop(Default) failed, error=%d", GetLastError());
        CloseDesktop(hDesk);
    }
    else
    {
        HelperLog("OpenDesktop(Default) failed, error=%d", GetLastError());
    }

    HelperLog("All desktop switches failed");
    return NULL;
}

int wmain(int argc, wchar_t* argv[])
{
    if (argc < 2)
    {
        PrintUsage();
        return 1;
    }

    // Switch to the active input desktop (important for lock screen)
    HDESK hDesk = SwitchToInputDesktop();

    const WCHAR* cmd = argv[1];

    if (_wcsicmp(cmd, L"screenshot") == 0)
    {
        if (argc < 3)
        {
            wprintf(L"Error: Missing output file path\n");
            return 1;
        }
        if (CaptureScreenGDI(argv[2]))
        {
            wprintf(L"OK\n");
            return 0;
        }
        wprintf(L"ERROR: Failed to capture screen\n");
        return 1;
    }
    else if (_wcsicmp(cmd, L"text") == 0)
    {
        if (argc < 3)
        {
            wprintf(L"Error: Missing text\n");
            return 1;
        }
        if (SendText(argv[2]))
        {
            wprintf(L"OK\n");
            return 0;
        }
        wprintf(L"ERROR: Failed to send text\n");
        return 1;
    }
    else if (_wcsicmp(cmd, L"enter") == 0)
    {
        if (SendEnter())
        {
            wprintf(L"OK\n");
            return 0;
        }
        wprintf(L"ERROR: Failed to send enter\n");
        return 1;
    }
    else if (_wcsicmp(cmd, L"key") == 0)
    {
        if (argc < 3)
        {
            wprintf(L"Error: Missing key code\n");
            return 1;
        }
        WORD vk = (WORD)_wtoi(argv[2]);
        BOOL keyUp = (argc > 3 && _wcsicmp(argv[3], L"up") == 0);
        if (SendKey(vk, keyUp))
        {
            wprintf(L"OK\n");
            return 0;
        }
        wprintf(L"ERROR: Failed to send key\n");
        return 1;
    }
    else if (_wcsicmp(cmd, L"mouse_move") == 0)
    {
        if (argc < 4)
        {
            wprintf(L"Error: Missing coordinates\n");
            return 1;
        }
        int x = _wtoi(argv[2]);
        int y = _wtoi(argv[3]);
        BOOL absolute = (argc > 4 && _wcsicmp(argv[4], L"abs") == 0);
        if (MoveMouse(x, y, absolute))
        {
            wprintf(L"OK\n");
            return 0;
        }
        wprintf(L"ERROR: Failed to move mouse\n");
        return 1;
    }
    else if (_wcsicmp(cmd, L"mouse_click") == 0)
    {
        int button = 0;
        BOOL doubleClick = FALSE;
        if (argc > 2) button = _wtoi(argv[2]);
        if (argc > 3 && _wcsicmp(argv[3], L"double") == 0) doubleClick = TRUE;
        if (ClickMouse(button, doubleClick))
        {
            wprintf(L"OK\n");
            return 0;
        }
        wprintf(L"ERROR: Failed to click mouse\n");
        return 1;
    }
    else if (_wcsicmp(cmd, L"unlock") == 0)
    {
        if (argc < 3)
        {
            wprintf(L"Error: Missing password\n");
            return 1;
        }
        if (UnlockScreen(argv[2]))
        {
            wprintf(L"OK\n");
            return 0;
        }
        wprintf(L"ERROR: Failed to unlock\n");
        return 1;
    }
    else
    {
        wprintf(L"Unknown command: %s\n", cmd);
        PrintUsage();
        return 1;
    }

    return 0;
}
