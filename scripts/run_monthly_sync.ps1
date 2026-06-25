# run_monthly_sync.ps1 — Chạy đồng bộ demographics theo từng tháng để tránh Rate Limit Facebook API

Write-Host "=== BẮT ĐẦU ĐỒNG BỘ DEMOGRAPHICS LỊCH SỬ THEO THÁNG (2026) ===" -ForegroundColor Cyan

# Danh sách các khoảng thời gian theo tháng
$months = @(
    @{ Start = "2026-01-01"; End = "2026-01-31" },
    @{ Start = "2026-02-01"; End = "2026-02-28" },
    @{ Start = "2026-03-01"; End = "2026-03-31" },
    @{ Start = "2026-04-01"; End = "2026-04-30" },
    @{ Start = "2026-05-01"; End = "2026-05-31" },
    @{ Start = "2026-06-01"; End = "2026-06-26" }
)

foreach ($m in $months) {
    Write-Host "`n>>> Đồng bộ khoảng thời gian: $($m.Start) -> $($m.End) <<<" -ForegroundColor Yellow
    python scripts/sync_fb_ad_demographics.py $m.Start $m.End
    
    # Nghỉ 15 giây giữa các đợt chạy để reset Rate Limit của Facebook API
    Write-Host "Chờ 15 giây trước khi tiếp tục đợt tiếp theo..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 15
}

Write-Host "`n=== ĐỒNG BỘ TOÀN BỘ HOÀN TẤT THÀNH CÔNG ===" -ForegroundColor Green
