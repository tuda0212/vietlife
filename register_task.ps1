# register_task.ps1 — Đăng ký Git Sync chạy tự động ẩn nền khi đăng nhập Windows
# Chạy file này MỘT LẦN với quyền Administrator.

$TaskName   = "VietlifeGitSync"
$ScriptPath = Join-Path $PSScriptRoot "sync_github.ps1"
$LogPath    = Join-Path $PSScriptRoot ".sync.log"

Write-Host "`n=== Dang ky Vietlife Git Sync Task ===" -ForegroundColor Cyan

# Kiem tra file script ton tai
if (-not (Test-Path $ScriptPath)) {
    Write-Host "[LOI] Khong tim thay: $ScriptPath" -ForegroundColor Red
    exit 1
}

# Xoa task cu neu da ton tai
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[INFO] Da tim thay task cu, dang xoa..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Cau hinh Action: chay PowerShell an nen (khong hien cua so)
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
    -WorkingDirectory $PSScriptRoot

# Cau hinh Trigger: chay ngay khi dang nhap Windows
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Cau hinh Settings
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -RunOnlyIfNetworkAvailable

# Dang ky Task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $action `
    -Trigger  $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Description "Tu dong dong bo 2 chieu giua local va GitHub cho Vietlife repo" `
    -Force | Out-Null

Write-Host "[OK] Da dang ky Task Scheduler: '$TaskName'" -ForegroundColor Green
Write-Host "     Script  : $ScriptPath"
Write-Host "     Log     : $LogPath"

# Chay ngay lap tuc
Write-Host "`n[INFO] Dang khoi dong sync daemon ngay bay gio..." -ForegroundColor Cyan
Start-ScheduledTask -TaskName $TaskName

Start-Sleep -Seconds 2

$status = (Get-ScheduledTask -TaskName $TaskName).State
Write-Host "[OK] Trang thai hien tai: $status" -ForegroundColor Green
Write-Host "`n=== HOAN TAT ===" -ForegroundColor Cyan
Write-Host "Daemon se tu dong chay an nen moi khi ban dang nhap Windows."
Write-Host "De dung:   Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
Write-Host "Xem log :  Get-Content '$LogPath' -Tail 50 -Wait"
