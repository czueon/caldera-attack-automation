# ========================================
# Network Share Propagation Simulation
# ========================================

$networkShare = "C:\Users\Public\data\NetworkShare"
$malwareLog = "C:\Users\Public\data\network_infection_log.txt"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Network Share Infection Simulation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/5] Creating simulated network share..." -ForegroundColor Yellow
if (Test-Path $networkShare) { Remove-Item $networkShare -Recurse -Force }
New-Item $networkShare -ItemType Directory -Force | Out-Null

# 공유 폴더처럼 보이는 구조
$computerNames = @("DESKTOP-543UKF", "DESKTOP-1B9JAD", "DESKTOP-391JFK", "DESKTOP-FKJ281", "DESKTOP-KF281K", "DESKTOP-29KH2", "DESKTOP-2916EJ", "DESKTOP-2K12J")

foreach ($comp in $computerNames) {
    New-Item "$networkShare\$comp" -ItemType Directory -Force | Out-Null
    "Shared documents from $comp" | Out-File "$networkShare\$comp\readme.txt"
}
Write-Host "  Created network share: $networkShare" -ForegroundColor Green
Write-Host "  Simulated computers: $($computerNames.Count)" -ForegroundColor Gray
Write-Host ""

Write-Host "[2/5] Creating malware payload..." -ForegroundColor Yellow

# 악성코드 스크립트
$malwareScript = @'
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$computer = $env:COMPUTERNAME
$logFile = "C:\Users\Public\data\network_infection_log.txt"

$entry = @"
[$timestamp] INFECTED: $computer
User: $env:USERNAME
Path: $PSScriptRoot
"@

$entry | Out-File $logFile -Append -Encoding UTF8

# 네트워크 공유로 전파 시뮬레이션
$networkPath = "C:\Users\Public\data\NetworkShare"
if (Test-Path $networkPath) {
    $computers = Get-ChildItem $networkPath -Directory
    foreach ($comp in $computers) {
        if (-not (Test-Path "$($comp.FullName)\infected.txt")) {
            "INFECTED by $computer at $timestamp" | Out-File "$($comp.FullName)\infected.txt"
        }
    }
}
'@

$malwareScript | Out-File "$networkShare\malware.ps1" -Encoding UTF8
Set-ItemProperty "$networkShare\malware.ps1" -Name Attributes -Value Hidden
Write-Host "  Created malware.ps1" -ForegroundColor Red

# VBS 실행 래퍼
$vbsContent = @'
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & scriptPath & "\malware.ps1""", 0, False
'@
$vbsContent | Out-File "$networkShare\run.vbs" -Encoding ASCII
Set-ItemProperty "$networkShare\run.vbs" -Name Attributes -Value Hidden
Write-Host "  Created run.vbs" -ForegroundColor Red

# 각 컴퓨터 폴더에 악성 문서 배포
Write-Host "  Deploying malicious files to network shares..." -ForegroundColor Red
foreach ($comp in $computerNames) {
    # 정상 파일처럼 보이는 바로가기
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$networkShare\$comp\Financial_Report_2024.lnk")
    $Shortcut.TargetPath = "wscript.exe"
    $Shortcut.Arguments = """$networkShare\run.vbs"""
    $Shortcut.IconLocation = "%SystemRoot%\System32\shell32.dll,1"  # 문서 아이콘
    $Shortcut.Save()
}
Write-Host "  Infected $($computerNames.Count) network shares" -ForegroundColor Red
Write-Host ""

Write-Host "[3/5] Network share structure:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Visible files (what users see):" -ForegroundColor Cyan
Get-ChildItem $networkShare -Recurse -File -Exclude "*.ps1","*.vbs","infected.txt" | Select-Object DirectoryName, Name | Format-Table -AutoSize
Write-Host ""

Write-Host "[4/5] Simulating infection spread..." -ForegroundColor Yellow
Write-Host ""

"" | Out-File $malwareLog -Force

$infectionScenarios = @(
    @{Computer="DESKTOP-543UKF"; User="User1"; Action="Opened Financial_Report_2024.lnk"},
    @{Computer="DESKTOP-1B9JAD"; User="User2"; Action="Accessed shared folder"},
    @{Computer="DESKTOP-391JFK"; User="User3"; Action="Downloaded malicious file"}
)

foreach ($scenario in $infectionScenarios) {
    Write-Host "  [$($scenario.Computer)] $($scenario.User): $($scenario.Action)" -ForegroundColor Yellow
    Start-Sleep 1
    
    Write-Host "  [INFECTION] Malware executing..." -ForegroundColor Red
    Start-Process "wscript.exe" -ArgumentList """$networkShare\run.vbs"""
    Start-Sleep 2
    
    Write-Host "  [PROPAGATION] Spreading to other shares..." -ForegroundColor Red
    Start-Sleep 1
    Write-Host ""
}

Write-Host "[5/5] Infection results:" -ForegroundColor Yellow
Write-Host ""

# 감염 로그 확인
if (Test-Path $malwareLog) {
    Write-Host "Infection Log:" -ForegroundColor Red
    Get-Content $malwareLog
    Write-Host ""
}

# 전파 확인
$infected = Get-ChildItem $networkShare -Recurse -Filter "infected.txt" -ErrorAction SilentlyContinue
Write-Host "Propagation Status:" -ForegroundColor Red
Write-Host "  Total shares: $($computerNames.Count)" -ForegroundColor White
Write-Host "  Infected: $($infected.Count)" -ForegroundColor Red

if ($infected) {
    Write-Host "`nInfected systems:" -ForegroundColor Red
    foreach ($file in $infected) {
        $comp = Split-Path (Split-Path $file.FullName -Parent) -Leaf
        Write-Host "    - $comp" -ForegroundColor Yellow
    }
}