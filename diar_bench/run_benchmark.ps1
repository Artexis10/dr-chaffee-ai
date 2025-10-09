Param(
    [string]$Source = "https://www.youtube.com/watch?v=1oKru2X3AvU",
    [switch]$TryFsEend = $true,
    [int]$Seconds = 120
)

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "Diarization Benchmark Runner" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source: $Source" -ForegroundColor Yellow
Write-Host "Seconds: $Seconds" -ForegroundColor Yellow
Write-Host "Try FS-EEND: $TryFsEend" -ForegroundColor Yellow
Write-Host ""

# Use parent project's venv
$parentVenv = "..\backend\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $parentVenv)) {
    $parentVenv = "..\.venv\Scripts\Activate.ps1"
}

if (Test-Path $parentVenv) {
    Write-Host "Activating parent project's virtual environment..." -ForegroundColor Green
    & $parentVenv
} else {
    Write-Host "ERROR: Parent virtual environment not found!" -ForegroundColor Red
    Write-Host "Looked for: ..\.venv or ..\backend\.venv" -ForegroundColor Red
    exit 1
}

# Build command
$cmd = "python .\benchmark_diarizers.py --source `"$Source`" --seconds $Seconds"
if ($TryFsEend) {
    $cmd += " --try-fs-eend"
}

Write-Host "Running: $cmd" -ForegroundColor Green
Write-Host ""

# Run benchmark
Invoke-Expression $cmd

# Find latest run directory
$latestRun = Get-ChildItem -Path ".\runs" -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if ($latestRun) {
    $summaryPath = Join-Path $latestRun.FullName "SUMMARY.md"
    
    if (Test-Path $summaryPath) {
        Write-Host ""
        Write-Host "==============================================================" -ForegroundColor Cyan
        Write-Host "Opening SUMMARY.md..." -ForegroundColor Cyan
        Write-Host "==============================================================" -ForegroundColor Cyan
        
        # Open in default editor
        Start-Process $summaryPath
    }
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
