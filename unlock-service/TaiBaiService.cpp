// TaiBaiService.cpp - TaiBai Unlock Service Main
#include "TaiBaiService.h"
#include <stdio.h>
#include <wtsapi32.h>
#include <userenv.h>
#include <sddl.h>

#pragma comment(lib, "wtsapi32.lib")
#pragma comment(lib, "userenv.lib")
#pragma comment(lib, "advapi32.lib")

// Global variables
SERVICE_STATUS g_ServiceStatus = {0};
SERVICE_STATUS_HANDLE g_StatusHandle = NULL;
HANDLE g_ServiceStopEvent = NULL;
HANDLE g_PipeThread = NULL;
volatile BOOL g_Running = FALSE;

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

// Check if workstation is locked
BOOL IsWorkstationLocked()
{
    HDESK hDesktop = OpenDesktopW(L"Default", 0, FALSE, DESKTOP_SWITCHDESKTOP);
    if (hDesktop)
    {
        BOOL bLocked = !SwitchDesktop(hDesktop);
        CloseDesktop(hDesktop);
        return bLocked;
    }
    return TRUE;  // Assume locked if can't open
}

// Open the secure desktop (Winlogon)
HDESK OpenSecureDesktop()
{
    // Try to open the Winlogon desktop
    HDESK hDesk = OpenDesktopW(L"Winlogon", 0, FALSE,
        DESKTOP_READOBJECTS | DESKTOP_WRITEOBJECTS |
        DESKTOP_ENUMERATE | DESKTOP_CREATEWINDOW);

    if (!hDesk)
    {
        DebugLog("Failed to open Winlogon desktop, error=%d", GetLastError());

        // Try Default desktop as fallback
        hDesk = OpenDesktopW(L"Default", 0, FALSE,
            DESKTOP_READOBJECTS | DESKTOP_WRITEOBJECTS |
            DESKTOP_ENUMERATE | DESKTOP_CREATEWINDOW);
    }

    return hDesk;
}

// Get active console session ID
DWORD GetActiveConsoleSessionId()
{
    return WTSGetActiveConsoleSessionId();
}

// Service main entry point
void WINAPI ServiceMain(DWORD argc, LPWSTR* argv)
{
    UNREFERENCED_PARAMETER(argc);
    UNREFERENCED_PARAMETER(argv);

    DebugLog("ServiceMain started");

    // Register service control handler
    g_StatusHandle = RegisterServiceCtrlHandlerW(SERVICE_NAME, ServiceCtrlHandler);
    if (!g_StatusHandle)
    {
        DebugLog("RegisterServiceCtrlHandler failed, error=%d", GetLastError());
        return;
    }

    // Initialize service status
    g_ServiceStatus.dwServiceType = SERVICE_WIN32_OWN_PROCESS;
    g_ServiceStatus.dwControlsAccepted = SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN;
    g_ServiceStatus.dwCurrentState = SERVICE_START_PENDING;
    g_ServiceStatus.dwWin32ExitCode = 0;
    g_ServiceStatus.dwServiceSpecificExitCode = 0;
    g_ServiceStatus.dwCheckPoint = 0;
    g_ServiceStatus.dwWaitHint = 3000;

    SetServiceStatus(g_StatusHandle, &g_ServiceStatus);

    // Create stop event
    g_ServiceStopEvent = CreateEventW(NULL, TRUE, FALSE, NULL);
    if (!g_ServiceStopEvent)
    {
        g_ServiceStatus.dwCurrentState = SERVICE_STOPPED;
        g_ServiceStatus.dwWin32ExitCode = GetLastError();
        SetServiceStatus(g_StatusHandle, &g_ServiceStatus);
        return;
    }

    // Start pipe server thread
    g_Running = TRUE;
    g_PipeThread = CreateThread(NULL, 0, PipeServerThread, NULL, 0, NULL);

    // Report running
    g_ServiceStatus.dwCurrentState = SERVICE_RUNNING;
    g_ServiceStatus.dwCheckPoint = 0;
    g_ServiceStatus.dwWaitHint = 0;
    SetServiceStatus(g_StatusHandle, &g_ServiceStatus);

    DebugLog("Service running, waiting for stop event");

    // Wait for stop signal
    WaitForSingleObject(g_ServiceStopEvent, INFINITE);

    // Cleanup
    g_Running = FALSE;
    if (g_PipeThread)
    {
        WaitForSingleObject(g_PipeThread, 5000);
        CloseHandle(g_PipeThread);
    }
    CloseHandle(g_ServiceStopEvent);

    // Report stopped
    g_ServiceStatus.dwCurrentState = SERVICE_STOPPED;
    SetServiceStatus(g_StatusHandle, &g_ServiceStatus);

    DebugLog("Service stopped");
}

