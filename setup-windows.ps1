# Dr. Chaffee AI - One-Command Windows Setup
# Run with: powershell -ExecutionPolicy Bypass -File setup-windows.ps1

param(
    [switch]$SkipDocker,
    [switch]$SkipDependencies
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Dr. Chaffee AI - Windows Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if command exists
function Test-Command {
    param($Command)
    try {
        if (Get-Command $Command -ErrorAction Stop) {
            return $true
        }
    }
    catch {
        return $false
    }
}

# Step 1: Check prerequisites
Write-Host "Step 1: Checking prerequisites..." -ForegroundColor Yellow
Write-Host ""

$missingDeps = @()

if (-not (Test-Command "python")) {
    $missingDeps += "Python 3.8+"
}
else {
    $pythonVersion = python --version
    Write-Host "  ✓ Python found: $pythonVersion" -ForegroundColor Green
}

if (-not (Test-Command "node")) {
    $missingDeps += "Node.js 20.x"
}
else {
    $nodeVersion = node --version
    Write-Host "  ✓ Node.js found: $nodeVersion" -ForegroundColor Green
}

if (-not (Test-Command "docker") -and -not $SkipDocker) {
    $missingDeps += "Docker Desktop"
}
elseif (-not $SkipDocker) {
    Write-Host "  ✓ Docker found" -ForegroundColor Green
}

if ($missingDeps.Count -gt 0) {
    Write-Host ""
    Write-Host "  ✗ Missing dependencies:" -ForegroundColor Red
    foreach ($dep in $missingDeps) {
        Write-Host "    - $dep" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Install missing dependencies:" -ForegroundColor Yellow
    Write-Host "  Python:  winget install Python.Python.3.12" -ForegroundColor White
    Write-Host "  Node.js: winget install OpenJS.NodeJS" -ForegroundColor White
    Write-Host "  Docker:  winget install Docker.DockerDesktop" -ForegroundColor White
    Write-Host ""
    Write-Host "After installing, restart PowerShell and run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 2: Create .env file
Write-Host "Step 2: Setting up environment file..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  ✓ Created .env file" -ForegroundColor Green
    Write-Host "  ⚠ IMPORTANT: Edit .env and add your API keys!" -ForegroundColor Yellow
}
else {
    Write-Host "  ✓ .env file already exists" -ForegroundColor Green
}

Write-Host ""

# Step 3: Install backend dependencies
Write-Host "Step 3: Installing backend dependencies..." -ForegroundColor Yellow

if (-not (Test-Path "backend\venv")) {
    Write-Host "  Creating Python virtual environment..." -ForegroundColor Cyan
    python -m venv backend\venv
}

Write-Host "  Installing Python packages (this may take a few minutes)..." -ForegroundColor Cyan

# Create a simplified requirements file that avoids compilation issues
$simplifiedReqs = @"
# Core dependencies
psycopg2-binary>=2.9.9
alembic>=1.13.0
sqlalchemy>=2.0.07
python-dotenv==1.0.0
numpy>=2.0.0
tqdm==4.66.1

# Web API
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
aiofiles==23.2.1
celery==5.3.4
redis==5.0.1

# YouTube
youtube-transcript-api==0.6.1
yt-dlp>=2023.11.16
google-api-python-client==2.108.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.1.0

# ML/AI (CPU versions)
sentence-transformers>=2.7.0
transformers>=4.41.0
torch>=2.2.0
torchaudio>=2.2.0

# Audio processing
psutil>=5.9.0
soundfile>=0.13.1
webvtt-py>=0.5.1

# Utilities
isodate==0.6.1
asyncio-throttle==1.0.2
apscheduler==3.10.4
aiohttp==3.9.1
aiohttp-socks==0.8.4

# Development
black==23.9.1
ruff==0.0.292
beautifulsoup4>=4.12.0
lxml>=4.9.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.1
pytest-asyncio>=0.21.1
pytest-timeout>=2.1.0
freezegun>=1.2.2
hypothesis>=6.82.0
"@

$simplifiedReqs | Out-File -FilePath "backend\requirements-simple.txt" -Encoding UTF8

try {
    & backend\venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    & backend\venv\Scripts\python.exe -m pip install -r backend\requirements-simple.txt --quiet
    Write-Host "  ✓ Backend dependencies installed" -ForegroundColor Green
}
catch {
    Write-Host "  ✗ Error installing backend dependencies" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Try running manually:" -ForegroundColor Yellow
    Write-Host "    backend\venv\Scripts\python.exe -m pip install -r backend\requirements-simple.txt" -ForegroundColor White
    exit 1
}

Write-Host ""

# Step 4: Install frontend dependencies
Write-Host "Step 4: Installing frontend dependencies..." -ForegroundColor Yellow

try {
    Push-Location frontend
    npm install --silent 2>&1 | Out-Null
    Pop-Location
    Write-Host "  ✓ Frontend dependencies installed" -ForegroundColor Green
}
catch {
    Pop-Location
    Write-Host "  ✗ Error installing frontend dependencies" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 5: Start Docker (if not skipped)
if (-not $SkipDocker) {
    Write-Host "Step 5: Starting Docker containers..." -ForegroundColor Yellow
    
    # Check if Docker is running
    $dockerRunning = $false
    try {
        docker info 2>&1 | Out-Null
        $dockerRunning = $true
    }
    catch {
        Write-Host "  ⚠ Docker Desktop is not running" -ForegroundColor Yellow
        Write-Host "  Please start Docker Desktop manually, then run:" -ForegroundColor Yellow
        Write-Host "    docker-compose up -d" -ForegroundColor White
    }
    
    if ($dockerRunning) {
        try {
            docker-compose up -d
            Write-Host "  ✓ Docker containers started" -ForegroundColor Green
            Write-Host "  Waiting for database to be ready..." -ForegroundColor Cyan
            Start-Sleep -Seconds 10
        }
        catch {
            Write-Host "  ✗ Error starting Docker containers" -ForegroundColor Red
            Write-Host "  Error: $_" -ForegroundColor Red
        }
    }
}
else {
    Write-Host "Step 5: Skipping Docker setup (--SkipDocker flag)" -ForegroundColor Yellow
}

Write-Host ""

# Step 6: Create quick start scripts
Write-Host "Step 6: Creating quick start scripts..." -ForegroundColor Yellow

# Create start script
$startScript = @"
# Quick Start Script
Write-Host "Starting Dr. Chaffee AI..." -ForegroundColor Cyan

# Start database
Write-Host "Starting database..." -ForegroundColor Yellow
docker-compose up -d

# Wait for database
Start-Sleep -Seconds 5

# Start frontend in new window
Write-Host "Starting frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host ""
Write-Host "✓ Services starting!" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend will be available at: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run ingestion:" -ForegroundColor Yellow
Write-Host "  backend\venv\Scripts\python.exe backend\scripts\ingest_youtube.py --limit 10" -ForegroundColor White
"@

$startScript | Out-File -FilePath "start.ps1" -Encoding UTF8

# Create stop script
$stopScript = @"
# Stop Script
Write-Host "Stopping Dr. Chaffee AI..." -ForegroundColor Cyan
docker-compose down
Write-Host "✓ Services stopped" -ForegroundColor Green
"@

$stopScript | Out-File -FilePath "stop.ps1" -Encoding UTF8

Write-Host "  ✓ Created start.ps1 and stop.ps1" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✓ Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Edit .env file with your API keys:" -ForegroundColor White
Write-Host "   - YOUTUBE_API_KEY (required for ingestion)" -ForegroundColor Gray
Write-Host "   - OPENAI_API_KEY (optional, for answer mode)" -ForegroundColor Gray
Write-Host "   - DATABASE_URL (already set for local Docker)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Start the application:" -ForegroundColor White
Write-Host "   .\start.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Run test ingestion (10 videos):" -ForegroundColor White
Write-Host "   backend\venv\Scripts\python.exe backend\scripts\ingest_youtube.py --limit 10" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Access the app:" -ForegroundColor White
Write-Host "   http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop everything:" -ForegroundColor White
Write-Host "   .\stop.ps1" -ForegroundColor Cyan
Write-Host ""
