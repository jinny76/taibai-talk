// CommandHandler.cpp - Handle pipe commands
#include <windows.h>
#include <algorithm>
#include "TaiBaiService.h"
#include <stdio.h>
#include <wtsapi32.h>

#pragma comment(lib, "wtsapi32.lib")

#ifndef min
#define min(a,b) ((a) < (b) ? (a) : (b))
#endif

// External functions from DesktopCapture.cpp
extern BOOL TypeUnicodeString(HDESK hDesktop, const WCHAR* text, DWORD length);
extern BOOL PressKeyCombo(HDESK hDesktop, WORD* vkCodes, DWORD count);
extern BOOL MoveMouseRelative(HDESK hDesktop, int dx, int dy);
extern BOOL MoveMouseAbsolute(HDESK hDesktop, int x, int y);
extern BOOL ClickMouse(HDESK hDesktop, DWORD button, BOOL doubleClick);

// Debug log
static void DebugLog(const char* fmt, ...)
{
    FILE* f = fopen("C:\\TaiBaiService.log", "a");
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

// Read exactly n bytes from pipe
static BOOL ReadExact(HANDLE hPipe, void* buffer, DWORD size)
{
    BYTE* p = (BYTE*)buffer;
    DWORD remaining = size;

    while (remaining > 0)
    {
        DWORD read = 0;
        if (!ReadFile(hPipe, p, remaining, &read, NULL))
        {
            return FALSE;
        }
        if (read == 0) return FALSE;
        p += read;
        remaining -= read;
    }
    return TRUE;
}

// Write exactly n bytes to pipe
static BOOL WriteExact(HANDLE hPipe, const void* buffer, DWORD size)
{
    const BYTE* p = (const BYTE*)buffer;
    DWORD remaining = size;

    while (remaining > 0)
    {
        DWORD written = 0;
        if (!WriteFile(hPipe, p, remaining, &written, NULL))
        {
            return FALSE;
        }
        p += written;
        remaining -= written;
    }
    return TRUE;
}

// Handle client connection
void HandleClient(HANDLE hPipe)
{
    CommandHeader header;

    while (ReadExact(hPipe, &header, sizeof(header)))
    {
        DebugLog("Received command: type=%d, dataSize=%d", header.cmdType, header.dataSize);

        BOOL locked = IsWorkstationLocked();
        HDESK hDesktop = locked ? OpenSecureDesktop() : NULL;

        switch (header.cmdType)
        {
        case CMD_SCREENSHOT:
        {
            BYTE* pData = NULL;
            DWORD size = 0, width = 0, height = 0;

            CaptureDesktop(hDesktop, &pData, &size, &width, &height);

            ScreenshotResponse resp = {0};
            resp.result = pData ? RESP_OK : RESP_ERROR;
            resp.width = width;
            resp.height = height;
            resp.dataSize = size;

            WriteExact(hPipe, &resp, sizeof(resp));
            if (pData)
            {
                WriteExact(hPipe, pData, size);
                free(pData);
            }
            break;
        }

        case CMD_KEY_INPUT:
        {
            KeyInputCmd cmd;
            if (header.dataSize >= sizeof(cmd) && ReadExact(hPipe, &cmd, sizeof(cmd)))
            {
                BOOL success = SendKeyInput(cmd.vkCode, cmd.keyUp);

                DWORD resp = success ? RESP_OK : RESP_ERROR;
                WriteExact(hPipe, &resp, sizeof(resp));
            }
            break;
        }

        case CMD_KEY_COMBO:
        {
            KeyComboCmd cmd = {0};
            DWORD readSize = min(header.dataSize, sizeof(cmd));
            if (ReadExact(hPipe, &cmd, readSize))
            {
                BOOL success = PressKeyCombo(hDesktop, cmd.vkCodes, cmd.keyCount);

                DWORD resp = success ? RESP_OK : RESP_ERROR;
                WriteExact(hPipe, &resp, sizeof(resp));
            }
            break;
        }

        case CMD_MOUSE_MOVE:
        {
            MouseMoveCmd cmd;
            if (header.dataSize >= sizeof(cmd) && ReadExact(hPipe, &cmd, sizeof(cmd)))
            {
                BOOL success = MoveMouseRelative(hDesktop, cmd.dx, cmd.dy);

                DWORD resp = success ? RESP_OK : RESP_ERROR;
                WriteExact(hPipe, &resp, sizeof(resp));
            }
            break;
        }

        case CMD_MOUSE_MOVE_ABS:
        {
            MouseMoveAbsCmd cmd;
            if (header.dataSize >= sizeof(cmd) && ReadExact(hPipe, &cmd, sizeof(cmd)))
            {
                BOOL success = MoveMouseAbsolute(hDesktop, cmd.x, cmd.y);

                DWORD resp = success ? RESP_OK : RESP_ERROR;
                WriteExact(hPipe, &resp, sizeof(resp));
            }
            break;
        }

        case CMD_MOUSE_CLICK:
        {
            MouseClickCmd cmd;
            if (header.dataSize >= sizeof(cmd) && ReadExact(hPipe, &cmd, sizeof(cmd)))
            {
                BOOL success = ClickMouse(hDesktop, cmd.button, cmd.doubleClick);

                DWORD resp = success ? RESP_OK : RESP_ERROR;
                WriteExact(hPipe, &resp, sizeof(resp));
            }
            break;
        }

        case CMD_TYPE_TEXT:
        {
            TypeTextCmd cmd;
            if (header.dataSize >= sizeof(cmd) && ReadExact(hPipe, &cmd, sizeof(cmd)))
            {
                DWORD textSize = cmd.length * sizeof(WCHAR);
                WCHAR* text = (WCHAR*)malloc(textSize + sizeof(WCHAR));
                if (text && ReadExact(hPipe, text, textSize))
                {
                    text[cmd.length] = L'\0';
                    BOOL success = TypeUnicodeString(hDesktop, text, cmd.length);

                    DWORD resp = success ? RESP_OK : RESP_ERROR;
                    WriteExact(hPipe, &resp, sizeof(resp));
                }
                if (text) free(text);
            }
            break;
        }

        case CMD_GET_STATUS:
        {
            StatusResponse resp = {0};
            resp.result = RESP_OK;
            resp.isLocked = locked;
            resp.sessionId = WTSGetActiveConsoleSessionId();

            WriteExact(hPipe, &resp, sizeof(resp));
            break;
        }

        case CMD_UNLOCK:
        {
            UnlockCmd cmd;
            if (header.dataSize >= sizeof(cmd) && ReadExact(hPipe, &cmd, sizeof(cmd)))
            {
                DWORD textSize = cmd.length * sizeof(WCHAR);
                WCHAR* password = (WCHAR*)malloc(textSize + sizeof(WCHAR));
                if (password && ReadExact(hPipe, password, textSize))
                {
                    password[cmd.length] = L'\0';
                    BOOL success = UnlockScreenWithPassword(password);

                    DWORD resp = success ? RESP_OK : RESP_ERROR;
                    WriteExact(hPipe, &resp, sizeof(resp));
                }
                if (password) free(password);
            }
            break;
        }

        default:
            DebugLog("Unknown command: %d", header.cmdType);
            DWORD resp = RESP_ERROR;
            WriteExact(hPipe, &resp, sizeof(resp));
            break;
        }

        if (hDesktop)
        {
            CloseDesktop(hDesktop);
        }

        FlushFileBuffers(hPipe);
    }
}