// Service control handler
void WINAPI ServiceCtrlHandler(DWORD ctrlCode)
{
    switch (ctrlCode)
    {
    case SERVICE_CONTROL_STOP:
    case SERVICE_CONTROL_SHUTDOWN:
        DebugLog("Stop/Shutdown control received");
        g_ServiceStatus.dwCurrentState = SERVICE_STOP_PENDING;
        g_ServiceStatus.dwWaitHint = 5000;
        SetServiceStatus(g_StatusHandle, &g_ServiceStatus);
        SetEvent(g_ServiceStopEvent);
        break;

    case SERVICE_CONTROL_INTERROGATE:
        SetServiceStatus(g_StatusHandle, &g_ServiceStatus);
        break;
    }
}

// Pipe server thread
DWORD WINAPI PipeServerThread(LPVOID lpParam)
{
    UNREFERENCED_PARAMETER(lpParam);

    DebugLog("Pipe server thread started");

    // Create security descriptor allowing all users
    SECURITY_ATTRIBUTES sa;
    SECURITY_DESCRIPTOR sd;
    InitializeSecurityDescriptor(&sd, SECURITY_DESCRIPTOR_REVISION);
    SetSecurityDescriptorDacl(&sd, TRUE, NULL, FALSE);
    sa.nLength = sizeof(sa);
    sa.lpSecurityDescriptor = &sd;
    sa.bInheritHandle = FALSE;

    while (g_Running)
    {
        DebugLog("Creating named pipe...");

        HANDLE hPipe = CreateNamedPipeW(
            PIPE_NAME,
            PIPE_ACCESS_DUPLEX,
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
            PIPE_UNLIMITED_INSTANCES,
            65536,
            65536,
            5000,
            &sa);

        if (hPipe == INVALID_HANDLE_VALUE)
        {
            DebugLog("CreateNamedPipe failed, error=%d", GetLastError());
            Sleep(1000);
            continue;
        }

        DebugLog("Waiting for client...");

        // Wait for client connection with overlapped I/O for cancellation
        OVERLAPPED ovl = {0};
        ovl.hEvent = CreateEventW(NULL, TRUE, FALSE, NULL);

        BOOL connected = ConnectNamedPipe(hPipe, &ovl);
        if (!connected)
        {
            DWORD err = GetLastError();
            if (err == ERROR_IO_PENDING)
            {
                HANDLE handles[2] = { ovl.hEvent, g_ServiceStopEvent };
                DWORD wait = WaitForMultipleObjects(2, handles, FALSE, INFINITE);

                if (wait == WAIT_OBJECT_0 + 1)
                {
                    // Stop requested
                    CancelIo(hPipe);
                    CloseHandle(ovl.hEvent);
                    CloseHandle(hPipe);
                    break;
                }
                connected = TRUE;
            }
            else if (err == ERROR_PIPE_CONNECTED)
            {
                connected = TRUE;
            }
        }

        CloseHandle(ovl.hEvent);

        if (connected)
        {
            DebugLog("Client connected");
            HandleClient(hPipe);
            DebugLog("Client disconnected");
        }

        DisconnectNamedPipe(hPipe);
        CloseHandle(hPipe);
    }

    DebugLog("Pipe server thread exiting");
    return 0;
}

