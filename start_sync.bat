@echo off
:: start_sync.bat — Chạy Git Sync Daemon ẩn nền trên Windows
:: Cửa sổ sẽ không hiện ra. Log xem tại: .sync.log

setlocal
set "REPO_DIR=%~dp0"
set "SCRIPT=%REPO_DIR%git_sync.py"
set "LOG=%REPO_DIR%.sync.log"
set "PID_FILE=%REPO_DIR%.sync.pid"

:: Kiểm tra script tồn tại
if not exist "%SCRIPT%" (
    echo [LỖI] Không tìm thấy git_sync.py tại %SCRIPT%
    pause
    exit /b 1
)

:: Kiểm tra xem đã chạy chưa (dựa vào PID file)
if exist "%PID_FILE%" (
    set /p OLD_PID=<"%PID_FILE%"
    tasklist /FI "PID eq %OLD_PID%" 2>nul | find "%OLD_PID%" >nul
    if not errorlevel 1 (
        echo [INFO] Git Sync Daemon da dang chay ^(PID=%OLD_PID%^).
        echo [INFO] Dung stop_sync.bat truoc khi chay lai.
        pause
        exit /b 0
    )
    del "%PID_FILE%" >nul 2>&1
)

:: Kiểm tra watchdog
python -c "import watchdog" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Cai dat thu vien watchdog...
    pip install watchdog --quiet
)

:: Chạy daemon ẩn nền (dùng pythonw để không hiện cửa sổ console)
echo [INFO] Dang khoi dong Git Sync Daemon...
start /B pythonw "%SCRIPT%" >> "%LOG%" 2>&1

:: Chờ 2 giây rồi tìm PID của process vừa tạo
timeout /t 2 /nobreak >nul

:: Lưu PID (tìm PID của pythonw mới nhất)
for /f "tokens=2 delims= " %%P in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO TABLE /NH 2^>nul ^| head -1') do (
    echo %%P > "%PID_FILE%"
    echo [OK] Daemon da chay ^(PID=%%P^)
    goto :done
)

:: Fallback nếu không tìm được PID
wmic process where "name='pythonw.exe'" get ProcessId /value 2>nul | find "ProcessId" > "%PID_FILE%"
echo [OK] Daemon da khoi dong.

:done
echo [INFO] Log duoc ghi tai: %LOG%
echo [INFO] De dung: chay stop_sync.bat
endlocal
