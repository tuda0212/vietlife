# =============================================================================
#  sync_github.ps1 — Đồng bộ 2 chiều Local <-> GitHub (chạy ẩn nền)
#
#  Chiều 1 (Local -> GitHub):
#    FileSystemWatcher theo dõi file thay đổi
#    Debounce 15s -> git add -A -> commit -> push
#
#  Chiều 2 (GitHub -> Local):
#    Timer kiểm tra remote mỗi 5 phút
#    Nếu có commit mới từ người khác -> git pull --rebase
#
#  Cách dùng: chạy register_task.ps1 một lần để đăng ký tự động chạy.
# =============================================================================

param(
    [string]$RepoDir    = (Split-Path -Parent $MyInvocation.MyCommand.Path),
    [int]$DebounceSec   = 15,
    [int]$PollMinutes   = 5
)

$LogFile   = Join-Path $RepoDir ".sync.log"
$StateFile = Join-Path $RepoDir ".sync_state.json"
$Branch    = "auto-backup"
$Remote    = "origin"

# Thư mục / extension không theo dõi
$IgnoreDirs  = @(".git", "__pycache__", ".venv", "node_modules")
$IgnoreFiles = @(".sync.log", ".sync_state.json", ".DS_Store", "Thumbs.db")
$IgnoreExts  = @(".pyc", ".pyo", ".pyd", ".log")