// Main entry point
int wmain(int argc, wchar_t* argv[])
{
    // Check for command line arguments
    if (argc > 1)
    {
        if (_wcsicmp(argv[1], L"/install") == 0 || _wcsicmp(argv[1], L"-install") == 0)
        {
            // Install service
            SC_HANDLE hSCM = OpenSCManagerW(NULL, NULL, SC_MANAGER_CREATE_SERVICE);
            if (!hSCM)
            {
                wprintf(L"OpenSCManager failed, error=%d\n", GetLastError());
                return 1;
            }

            WCHAR szPath[MAX_PATH];
            GetModuleFileNameW(NULL, szPath, MAX_PATH);

            SC_HANDLE hService = CreateServiceW(
                hSCM,
                SERVICE_NAME,
                SERVICE_DISPLAY_NAME,
                SERVICE_ALL_ACCESS,
                SERVICE_WIN32_OWN_PROCESS,
                SERVICE_AUTO_START,
                SERVICE_ERROR_NORMAL,
                szPath,
                NULL, NULL, NULL, NULL, NULL);

            if (!hService)
            {
                DWORD err = GetLastError();
                if (err == ERROR_SERVICE_EXISTS)
                {
                    wprintf(L"Service already exists\n");
                }
                else
                {
                    wprintf(L"CreateService failed, error=%d\n", err);
                    CloseServiceHandle(hSCM);
                    return 1;
                }
            }
            else
            {
                // Set description
                SERVICE_DESCRIPTIONW desc;
                desc.lpDescription = (LPWSTR)SERVICE_DESCRIPTION;
                ChangeServiceConfig2W(hService, SERVICE_CONFIG_DESCRIPTION, &desc);

                wprintf(L"Service installed successfully\n");
                CloseServiceHandle(hService);
            }

            CloseServiceHandle(hSCM);
            return 0;
        }
        else if (_wcsicmp(argv[1], L"/uninstall") == 0 || _wcsicmp(argv[1], L"-uninstall") == 0)
        {
            // Uninstall service
            SC_HANDLE hSCM = OpenSCManagerW(NULL, NULL, SC_MANAGER_CONNECT);
            if (!hSCM)
            {
                wprintf(L"OpenSCManager failed, error=%d\n", GetLastError());
                return 1;
            }

            SC_HANDLE hService = OpenServiceW(hSCM, SERVICE_NAME, SERVICE_STOP | DELETE);
            if (!hService)
            {
                wprintf(L"OpenService failed, error=%d\n", GetLastError());
                CloseServiceHandle(hSCM);
                return 1;
            }

            // Stop service first
            SERVICE_STATUS status;
            ControlService(hService, SERVICE_CONTROL_STOP, &status);
            Sleep(1000);

            if (DeleteService(hService))
            {
                wprintf(L"Service uninstalled successfully\n");
            }
            else
            {
                wprintf(L"DeleteService failed, error=%d\n", GetLastError());
            }

            CloseServiceHandle(hService);
            CloseServiceHandle(hSCM);
            return 0;
        }
        else if (_wcsicmp(argv[1], L"/start") == 0 || _wcsicmp(argv[1], L"-start") == 0)
        {
            // Start service
            SC_HANDLE hSCM = OpenSCManagerW(NULL, NULL, SC_MANAGER_CONNECT);
            if (!hSCM)
            {
                wprintf(L"OpenSCManager failed, error=%d\n", GetLastError());
                return 1;
            }

            SC_HANDLE hService = OpenServiceW(hSCM, SERVICE_NAME, SERVICE_START);
            if (!hService)
            {
                wprintf(L"OpenService failed, error=%d\n", GetLastError());
                CloseServiceHandle(hSCM);
                return 1;
            }

            if (StartServiceW(hService, 0, NULL))
            {
                wprintf(L"Service started successfully\n");
            }
            else
            {
                wprintf(L"StartService failed, error=%d\n", GetLastError());
            }

            CloseServiceHandle(hService);
            CloseServiceHandle(hSCM);
            return 0;
        }
        else if (_wcsicmp(argv[1], L"/stop") == 0 || _wcsicmp(argv[1], L"-stop") == 0)
        {
            // Stop service
            SC_HANDLE hSCM = OpenSCManagerW(NULL, NULL, SC_MANAGER_CONNECT);
            if (!hSCM)
            {
                wprintf(L"OpenSCManager failed, error=%d\n", GetLastError());
                return 1;
            }

            SC_HANDLE hService = OpenServiceW(hSCM, SERVICE_NAME, SERVICE_STOP);
            if (!hService)
            {
                wprintf(L"OpenService failed, error=%d\n", GetLastError());
                CloseServiceHandle(hSCM);
                return 1;
            }

            SERVICE_STATUS status;
            if (ControlService(hService, SERVICE_CONTROL_STOP, &status))
            {
                wprintf(L"Service stopped successfully\n");
            }
            else
            {
                wprintf(L"ControlService failed, error=%d\n", GetLastError());
            }

            CloseServiceHandle(hService);
            CloseServiceHandle(hSCM);
            return 0;
        }
        else if (_wcsicmp(argv[1], L"/debug") == 0 || _wcsicmp(argv[1], L"-debug") == 0)
        {
            // Debug mode - run as console app
            wprintf(L"Running in debug mode...\n");
            g_Running = TRUE;
            g_ServiceStopEvent = CreateEventW(NULL, TRUE, FALSE, NULL);

            // Start pipe server in main thread
            PipeServerThread(NULL);

            return 0;
        }
    }

    // Run as service
    SERVICE_TABLE_ENTRYW serviceTable[] = {
        { (LPWSTR)SERVICE_NAME, ServiceMain },
        { NULL, NULL }
    };

    if (!StartServiceCtrlDispatcherW(serviceTable))
    {
        DWORD err = GetLastError();
        if (err == ERROR_FAILED_SERVICE_CONTROLLER_CONNECT)
        {
            wprintf(L"Usage: TaiBaiService.exe [/install | /uninstall | /start | /stop | /debug]\n");
        }
        return 1;
    }

    return 0;
}
