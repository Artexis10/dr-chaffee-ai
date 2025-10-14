# PowerShell script to execute BGE-Small migration
# Runs all 3 phases: add column, backfill, swap & index

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "BGE-SMALL MIGRATION SCRIPT (Windows)" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

# Check if we're in the backend directory
if (-not (Test-Path "alembic.ini")) {
    Write-Host "ERROR: alembic.ini not found. Run this script from the backend/ directory." -ForegroundColor Red
    exit 1
}

# Check if .env exists
if (-not (Test-Path "../.env")) {
    Write-Host "WARNING: .env file not found in parent directory" -ForegroundColor Yellow
    Write-Host "Using .env.example as reference..." -ForegroundColor Yellow
}

# Verify DATABASE_URL is set
$dbUrl = $env:DATABASE_URL
if (-not $dbUrl) {
    Write-Host "ERROR: DATABASE_URL environment variable not set" -ForegroundColor Red
    Write-Host "Please set DATABASE_URL in your .env file or environment" -ForegroundColor Red
    exit 1
}

Write-Host "Step 1: Running Alembic migrations (005 -> 007)" -ForegroundColor Green
Write-Host "This will:" -ForegroundColor Yellow
Write-Host "  - Add embedding_384 column (Phase 1)" -ForegroundColor Yellow
Write-Host "  - Backfill embeddings with BGE-Small (Phase 2)" -ForegroundColor Yellow
Write-Host "  - Swap columns and rebuild index (Phase 3)" -ForegroundColor Yellow
Write-Host ""

$response = Read-Host "Continue? (y/n)"
if ($response -ne "y") {
    Write-Host "Migration cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Running: alembic upgrade head" -ForegroundColor Cyan
alembic upgrade head

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Migration failed!" -ForegroundColor Red
    Write-Host "Check the error messages above for details." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 79) -ForegroundColor Green
Write-Host "MIGRATION COMPLETE!" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 79) -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Running embedding speed benchmark" -ForegroundColor Green
Write-Host ""

$response = Read-Host "Run benchmark? (y/n)"
if ($response -eq "y") {
    Write-Host ""
    Write-Host "Running: python scripts/test_embedding_speed.py" -ForegroundColor Cyan
    python scripts/test_embedding_speed.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "WARNING: Benchmark failed or had errors" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 79) -ForegroundColor Green
Write-Host "ALL DONE!" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 79) -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Update application code to use EmbeddingsService" -ForegroundColor White
Write-Host "  2. Test semantic search queries" -ForegroundColor White
Write-Host "  3. Monitor embedding generation performance" -ForegroundColor White
Write-Host ""
Write-Host "To run tests:" -ForegroundColor Cyan
Write-Host "  pytest tests/embeddings/ -v" -ForegroundColor White
Write-Host "  pytest tests/db/ -v" -ForegroundColor White
Write-Host "  pytest tests/migrations/ -v" -ForegroundColor White
Write-Host ""
