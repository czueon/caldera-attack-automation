# ========================================
# Credentials in Files - Dump & Collection
# ========================================

$logPath = "C:\Users\Public\data\credentials_dump.txt"
$filesPath = "C:\Users\Public\data\sample_files"

# 폴더 생성
New-Item -Path "C:\Users\Public\data" -ItemType Directory -Force | Out-Null
New-Item -Path $filesPath -ItemType Directory -Force | Out-Null

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Credentials in Files Simulation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========================================
# 1. 샘플 파일 생성 (계정정보 포함)
# ========================================

Write-Host "[1/4] Creating sample files with credentials..." -ForegroundColor Yellow

# config.txt
$configContent = @"
[Database]
Server=192.168.1.100
Port=3306
Username=dbadmin
Password=DbP@ss123!

[API]
Endpoint=https://api.company.com
APIKey=sk_live_51Hxyz1234567890
Secret=api_secret_abc123

[Email]
SMTPServer=smtp.gmail.com
Username=admin@company.com
Password=EmailP@ss456
"@
$configContent | Out-File "$filesPath\config.txt" -Encoding UTF8

# credentials.xml
$xmlContent = @"
<?xml version="1.0"?>
<credentials>
  <account>
    <service>FTP Server</service>
    <username>ftpuser</username>
    <password>Ftp123456</password>
    <host>ftp.company.com</host>
  </account>
  <account>
    <service>SSH Server</service>
    <username>root</username>
    <password>RootP@ssw0rd</password>
    <host>192.168.1.50</host>
  </account>
</credentials>
"@
$xmlContent | Out-File "$filesPath\credentials.xml" -Encoding UTF8

# passwords.json
$jsonContent = @"
{
  "accounts": [
    {
      "service": "AWS",
      "access_key": "AKIAIOSFODNN7EXAMPLE",
      "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
      "region": "us-east-1"
    },
    {
      "service": "Database",
      "username": "postgres",
      "password": "PostgresP@ss789",
      "connection_string": "postgresql://localhost:5432/mydb"
    }
  ]
}
"@
$jsonContent | Out-File "$filesPath\passwords.json" -Encoding UTF8

# .env
$envContent = @"
DB_HOST=localhost
DB_USER=webapp
DB_PASS=WebApp@2024!
DB_NAME=production

REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=RedisSecret123

JWT_SECRET=my-super-secret-jwt-key-12345
API_TOKEN=bearer_token_xyz789abc
"@
$envContent | Out-File "$filesPath\.env" -Encoding ASCII

# backup_script.ps1
$scriptContent = @'
# Database Backup Script
$server = "192.168.1.200"
$username = "backup_admin"
$password = "BackupP@ss2024!"

# Connection
$cred = New-Object System.Management.Automation.PSCredential($username, (ConvertTo-SecureString $password -AsPlainText -Force))
'@
$scriptContent | Out-File "$filesPath\backup_script.ps1" -Encoding UTF8

Write-Host "  Created: config.txt" -ForegroundColor Green
Write-Host "  Created: credentials.xml" -ForegroundColor Green
Write-Host "  Created: passwords.json" -ForegroundColor Green
Write-Host "  Created: .env" -ForegroundColor Green
Write-Host "  Created: backup_script.ps1" -ForegroundColor Green
Write-Host ""

# ========================================
# 2. 파일 검색 및 파싱
# ========================================

Write-Host "[2/4] Searching for credential files..." -ForegroundColor Yellow

$credentialFiles = Get-ChildItem -Path $filesPath -File | 
    Where-Object { 
        $_.Name -match "(config|credential|password|secret|key|\.env|backup)" -or
        $_.Extension -match "\.(txt|xml|json|conf|ini|ps1|bat|sh)"
    }

Write-Host "  Found $($credentialFiles.Count) suspicious files" -ForegroundColor Cyan
$credentialFiles | ForEach-Object {
    Write-Host "    - $($_.Name)" -ForegroundColor Gray
}
Write-Host ""

# ========================================
# 3. 계정정보 추출
# ========================================

Write-Host "[3/4] Extracting credentials..." -ForegroundColor Yellow

$logHeader = @"
===========================================
Credential Harvesting Report
===========================================
Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Target Directory: $filesPath
Files Analyzed: $($credentialFiles.Count)
===========================================

"@
Set-Content -Path $logPath -Value $logHeader -Encoding UTF8

$totalCredentials = 0

