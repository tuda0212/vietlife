# analyze_pancake_ads.ps1
# Script to analyze pancake chat history and match it with ad creatives.
# This script is written in 100% ASCII to avoid encoding issues in Windows PowerShell.
# All Vietnamese keywords and labels are loaded from keywords.json.

param(
    [string]$StartDate,
    [string]$EndDate
)

$chatsFile = "pancake_chats_with_ads.json"
$creativesFile = "ad_creatives.json"
$keywordsFile = ".agents/skills/ad-insight-alignment/scripts/keywords.json"

if (-not (Test-Path $chatsFile)) {
    Write-Error "Could not find file $chatsFile"
    exit 1
}
if (-not (Test-Path $creativesFile)) {
    Write-Error "Could not find file $creativesFile"
    exit 1
}
if (-not (Test-Path $keywordsFile)) {
    Write-Error "Could not find file $keywordsFile"
    exit 1
}

# Ensure Output Encoding is UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Parse Dates if provided
$filterStart = $null
$filterEnd = $null
if ($StartDate) {
    $filterStart = [DateTime]::ParseExact($StartDate, "yyyy-MM-dd", $null)
    Write-Host "[*] Filtering chats starting from: $StartDate" -ForegroundColor Yellow
}
if ($EndDate) {
    # Set to end of day
    $filterEnd = [DateTime]::ParseExact($EndDate, "yyyy-MM-dd", $null).AddDays(1).AddTicks(-1)
    Write-Host "[*] Filtering chats up to: $EndDate" -ForegroundColor Yellow
}

# Load Data
$chatsData = Get-Content -Raw -Path $chatsFile -Encoding UTF8 | ConvertFrom-Json
$creativesData = Get-Content -Raw -Path $creativesFile -Encoding UTF8 | ConvertFrom-Json
$k = Get-Content -Raw -Path $keywordsFile -Encoding UTF8 | ConvertFrom-Json

$chats = $chatsData.chats
$regexPhone = $k.regexPhone
$bookingKeywords = $k.bookingKeywords
$painCost = $k.painCost
$painSymptoms = $k.painSymptoms
$painFearSurgery = $k.painFearSurgery
$painTrust = $k.painTrust
$painLocation = $k.painLocation
$clinicSenders = $k.clinicSenders
$l = $k.labels

# Analyze
$adStats = @{}
$includedChatsCount = 0

foreach ($chat in $chats) {
    if ($null -eq $chat.ads -or $chat.ads.Count -eq 0) {
        continue
    }

    # Time Filter Check
    $chatDateStr = $chat.inserted_at
    if ($null -eq $chatDateStr) { $chatDateStr = $chat.updated_at }
    
    if ($chatDateStr) {
        $chatDate = [DateTime]::Parse($chatDateStr)
        if ($null -ne $filterStart -and $chatDate -lt $filterStart) {
            continue
        }
        if ($null -ne $filterEnd -and $chatDate -gt $filterEnd) {
            continue
        }
    }
    
    $includedChatsCount += 1

    foreach ($ad in $chat.ads) {
        $adId = $ad.ad_id
        if (-not $adStats.ContainsKey($adId)) {
            $adStats[$adId] = @{
                AdId = $adId
                TotalChats = 0
                PhoneLeads = 0
                Bookings = 0
                PainCost = 0
                PainSymptoms = 0
                PainFearSurgery = 0
                PainTrust = 0
                PainLocation = 0
                CustomerMessages = 0
            }
        }
        
        $stats = $adStats[$adId]
        $stats.TotalChats += 1

        $hasPhone = $false
        $hasBooking = $false
        
        $costFound = $false
        $symptomsFound = $false
        $fearSurgeryFound = $false
        $trustFound = $false
        $locationFound = $false

        foreach ($msg in $chat.messages) {
            $content = $msg.content
            if ($null -eq $content) { continue }
            
            # Clean HTML tags
            $cleanContent = $content -replace "<[^>]*>", ""
            
            # 1. Phone number check
            if ($cleanContent -match $regexPhone) {
                $hasPhone = $true
            }

            # 2. Booking check
            foreach ($kw in $bookingKeywords) {
                if ($cleanContent.ToLower().Contains($kw)) {
                    $hasBooking = $true
                    break
                }
            }

            # 3. Pain points check (customer messages only)
            $isCustomer = ($msg.sender -eq $chat.customer_name) -or ($clinicSenders -notcontains $msg.sender)
            
            if ($isCustomer) {
                $stats.CustomerMessages += 1
                $text = $cleanContent.ToLower()

                if ($text -match $painCost) { $costFound = $true }
                if ($text -match $painSymptoms) { $symptomsFound = $true }
                if ($text -match $painFearSurgery) { $fearSurgeryFound = $true }
                if ($text -match $painTrust) { $trustFound = $true }
                if ($text -match $painLocation) { $locationFound = $true }
            }
        }

        if ($hasPhone) { $stats.PhoneLeads += 1 }
        if ($hasBooking) { $stats.Bookings += 1 }
        
        if ($costFound) { $stats.PainCost += 1 }
        if ($symptomsFound) { $stats.PainSymptoms += 1 }
        if ($fearSurgeryFound) { $stats.PainFearSurgery += 1 }
        if ($trustFound) { $stats.PainTrust += 1 }
        if ($locationFound) { $stats.PainLocation += 1 }
    }
}

