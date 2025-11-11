#!/bin/bash
# One-command Docker setup for Dr. Chaffee AI

set -e

echo "=========================================="
echo "  Dr. Chaffee AI - Docker Setup"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo ""
    echo "Install Docker:"
    echo "  Windows: winget install Docker.DockerDesktop"
    echo "  macOS:   brew install docker"
    echo "  Linux:   sudo apt-get install docker.io docker-compose"
    exit 1
fi

echo "✓ Docker found"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ Created .env file"
        echo "⚠️  Please edit .env and add your YOUTUBE_API_KEY"
        echo ""
    else
        echo "❌ .env.example not found"
        exit 1
    fi
else
    echo "✓ .env file exists"
    echo ""
fi

# Build and start all services
echo "Building and starting services..."
echo "This may take a few minutes on first run..."
echo ""

docker-compose -f docker-compose.dev.yml up -d --build

echo ""
echo "=========================================="
echo "  ✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Services running:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  Database:  localhost:5432"
echo "  Redis:     localhost:6379"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your YOUTUBE_API_KEY"
echo "  2. Run ingestion:"
echo "     docker-compose -f docker-compose.dev.yml exec backend python scripts/ingest_youtube.py --limit 10"
echo ""
echo "Common commands:"
echo "  View logs:  docker-compose -f docker-compose.dev.yml logs -f"
echo "  Stop:       docker-compose -f docker-compose.dev.yml down"
echo "  Restart:    docker-compose -f docker-compose.dev.yml restart"
echo "  Reset DB:   docker-compose -f docker-compose.dev.yml down -v"
echo ""