foreach ($file in $credentialFiles) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    
    if (-not $content) { continue }
    
    $fileLog = "`n--- File: $($file.Name) ---`n"
    $fileLog += "Path: $($file.FullName)`n"
    $fileLog += "Size: $($file.Length) bytes`n`n"
    
    # 패턴 매칭
    $patterns = @{
        'Username' = '(?i)(user|username|user_name|login)["\s:=]+([^\s"]+)'
        'Password' = '(?i)(pass|password|passwd|pwd)["\s:=]+([^\s"]+)'
        'API Key' = '(?i)(api[_-]?key|apikey)["\s:=]+([^\s"]+)'
        'Secret' = '(?i)(secret|secret[_-]?key)["\s:=]+([^\s"]+)'
        'Token' = '(?i)(token|auth[_-]?token|bearer)["\s:=]+([^\s"]+)'
        'Access Key' = '(?i)(access[_-]?key|access_key_id)["\s:=]+([^\s"]+)'
        'Connection String' = '(?i)(connection[_-]?string|conn[_-]?str)["\s:=]+([^\s"]+)'
    }
    
    $foundCount = 0
    
    foreach ($patternName in $patterns.Keys) {
        $matches = [regex]::Matches($content, $patterns[$patternName])
        
        foreach ($match in $matches) {
            if ($match.Groups.Count -ge 3) {
                $value = $match.Groups[2].Value.Trim('"').Trim("'").Trim()
                if ($value.Length -gt 3) {
                    $fileLog += "[+] $patternName : $value`n"
                    $foundCount++
                    $totalCredentials++
                    Write-Host "  [!] Found $patternName in $($file.Name)" -ForegroundColor Red
                }
            }
        }
    }
    
    # IP 주소 추출
    $ipMatches = [regex]::Matches($content, '\b(?:\d{1,3}\.){3}\d{1,3}\b')
    if ($ipMatches.Count -gt 0) {
        $fileLog += "`n[+] IP Addresses:`n"
        $ipMatches | ForEach-Object { 
            $fileLog += "    - $($_.Value)`n" 
        }
    }
    
    # 이메일 주소 추출
    $emailMatches = [regex]::Matches($content, '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    if ($emailMatches.Count -gt 0) {
        $fileLog += "`n[+] Email Addresses:`n"
        $emailMatches | ForEach-Object { 
            $fileLog += "    - $($_.Value)`n" 
        }
    }
    
    if ($foundCount -gt 0) {
        $fileLog += "`nTotal credentials in this file: $foundCount`n"
        Add-Content -Path $logPath -Value $fileLog -Encoding UTF8
    }
}

# ========================================
# 4. 결과 요약
# ========================================

Write-Host ""
Write-Host "[4/4] Generating report..." -ForegroundColor Yellow

$summary = @"

===========================================
SUMMARY
===========================================
Total Files Analyzed: $($credentialFiles.Count)
Total Credentials Found: $totalCredentials

File Types:
$(($credentialFiles | Group-Object Extension | ForEach-Object { "  $($_.Name): $($_.Count) files" }) -join "`n")

===========================================
"@

Add-Content -Path $logPath -Value $summary -Encoding UTF8

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Extraction Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 결과 표시
Write-Host "Statistics:" -ForegroundColor Yellow
Write-Host "  Files analyzed: $($credentialFiles.Count)" -ForegroundColor White
Write-Host "  Credentials found: $totalCredentials" -ForegroundColor Red
Write-Host ""

# 로그 내용 일부 표시
Write-Host "Sample extracted data:" -ForegroundColor Yellow
Write-Host ""
$logContent = Get-Content $logPath -Raw -Encoding UTF8
$sampleLines = ($logContent -split "`n" | Select-Object -First 40) -join "`n"
Write-Host $sampleLines -ForegroundColor White

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Demo Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "What happened:" -ForegroundColor Yellow
Write-Host "  1. Created sample files with credentials" -ForegroundColor White
Write-Host "  2. Searched for suspicious file patterns" -ForegroundColor White
Write-Host "  3. Extracted credentials using regex" -ForegroundColor White
Write-Host "  4. Collected: usernames, passwords, API keys, tokens" -ForegroundColor White
Write-Host "  5. Also found: IP addresses, email addresses" -ForegroundColor White
Write-Host ""
Write-Host "Files location:" -ForegroundColor Yellow
Write-Host "  Sample files: $filesPath" -ForegroundColor Gray
Write-Host "  Dump log: $logPath" -ForegroundColor Gray
Write-Host ""
Write-Host "View full dump:" -ForegroundColor Yellow
Write-Host "  Get-Content '$logPath' -Encoding UTF8" -ForegroundColor Gray
Write-Host ""
Write-Host "View sample files:" -ForegroundColor Yellow
Write-Host "  Get-ChildItem '$filesPath'" -ForegroundColor Gray
Write-Host ""
Write-Host "Clean up:" -ForegroundColor Yellow
Write-Host "  Remove-Item '$filesPath' -Recurse -Force" -ForegroundColor Gray
Write-Host "  Remove-Item '$logPath' -Force" -ForegroundColor Gray
Write-Host ""