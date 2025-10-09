# Test Runner for Dr. Chaffee AI
# Runs unit and integration tests with coverage reporting

Param(
    [switch]$Unit = $false,
    [switch]$Integration = $false,
    [switch]$Coverage = $false,
    [switch]$Verbose = $false,
    [string]$TestFile = ""
)

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "Dr. Chaffee AI - Test Runner" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""

# Default: run all tests if no flags specified
if (-not $Unit -and -not $Integration -and -not $TestFile) {
    $Unit = $true
    $Integration = $true
}

$testArgs = @()

# Add test paths
if ($TestFile) {
    $testArgs += $TestFile
} else {
    if ($Unit) {
        $testArgs += "tests/unit"
        Write-Host "[Unit Tests] Enabled" -ForegroundColor Green
    }
    if ($Integration) {
        $testArgs += "tests/integration"
        Write-Host "[Integration Tests] Enabled" -ForegroundColor Green
    }
}

# Add verbosity
if ($Verbose) {
    $testArgs += "-v"
    $testArgs += "-s"
    Write-Host "[Verbose Mode] Enabled" -ForegroundColor Yellow
}

# Add coverage
if ($Coverage) {
    $testArgs += "--cov=backend/scripts"
    $testArgs += "--cov-report=html"
    $testArgs += "--cov-report=term"
    Write-Host "[Coverage] Enabled" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Running tests..." -ForegroundColor Cyan
Write-Host "Command: pytest $($testArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

# Run pytest
python -m pytest @testArgs

$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "Tests PASSED" -ForegroundColor Green
} else {
    Write-Host "Tests FAILED" -ForegroundColor Red
}
Write-Host "==============================================================" -ForegroundColor Cyan

if ($Coverage -and $exitCode -eq 0) {
    Write-Host ""
    Write-Host "Coverage report generated: htmlcov/index.html" -ForegroundColor Yellow
    $openReport = Read-Host "Open coverage report? (y/n)"
    if ($openReport -eq 'y') {
        Start-Process "htmlcov/index.html"
    }
}

exit $exitCode
