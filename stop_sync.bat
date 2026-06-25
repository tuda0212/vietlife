@echo off
:: stop_sync.bat — Dừng Git Sync Daemon

setlocal
set "REPO_DIR=%~dp0"
set "PID_FILE=%REPO_DIR%.sync.pid"

if not exist "%PID_FILE%" (
    echo [INFO] Khong tim thay PID file. Daemon co the chua chay.
    :: Dừng tất cả pythonw có thể liên quan
    taskkill /IM pythonw.exe /F >nul 2>&1
    echo [INFO] Da dung tat ca pythonw.exe.
    goto :done
)

set /p PID=<"%PID_FILE%"
echo [INFO] Dang dung daemon PID=%PID%...
taskkill /PID %PID% /F >nul 2>&1
if errorlevel 1 (
    echo [WARN] Khong the dung PID=%PID%. Co the da dung roi.
) else (
    echo [OK] Daemon da dung.
)
del "%PID_FILE%" >nul 2>&1

:done
endlocal
