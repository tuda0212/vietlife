# run_monthly_sync.ps1 — Dong bo demographics theo tung thang de tranh Rate Limit

Write-Host "=== BAT DAU DONG BO DEMOGRAPHICS LICH SU THEO THANG (2026) ===" -ForegroundColor Cyan

# Danh sach cac khoang thoi gian theo thang
$months = @(
    @{ Start = "2026-01-01"; End = "2026-01-31" },
    @{ Start = "2026-02-01"; End = "2026-02-28" },
    @{ Start = "2026-03-01"; End = "2026-03-31" },
    @{ Start = "2026-04-01"; End = "2026-04-30" },
    @{ Start = "2026-05-01"; End = "2026-05-31" },
    @{ Start = "2026-06-01"; End = "2026-06-26" }
)

foreach ($m in $months) {
    Write-Host "=== Dong bo thang: $($m.Start) den $($m.End) ===" -ForegroundColor Yellow
    python scripts/sync_fb_ad_demographics.py $m.Start $m.End
    
    # Nghi 15 giay de Facebook API cooldown
    Write-Host "Cho 15 giay truoc khi chay thang tiep theo..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 15
}

Write-Host "=== DONG BO TOAN BO HOAN TAT ===" -ForegroundColor Green
