# One-command Docker setup for Dr. Chaffee AI (Windows)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Dr. Chaffee AI - Docker Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
try {
    docker --version | Out-Null
    Write-Host "✓ Docker found" -ForegroundColor Green
}
catch {
    Write-Host "✗ Docker is not installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Docker:" -ForegroundColor Yellow
    Write-Host "  winget install Docker.DockerDesktop" -ForegroundColor White
    exit 1
}

# Check if Docker is running
try {
    docker info 2>&1 | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
}
catch {
    Write-Host "✗ Docker is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Create .env if it doesn't exist
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✓ Created .env file" -ForegroundColor Green
        Write-Host "⚠  Please edit .env and add your YOUTUBE_API_KEY" -ForegroundColor Yellow
        Write-Host ""
    }
    else {
        Write-Host "✗ .env.example not found" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "✓ .env file exists" -ForegroundColor Green
    Write-Host ""
}

# Build and start all services
Write-Host "Building and starting services..." -ForegroundColor Cyan
Write-Host "This may take a few minutes on first run..." -ForegroundColor Gray
Write-Host ""

docker-compose -f docker-compose.dev.yml up -d --build

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  ✓ Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services running:" -ForegroundColor Yellow
Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  Database:  localhost:5432" -ForegroundColor White
Write-Host "  Redis:     localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Edit .env and add your YOUTUBE_API_KEY" -ForegroundColor White
Write-Host "  2. Run ingestion:" -ForegroundColor White
Write-Host "     docker-compose -f docker-compose.dev.yml exec backend python scripts/ingest_youtube.py --limit 10" -ForegroundColor Cyan
Write-Host ""
Write-Host "Common commands:" -ForegroundColor Yellow
Write-Host "  View logs:  docker-compose -f docker-compose.dev.yml logs -f" -ForegroundColor Gray
Write-Host "  Stop:       docker-compose -f docker-compose.dev.yml down" -ForegroundColor Gray
Write-Host "  Restart:    docker-compose -f docker-compose.dev.yml restart" -ForegroundColor Gray
Write-Host "  Reset DB:   docker-compose -f docker-compose.dev.yml down -v" -ForegroundColor Gray
Write-Host ""
