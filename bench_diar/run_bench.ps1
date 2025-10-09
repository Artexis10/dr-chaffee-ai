Param(
    [string]$Source = "https://www.youtube.com/watch?v=1oKru2X3AvU",
    [int]$Seconds = 120,
    [switch]$IncludeE2E = $false,
    [switch]$IncludeNeMo = $false
)

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "Diarization Benchmark (Ingest Integration)" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source: $Source" -ForegroundColor Yellow
Write-Host "Seconds: $Seconds" -ForegroundColor Yellow
Write-Host ""

# Build command
$cmd = "python .\bench_diar\bench_from_ingest.py --source `"$Source`" --seconds $Seconds"
if ($IncludeE2E) {
    $cmd += " --include-e2e"
    Write-Host "Including FS-EEND (E2E)" -ForegroundColor Yellow
}
if ($IncludeNeMo) {
    $cmd += " --include-nemo"
    Write-Host "Including NeMo Sortformer (E2E)" -ForegroundColor Yellow
}

# Run benchmark
Invoke-Expression $cmd

# Open SUMMARY.md
$latestRun = Get-ChildItem -Path ".\bench_diar\runs" -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if ($latestRun) {
    $summaryPath = Join-Path $latestRun.FullName "SUMMARY.md"
    
    if (Test-Path $summaryPath) {
        Write-Host ""
        Write-Host "==============================================================" -ForegroundColor Cyan
        Write-Host "Opening SUMMARY.md..." -ForegroundColor Cyan
        Write-Host "==============================================================" -ForegroundColor Cyan
        
        Start-Process $summaryPath
    }
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
