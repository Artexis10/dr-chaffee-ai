# Quick Start Guide

Get the Dr. Chaffee AI app running in **under 5 minutes**.

## Prerequisites

Install these three things (if not already installed):

```bash
# Windows
winget install Python.Python.3.12
winget install OpenJS.NodeJS
winget install Docker.DockerDesktop

# macOS
brew install python@3.12
brew install node
brew install docker

# Linux (Ubuntu/Debian)
sudo apt-get install python3.12 nodejs docker.io
```

**After installing, restart your terminal.**

## One-Command Setup

```bash
npm run setup
```

That's it! The script will:
- ✓ Check prerequisites
- ✓ Create Python virtual environment
- ✓ Install all Python dependencies
- ✓ Install all Node.js dependencies
- ✓ Create .env file
- ✓ Start Docker containers

## Configure API Keys

Edit `.env` and add your YouTube API key:

```env
YOUTUBE_API_KEY=your_key_here
```

Get a free API key: https://console.cloud.google.com/apis/credentials

## Start the App

```bash
npm start
```

This starts:
- PostgreSQL database (Docker)
- Redis cache (Docker)
- Frontend dev server (http://localhost:3000)
- Backend API server (http://localhost:8000)

## Ingest Test Data

```bash
npm run ingest:test
```

This ingests 10 videos for testing.

## Stop the App

```bash
npm run stop
```

---

## Troubleshooting

### Docker not running?

Start Docker Desktop manually, then run:
```bash
npm run start:docker
```

### Python dependencies failing?

Try installing manually:
```bash
npm run setup:backend
```

### Frontend not starting?

```bash
npm run setup:frontend
npm run start:frontend
```

---

## Full Documentation

For detailed setup, deployment, and configuration:
- [README.md](README.md) - Full documentation
- [SETUP.md](SETUP.md) - Detailed setup guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and fixes

---

## Common Commands

```bash
# Setup (one-time)
npm run setup

# Start everything
npm start

# Start just frontend
npm run start:frontend

# Start just backend
npm run start:backend

# Start just database
npm run start:docker

# Stop everything
npm run stop

# Ingest 10 videos (test)
npm run ingest:test

# Ingest all videos
npm run ingest

# Check database status
npm run db:status

# Reset database (WARNING: deletes all data)
npm run db:reset

# Run tests
npm test
```

---

## Project Structure

```
dr-chaffee-ai/
├── frontend/          # Next.js web app
├── backend/           # Python ingestion pipeline
│   ├── scripts/       # Ingestion scripts
│   └── venv/          # Python virtual environment
├── .env               # Configuration (API keys)
├── docker-compose.yml # Database setup
├── setup-windows.ps1  # One-command setup
├── start.ps1          # Start app
└── stop.ps1           # Stop app
```

---

## Need Help?

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review [README.md](README.md)
3. Check GitHub issues
