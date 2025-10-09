Param([switch]$Recreate)

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "E2E Models Sub-Environment Setup" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan

$venvPath = ".\.e2e_venv"

if ($Recreate -and (Test-Path $venvPath)) {
    Write-Host "Recreating sub-venv..." -ForegroundColor Yellow
    Remove-Item $venvPath -Recurse -Force
}

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating sub-venv with --system-site-packages..." -ForegroundColor Green
    python -m venv $venvPath --system-site-packages
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create venv!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Activating sub-venv..." -ForegroundColor Green
& "$venvPath\Scripts\Activate.ps1"

Write-Host "Upgrading pip..." -ForegroundColor Green
python -m pip install -U pip -q

Write-Host "" -ForegroundColor Green
Write-Host "✓ E2E sub-venv ready" -ForegroundColor Green
Write-Host "  Location: $venvPath" -ForegroundColor Gray
Write-Host "  Inherits: torch, torchaudio, numpy, etc. from main env" -ForegroundColor Gray
Write-Host "==============================================================" -ForegroundColor Cyan