# Generate Markdown Report
$report = New-Object System.Text.StringBuilder
[void]$report.AppendLine($l.reportTitle)

$timeStr = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$lineTime = "{0}: {1}" -f $l.timeAnalyzed, $timeStr
[void]$report.AppendLine($lineTime)

$lineTotalChats = "{0}: {1} (Filtered: {2})" -f $l.totalChatsAnalyzed, $chats.Count, $includedChatsCount
[void]$report.AppendLine($lineTotalChats)

if ($StartDate -or $EndDate) {
    [void]$report.AppendLine("Khoang thoi gian loc: $StartDate -> $EndDate")
}
[void]$report.AppendLine()

[void]$report.AppendLine($l.section1Title)
[void]$report.AppendLine($l.section1Desc)
[void]$report.AppendLine()
[void]$report.AppendLine($l.section1Header)
[void]$report.AppendLine("|---|---|---|---|---|---|")

$sortedStats = $adStats.Values | Sort-Object TotalChats -Descending

foreach ($stats in $sortedStats) {
    if ($stats.TotalChats -lt 1) { continue } # Show all active ads in this period
    
    $phoneRate = ($stats.PhoneLeads / $stats.TotalChats) * 100
    $bookingRate = ($stats.Bookings / $stats.TotalChats) * 100
    
    $line = "| {0} | {1} | {2} | {3:N1}% | {4} | {5:N1}% |" -f $stats.AdId, $stats.TotalChats, $stats.PhoneLeads, $phoneRate, $stats.Bookings, $bookingRate
    [void]$report.AppendLine($line)
}
[void]$report.AppendLine()

[void]$report.AppendLine($l.section2Title)
[void]$report.AppendLine($l.section2Desc)
[void]$report.AppendLine()
[void]$report.AppendLine($l.section2Header)
[void]$report.AppendLine("|---|---|---|---|---|---|---|")

foreach ($stats in $sortedStats) {
    if ($stats.TotalChats -lt 1) { continue }
    
    $sympRate = ($stats.PainSymptoms / $stats.TotalChats) * 100
    $costRate = ($stats.PainCost / $stats.TotalChats) * 100
    $fearRate = ($stats.PainFearSurgery / $stats.TotalChats) * 100
    $trustRate = ($stats.PainTrust / $stats.TotalChats) * 100
    $locRate = ($stats.PainLocation / $stats.TotalChats) * 100
    
    $line = "| {0} | {1} | {2:N1}% | {3:N1}% | {4:N1}% | {5:N1}% | {6:N1}% |" -f $stats.AdId, $stats.TotalChats, $sympRate, $costRate, $fearRate, $trustRate, $locRate
    [void]$report.AppendLine($line)
}
[void]$report.AppendLine()

