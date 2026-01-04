# ========================================
# Screen Capture (Background)
# ========================================

$savePath = "C:\Users\Public\data"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$screenshotPath = "$savePath\screenshot_$timestamp.png"

New-Item -Path $savePath -ItemType Directory -Force | Out-Null

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# 전체 화면 영역 계산 (멀티모니터 포함)
$left = [System.Windows.Forms.SystemInformation]::VirtualScreen.Left
$top = [System.Windows.Forms.SystemInformation]::VirtualScreen.Top
$width = [System.Windows.Forms.SystemInformation]::VirtualScreen.Width
$height = [System.Windows.Forms.SystemInformation]::VirtualScreen.Height

# 캡처
$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($left, $top, 0, 0, $bitmap.Size)

# 저장
$bitmap.Save($screenshotPath, [System.Drawing.Imaging.ImageFormat]::Png)

# 정리
$graphics.Dispose()
$bitmap.Dispose()

# 로그 (화면에 안보임)
"[$(Get-Date)] Screenshot saved: $screenshotPath ($width x $height)" | Out-File "$savePath\capture_log.txt" -Append