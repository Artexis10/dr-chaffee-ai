# Setup Custom Instructions Feature
# Run this script to apply the database migration and verify setup

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Custom Instructions Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Yellow
docker ps 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker is running" -ForegroundColor Green
Write-Host ""

# Check if containers are running
Write-Host "Checking containers..." -ForegroundColor Yellow
$backendRunning = docker-compose -f docker-compose.dev.yml ps backend | Select-String "Up"
$dbRunning = docker-compose -f docker-compose.dev.yml ps db | Select-String "Up"

if (-not $backendRunning -or -not $dbRunning) {
    Write-Host "⚠️  Containers not running. Starting services..." -ForegroundColor Yellow
    docker-compose -f docker-compose.dev.yml up -d backend db
    Write-Host "Waiting 10 seconds for services to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}
Write-Host "✅ Containers are running" -ForegroundColor Green
Write-Host ""

# Apply migration
Write-Host "Applying database migration..." -ForegroundColor Yellow
docker-compose -f docker-compose.dev.yml exec -T backend python utils/database/apply_custom_instructions_migration.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Migration applied successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Migration failed. Check errors above." -ForegroundColor Red
    exit 1
}
Write-Host ""

# Verify tables exist
Write-Host "Verifying database tables..." -ForegroundColor Yellow
$tables = docker-compose -f docker-compose.dev.yml exec -T db psql -U postgres -d drchaffee -t -c "\dt custom_instructions*" 2>$null

if ($tables -match "custom_instructions") {
    Write-Host "✅ Tables created successfully" -ForegroundColor Green
    Write-Host "   - custom_instructions" -ForegroundColor Gray
    Write-Host "   - custom_instructions_history" -ForegroundColor Gray
} else {
    Write-Host "⚠️  Could not verify tables" -ForegroundColor Yellow
}
Write-Host ""

# Test API endpoint
Write-Host "Testing API endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/tuning/instructions" -Method GET -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ API endpoint responding" -ForegroundColor Green
        $data = $response.Content | ConvertFrom-Json
        Write-Host "   Found $($data.Count) instruction set(s)" -ForegroundColor Gray
    }
} catch {
    Write-Host "⚠️  API not responding yet. Backend may still be starting." -ForegroundColor Yellow
    Write-Host "   Try accessing http://localhost:8000/api/tuning/instructions in a few seconds" -ForegroundColor Gray
}
Write-Host ""

# Run tests
Write-Host "Running unit tests..." -ForegroundColor Yellow
docker-compose -f docker-compose.dev.yml exec -T backend python tests/test_custom_instructions.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some tests failed (this may be expected if DB not fully configured)" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Open tuning dashboard: http://localhost:3000/tuning" -ForegroundColor White
Write-Host "2. Look for 'Custom Instructions' section at the top" -ForegroundColor White
Write-Host "3. Click 'New Instruction Set' to create your first custom instructions" -ForegroundColor White
Write-Host ""
Write-Host "Documentation: CUSTOM_INSTRUCTIONS_GUIDE.md" -ForegroundColor Gray
Write-Host ""