[void]$report.AppendLine($l.section3Title)
[void]$report.AppendLine($l.section3Desc)
[void]$report.AppendLine()

foreach ($stats in $sortedStats) {
    if ($stats.TotalChats -lt 1) { continue }
    
    $adId = $stats.AdId
    $creative = $creativesData.$adId
    
    $adName = "Unmapped"
    $adBody = "No Content"
    if ($null -ne $creative) {
        $adName = $creative.name
        $adBody = $creative.body
    }

    $phoneRate = ($stats.PhoneLeads / $stats.TotalChats) * 100
    $bookingRate = ($stats.Bookings / $stats.TotalChats) * 100
    
    $costRate = ($stats.PainCost / $stats.TotalChats) * 100
    $sympRate = ($stats.PainSymptoms / $stats.TotalChats) * 100
    $fearRate = ($stats.PainFearSurgery / $stats.TotalChats) * 100

    $lineAdHeader = "{0}: {1} ({2})" -f $l.adIdLabel, $adId, $adName
    [void]$report.AppendLine($lineAdHeader)
    [void]$report.AppendLine()
    [void]$report.AppendLine($l.adCopyLabel)
    [void]$report.AppendLine('```text')
    [void]$report.AppendLine($adBody)
    [void]$report.AppendLine('```')
    [void]$report.AppendLine()
    [void]$report.AppendLine($l.adPerformanceLabel)
    
    $lineTotal = "{0} {1}" -f $l.totalChats, $stats.TotalChats
    [void]$report.AppendLine($lineTotal)
    
    $phoneRateStr = $phoneRate.ToString("N1")
    $linePhone = "{0} {1} ({2}%)" -f $l.phoneRate, $stats.PhoneLeads, $phoneRateStr
    [void]$report.AppendLine($linePhone)
    
    $bookingRateStr = $bookingRate.ToString("N1")
    $lineBooking = "{0} {1} ({2}%)" -f $l.bookingRate, $stats.Bookings, $bookingRateStr
    [void]$report.AppendLine($lineBooking)
    
    [void]$report.AppendLine()
    [void]$report.AppendLine($l.painAnalysisLabel)
    
    $sympRateStr = $sympRate.ToString("N1")
    $lineSymp = "{0} {1}%" -f $l.sympPain, $sympRateStr
    [void]$report.AppendLine($lineSymp)
    
    $costRateStr = $costRate.ToString("N1")
    $lineCost = "{0} {1}%" -f $l.costPain, $costRateStr
    [void]$report.AppendLine($lineCost)
    
    $fearRateStr = $fearRate.ToString("N1")
    $lineSurgery = "{0} {1}%" -f $l.surgeryPain, $fearRateStr
    [void]$report.AppendLine($lineSurgery)
    
    [void]$report.AppendLine()
    [void]$report.AppendLine($l.feedbackLabel)
    
    if ($phoneRate -ge 30 -and $bookingRate -ge 15) {
        [void]$report.AppendLine("> [!TIP]")
        [void]$report.AppendLine($l.tipGood)
    } elseif ($costRate -gt 50 -and $phoneRate -lt 15) {
        [void]$report.AppendLine("> [!WARNING]")
        [void]$report.AppendLine($l.warningCost)
    } elseif ($sympRate -lt 40) {
        [void]$report.AppendLine("> [!CAUTION]")
        [void]$report.AppendLine($l.cautionSpam)
    } else {
        [void]$report.AppendLine("> [!NOTE]")
        [void]$report.AppendLine($l.noteNormal)
    }
    [void]$report.AppendLine()
    [void]$report.AppendLine("---")
    [void]$report.AppendLine()
}

$outputPath = "evaluation_report.md"
$fullPath = (Get-Item .).FullName + "/" + $outputPath
[System.IO.File]::WriteAllText($fullPath, $report.ToString(), [System.Text.Encoding]::UTF8)
Write-Host "[+] Report generated successfully at: $outputPath"
