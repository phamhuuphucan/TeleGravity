<#
.SYNOPSIS
    Quản lý Antigravity Telegram Bridge trên Windows (PowerShell).
    Dùng: .\service.ps1 setup | install | uninstall | restart | status | logs | login
#>
param(
    [Parameter(Position=0)]
    [ValidateSet("setup", "install", "uninstall", "restart", "status", "logs", "login")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"
$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $Dir ".venv"
$Py = Join-Path $VenvDir "Scripts\python.exe"
$Pyw = Join-Path $VenvDir "Scripts\pythonw.exe"
$BotScript = Join-Path $Dir "bot.py"
$LogDir = Join-Path $Dir "logs"
$LogFile = Join-Path $LogDir "bot.log"
$EnvFile = Join-Path $Dir ".env"
$TaskName = "AntigravityTelegramBridge"

function Find-Agy {
    $cmd = Get-Command agy -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "$env:USERPROFILE\.local\bin\agy.exe",
        "$env:USERPROFILE\.local\bin\agy.cmd",
        "$env:LOCALAPPDATA\Programs\Antigravity\bin\agy.cmd",
        "$env:LOCALAPPDATA\Programs\Antigravity\bin\agy.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return "agy"
}

switch ($Action) {
    "setup" {
        Write-Host "🚀 Đang thiết lập môi trường Python (.venv) trên Windows..." -ForegroundColor Cyan
        if (!(Test-Path $VenvDir)) {
            python -m venv $VenvDir
        }
        & $Py -m pip install --upgrade pip -q
        & $Py -m pip install -r (Join-Path $Dir "requirements.txt") -q
        if (!(Test-Path $EnvFile)) {
            Copy-Item (Join-Path $Dir ".env.example") $EnvFile
            Write-Host "`n📝 Cấu hình nhanh Bot Telegram (nhấn Enter để dùng mặc định):" -ForegroundColor Cyan
            $tgToken = Read-Host "1. Nhập TELEGRAM_BOT_TOKEN (từ @BotFather)"
            $tgUid = Read-Host "2. Nhập ALLOWED_USER_IDS (từ @userinfobot)"
            $defaultProj = Join-Path $env:USERPROFILE "Projects"
            $projDir = Read-Host "3. Thư mục chứa dự án code (PROJECTS_ROOT) [mặc định: $defaultProj]"
            if ([string]::IsNullOrWhiteSpace($projDir)) { $projDir = $defaultProj }
            $defaultPa = Join-Path $projDir "Personal_Assistant"
            $paDir = Read-Host "4. Thư mục Trợ lý cá nhân (ASSISTANT_HOME) [mặc định: $defaultPa]"
            if ([string]::IsNullOrWhiteSpace($paDir)) { $paDir = $defaultPa }

            New-Item -ItemType Directory -Force -Path $projDir | Out-Null
            New-Item -ItemType Directory -Force -Path $paDir | Out-Null

            $agyBin = Find-Agy
            $lines = Get-Content $EnvFile -Encoding UTF8
            $newLines = foreach ($ln in $lines) {
                if ($ln -like "TELEGRAM_BOT_TOKEN=*" -and $tgToken) { "TELEGRAM_BOT_TOKEN=$tgToken" }
                elseif ($ln -like "ALLOWED_USER_IDS=*" -and $tgUid) { "ALLOWED_USER_IDS=$tgUid" }
                elseif ($ln -like "AGY_PATH=*" -and $agyBin) { "AGY_PATH=$agyBin" }
                elseif ($ln -like "PROJECTS_ROOT=*") { "PROJECTS_ROOT=$projDir" }
                elseif ($ln -like "ASSISTANT_HOME=*") { "ASSISTANT_HOME=$paDir" }
                elseif ($ln -like "DEFAULT_WORKSPACE=*") { "DEFAULT_WORKSPACE=$paDir" }
                else { $ln }
            }
            $newLines | Set-Content $EnvFile -Encoding UTF8
            if ([string]::IsNullOrWhiteSpace($tgToken) -or [string]::IsNullOrWhiteSpace($tgUid)) {
                Write-Host "⚠️ Bạn chưa điền đủ Token/User ID — đang mở Notepad để bạn bổ sung vào .env..." -ForegroundColor Yellow
                notepad $EnvFile
            } else {
                Write-Host "✅ Đã lưu cấu hình vào .env!" -ForegroundColor Green
            }
        }
        Write-Host "✅ Thiết lập hoàn tất! Chạy '.\service.ps1 login' hoặc '.\service.ps1 install'." -ForegroundColor Green
    }
    "install" {
        if (!(Test-Path $EnvFile)) {
            Write-Error "Chưa có file .env! Hãy chạy: .\service.ps1 setup"
        }
        New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
        $ActionCmd = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"`"$Py`" `"$BotScript`" >> `"$LogFile`" 2>&1`"" -WorkingDirectory $Dir
        $Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
        $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
        Register-ScheduledTask -TaskName $TaskName -Action $ActionCmd -Trigger $Trigger -Settings $Settings -Force | Out-Null
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "✅ Đã cài đặt và khởi chạy nền '$TaskName' trong Windows Task Scheduler!" -ForegroundColor Green
        Write-Host "👉 Xem log: .\service.ps1 logs"
    }
    "uninstall" {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*$BotScript*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Write-Host "✅ Đã gỡ tác vụ chạy nền '$TaskName'." -ForegroundColor Green
    }
    "restart" {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*$BotScript*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 1
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "✅ Đã khởi động lại '$TaskName'." -ForegroundColor Green
    }
    "status" {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($task) {
            Write-Host "Trạng thái Task Scheduler: $($task.State)" -ForegroundColor Cyan
        } else {
            Write-Host "Chưa cài đặt Task Scheduler (chạy: .\service.ps1 install)" -ForegroundColor Yellow
        }
        $procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*$BotScript*" }
        if ($procs) {
            foreach ($p in $procs) {
                Write-Host "🟢 Tiến trình bot.py đang chạy (PID: $($p.ProcessId))" -ForegroundColor Green
            }
        } else {
            Write-Host "⚪ Tiến trình bot.py hiện không chạy." -ForegroundColor Gray
        }
    }
    "logs" {
        if (Test-Path $LogFile) {
            Get-Content $LogFile -Tail 100 -Wait
        } else {
            Write-Host "Chưa có file log tại $LogFile" -ForegroundColor Yellow
        }
    }
    "login" {
        $agy = Find-Agy
        Write-Host "🔑 Đang mở trình duyệt đăng nhập Google cho Antigravity CLI ($agy)..." -ForegroundColor Cyan
        & $agy acp --login
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($task) {
            & $MyInvocation.MyCommand.Path restart
        }
    }
}
