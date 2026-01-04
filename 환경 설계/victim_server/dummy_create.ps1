# =====================================
# TTPS4 더미 민감 데이터 생성 스크립트
# =====================================

$base = "C:\Users\Public\data"
New-Item -ItemType Directory -Force -Path $base | Out-Null


# -------------------------------------
# 1. TXT 파일 (계정 정보)
# -------------------------------------
"admin: q1w2e3!"         | Out-File "$base\credentials.txt"
"db_user: root; pw=1234" | Out-File "$base\db_access.txt"


# -------------------------------------
# 2. CSV (직원 인사 데이터)
# -------------------------------------
@"
name,department,email,salary
Kim Jiho,Finance,jiho.kim@victimcorp.com,4200
Lee Sooah,HR,sooah.lee@victimcorp.com,3900
Park Minjae,R&D,minjae.park@victimcorp.com,5500
"@ | Out-File "$base\hr_records.csv"


# -------------------------------------
# 3. JSON (내부 설정 정보)
# -------------------------------------
@"
{
  "system": "IntranetPortal",
  "version": "2.1.7",
  "keys": {
     "jwt_secret": "ABC123SECRET",
     "api_key": "KJ3290-SD923-XX002"
  }
}
"@ | Out-File "$base\config.json"


# -------------------------------------
# 4. LOG 파일 (서버 활동 로그)
# -------------------------------------
Get-Date | Out-File "$base\server.log"
"User 'admin' failed login"        | Out-File "$base\server.log" -Append
"User 'kim' accessed HR module"    | Out-File "$base\server.log" -Append
"Connection from 192.168.56.105"   | Out-File "$base\server.log" -Append


# -------------------------------------
# 5. DOCX 생성
# -------------------------------------
$docxTemp = "$base\_docx"
New-Item -ItemType Directory -Force -Path "$docxTemp\word" | Out-Null

$docxContent = @"
<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>
  <w:body>
    <w:p><w:r><w:t>Project Plan – Confidential</w:t></w:r></w:p>
    <w:p><w:r><w:t>Phase 1: AI model development</w:t></w:r></w:p>
  </w:body>
</w:document>
"@

$docxContent | Out-File "$docxTemp\word\document.xml"

$docxZip = "$base\docx.zip"
Compress-Archive -Path "$docxTemp\*" -DestinationPath $docxZip -Force
Move-Item -Force $docxZip "$base\ProjectPlan.docx"
Remove-Item $docxTemp -Recurse -Force


# -------------------------------------
# 6. XLSX 생성
# -------------------------------------
$xlsxTemp = "$base\_xlsx"
New-Item -ItemType Directory -Force -Path "$xlsxTemp\xl\worksheets" | Out-Null

$xlsxSheet = @"
<?xml version='1.0' encoding='UTF-8'?>
<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>
  <sheetData>
    <row r='1'>
      <c r='A1' t='s'><v>0</v></c>
      <c r='B1'><v>5500</v></c>
    </row>
  </sheetData>
</worksheet>
"@

$xlsxSheet | Out-File "$xlsxTemp\xl\worksheets\sheet1.xml"

$xlsxZip = "$base\xlsx.zip"
Compress-Archive -Path "$xlsxTemp\*" -DestinationPath $xlsxZip -Force
Move-Item -Force $xlsxZip "$base\FinanceReport.xlsx"
Remove-Item $xlsxTemp -Recurse -Force


# -------------------------------------
# 7. PDF 생성 (텍스트 기반 미니 PDF)
# -------------------------------------
$pdfPath = "$base\Confidential.pdf"
$pdfContent = "%PDF-1.1`n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj`n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj`n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj`n4 0 obj<</Length 44>>stream`nBT /F1 24 Tf 100 700 Td (Confidential PDF File) Tj ET`nendstream`nendobj`nxref`n0 5`n0000000000 65535 f `n0000000010 00000 n `n0000000060 00000 n `n0000000110 00000 n `n0000000200 00000 n `ntrailer<</Root 1 0 R/Size 5>>`nstartxref`n300`n%%EOF"
$pdfContent | Out-File $pdfPath


# -------------------------------------
# 8. PNG (1x1 더미 이미지)
# -------------------------------------
$pngBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAF/wJKRYnS0gAAAABJRU5ErkJggg=="
[IO.File]::WriteAllBytes("$base\image.png", [Convert]::FromBase64String($pngBase64))

# -------------------------------------
# 완료 메시지
# -------------------------------------
Write-Host "[+] Dummy data created at $base"