# =============================================================================
#  LOGGING
# =============================================================================
function Write-Log {
    param([string]$Msg, [string]$Level = "INFO")
    $ts   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts [$Level] $Msg"
    Write-Output $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

# =============================================================================
#  HELPERS: STATE FILE
# =============================================================================
function Get-State {
    if (Test-Path $StateFile) {
        try { return (Get-Content $StateFile -Raw -Encoding UTF8 | ConvertFrom-Json) }
        catch {}
    }
    return [PSCustomObject]@{ last_pushed_commit = "" }
}

function Save-State {
    param($State)
    $State | ConvertTo-Json | Set-Content -Path $StateFile -Encoding UTF8
}

# =============================================================================
#  HELPERS: GIT
# =============================================================================
function Invoke-Git {
    param([string[]]$Args)
    $result = & git @Args 2>&1
    return @{
        ExitCode = $LASTEXITCODE
        Output   = ($result -join "`n").Trim()
    }
}

function Get-LocalCommit {
    $r = Invoke-Git @("rev-parse", "HEAD")
    return $r.Output
}

function Get-RemoteCommit {
    Invoke-Git @("fetch", $Remote, $Branch, "--quiet") | Out-Null
    $r = Invoke-Git @("rev-parse", "$Remote/$Branch")
    return $r.Output
}

function Test-HasLocalChanges {
    $r = Invoke-Git @("status", "--porcelain")
    return ($r.Output.Trim() -ne "")
}

# =============================================================================
#  CHIEU 1: LOCAL -> GITHUB
# =============================================================================
$script:PushLock = $false

function Push-LocalChanges {
    if ($script:PushLock) { return }
    if (-not (Test-HasLocalChanges)) { return }

    $script:PushLock = $true
    try {
        $msg = "auto-sync: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

        $r = Invoke-Git @("add", "-A")
        if ($r.ExitCode -ne 0) {
            Write-Log "git add loi: $($r.Output)" "ERROR"
            return
        }

        $r = Invoke-Git @("commit", "-m", $msg)
        if ($r.ExitCode -ne 0) {
            if ($r.Output -match "nothing to commit") { return }
            Write-Log "git commit loi: $($r.Output)" "ERROR"
            return
        }
        Write-Log "Committed: $msg"

        $r = Invoke-Git @("push", $Remote, $Branch)
        if ($r.ExitCode -ne 0) {
            Write-Log "Push that bai, thu pull --rebase roi push lai..." "WARN"
            Invoke-Git @("pull", "--rebase", $Remote, $Branch) | Out-Null
            $r2 = Invoke-Git @("push", $Remote, $Branch)
            if ($r2.ExitCode -ne 0) {
                Write-Log "Push lan 2 that bai: $($r2.Output)" "ERROR"
                return
            }
        }

        $newCommit = Get-LocalCommit
        $state = Get-State
        $state.last_pushed_commit = $newCommit
        Save-State $state
        Write-Log "[LOCAL->GITHUB] Pushed OK [$($newCommit.Substring(0,8))]"
    }
    finally {
        $script:PushLock = $false
    }
}

# =============================================================================
#  CHIEU 2: GITHUB -> LOCAL (goi tu timer)
# =============================================================================
$script:IsPulling = $false

function Check-Remote {
    if ($script:IsPulling) { return }

    $remoteCommit = Get-RemoteCommit
    $localCommit  = Get-LocalCommit
    $state        = Get-State
    $lastPushed   = $state.last_pushed_commit

    # Da dong bo
    if ($remoteCommit -eq $localCommit) { return }

    # Day chinh la commit minh vua push
    if ($remoteCommit -eq $lastPushed) { return }

    Write-Log "[GITHUB->LOCAL] Commit moi tren remote [$($remoteCommit.Substring(0,8))] -> pull ve..."

    # Stash neu co thay doi local chua commit
    $stashed = $false
    if (Test-HasLocalChanges) {
        $r = Invoke-Git @("stash", "push", "-m", "git-sync-auto-stash")
        if ($r.ExitCode -eq 0) {
            $stashed = $true
            Write-Log "Stash local changes truoc khi pull."
        }
    }

    $script:IsPulling = $true
    try {
        $r = Invoke-Git @("pull", "--rebase", $Remote, $Branch)
        if ($r.ExitCode -ne 0) {
            Write-Log "pull --rebase loi: $($r.Output)" "ERROR"
        } else {
            $newLocal = Get-LocalCommit
            Write-Log "[GITHUB->LOCAL] Pull OK - HEAD gio la [$($newLocal.Substring(0,8))]"
            $state = Get-State
            $state.last_pushed_commit = $newLocal
            Save-State $state
        }
    }
    finally {
        $script:IsPulling = $false
    }

    if ($stashed) {
        $r = Invoke-Git @("stash", "pop")
        if ($r.ExitCode -ne 0) {
            Write-Log "stash pop loi (co the conflict): $($r.Output)" "WARN"
        } else {
            Write-Log "Khoi phuc local changes sau pull thanh cong."
        }
    }
}

# =============================================================================
#  FILESYSTEMWATCHER — theo doi file local
# =============================================================================
$script:DebounceTimer = $null

function Should-Ignore {
    param([string]$FilePath)
    $name = Split-Path $FilePath -Leaf
    $ext  = [System.IO.Path]::GetExtension($FilePath)

    if ($IgnoreFiles -contains $name) { return $true }
    if ($IgnoreExts  -contains $ext)  { return $true }

    foreach ($dir in $IgnoreDirs) {
        if ($FilePath -match [regex]::Escape("\$dir\")) { return $true }
    }
    return $false
}

function Reset-DebounceTimer {
    if ($script:DebounceTimer) {
        $script:DebounceTimer.Stop()
        $script:DebounceTimer.Dispose()
    }
    $script:DebounceTimer = New-Object System.Timers.Timer
    $script:DebounceTimer.Interval = $DebounceSec * 1000
    $script:DebounceTimer.AutoReset = $false

    Register-ObjectEvent -InputObject $script:DebounceTimer -EventName Elapsed -Action {
        if (-not $script:IsPulling) {
            Push-LocalChanges
        }
    } | Out-Null

    $script:DebounceTimer.Start()
}

$watcher                       = New-Object System.IO.FileSystemWatcher
$watcher.Path                  = $RepoDir
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents   = $true
$watcher.NotifyFilter          = [System.IO.NotifyFilters]::LastWrite -bor
                                 [System.IO.NotifyFilters]::FileName  -bor
                                 [System.IO.NotifyFilters]::DirectoryName

$action = {
    $path = $Event.SourceEventArgs.FullPath
    if (-not (Should-Ignore $path)) {
        if (-not $script:IsPulling) {
            Reset-DebounceTimer
        }
    }
}

Register-ObjectEvent $watcher "Changed" -Action $action | Out-Null
Register-ObjectEvent $watcher "Created" -Action $action | Out-Null
Register-ObjectEvent $watcher "Deleted" -Action $action | Out-Null
Register-ObjectEvent $watcher "Renamed" -Action $action | Out-Null

# =============================================================================
#  POLL TIMER — kiem tra remote dinh ky
# =============================================================================
$pollTimer          = New-Object System.Timers.Timer
$pollTimer.Interval = $PollMinutes * 60 * 1000
$pollTimer.AutoReset = $true

Register-ObjectEvent -InputObject $pollTimer -EventName Elapsed -Action {
    Check-Remote
} | Out-Null

$pollTimer.Start()

# =============================================================================
#  KHOI DONG
# =============================================================================

# Khoi tao state
$state = Get-State
if ($state.last_pushed_commit -eq "") {
    $head = Get-LocalCommit
    $state.last_pushed_commit = $head
    Save-State $state
}

Write-Log ("=" * 55)
Write-Log "  Git Sync Daemon - Vietlife"
Write-Log "  Repo     : $RepoDir"
Write-Log "  Debounce : ${DebounceSec}s  |  Poll : ${PollMinutes}min"
Write-Log ("=" * 55)
Write-Log "Daemon dang chay..."

# Kiem tra remote ngay lan dau sau 30 giay
Start-Sleep -Seconds 30
Check-Remote

# Vong lap chinh - giu process song
while ($true) {
    Start-Sleep -Seconds 5
}
