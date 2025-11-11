# Docker Setup (Recommended)

The **simplest and most reliable** way to run Dr. Chaffee AI.

## Why Docker?

✅ **One command** - Everything runs in containers  
✅ **Cross-platform** - Works on Windows, macOS, Linux  
✅ **Isolated** - No dependency conflicts  
✅ **Reproducible** - Same environment everywhere  
✅ **No manual setup** - No Python venv, no npm install  
✅ **Production-ready** - Same setup for dev and prod  

---

## Quick Start (3 minutes)

### 1. Install Docker

```bash
# Windows
winget install Docker.DockerDesktop

# macOS
brew install docker

# Linux
sudo apt-get install docker.io docker-compose
```

Start Docker Desktop and wait for it to be ready.

### 2. One-Command Setup

```bash
# Option 1: Using script (recommended)
./docker-setup.sh          # macOS/Linux
.\docker-setup.ps1         # Windows

# Option 2: Using npm
npm run docker:setup

# Option 3: Direct docker-compose
docker-compose -f docker-compose.dev.yml up -d --build
```

### 3. Edit .env

Add your YouTube API key:
```env
YOUTUBE_API_KEY=your_key_here
```

### 4. Access the App

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## What Gets Started?

The Docker setup starts **4 containers**:

1. **PostgreSQL** (with pgvector) - Database
2. **Redis** - Cache and task queue
3. **Backend** - Python FastAPI server
4. **Frontend** - Next.js web app

All connected and ready to use!

---

## Common Commands

### Using npm scripts (easiest)

```bash
# Start everything
npm run docker:start

# Stop everything
npm run docker:stop

# View logs
npm run docker:logs

# Restart services
npm run docker:restart

# Reset database (deletes all data)
npm run docker:reset

# Run ingestion (10 test videos)
npm run docker:ingest
```

### Using docker-compose directly

```bash
# Start
docker-compose -f docker-compose.dev.yml up -d

# Stop
docker-compose -f docker-compose.dev.yml down

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# View specific service logs
docker-compose -f docker-compose.dev.yml logs -f frontend
docker-compose -f docker-compose.dev.yml logs -f backend

# Restart a service
docker-compose -f docker-compose.dev.yml restart backend

# Rebuild and restart
docker-compose -f docker-compose.dev.yml up -d --build

# Execute command in container
docker-compose -f docker-compose.dev.yml exec backend python scripts/ingest_youtube.py --limit 10

# Check status
docker-compose -f docker-compose.dev.yml ps

# Stop and remove volumes (reset everything)
docker-compose -f docker-compose.dev.yml down -v
```

---

## Development Workflow

### Making Code Changes

**Frontend changes:**
- Edit files in `frontend/`
- Hot reload is automatic
- See changes immediately at http://localhost:3000

**Backend changes:**
- Edit files in `backend/`
- Server auto-reloads
- API updates immediately at http://localhost:8000

### Running Ingestion

```bash
# Test with 10 videos
npm run docker:ingest

# Or full ingestion
docker-compose -f docker-compose.dev.yml exec backend python scripts/ingest_youtube.py

# With specific options
docker-compose -f docker-compose.dev.yml exec backend python scripts/ingest_youtube.py --source api --limit 50
```

### Accessing Database

```bash
# Connect to PostgreSQL
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d askdrchaffee

# Run SQL query
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d askdrchaffee -c "SELECT COUNT(*) FROM segments;"

# Backup database
docker-compose -f docker-compose.dev.yml exec postgres pg_dump -U postgres askdrchaffee > backup.sql

# Restore database
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres askdrchaffee < backup.sql
```

---

## Troubleshooting

### Port already in use

```bash
# Find what's using the port
# Windows
netstat -ano | findstr :3000

# macOS/Linux
lsof -i :3000

# Kill the process or change port in docker-compose.dev.yml
```

### Container won't start

```bash
# Check logs
docker-compose -f docker-compose.dev.yml logs backend

# Check container status
docker-compose -f docker-compose.dev.yml ps

# Rebuild from scratch
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d --build
```

### Out of disk space

```bash
# Clean up Docker
docker system prune -a --volumes

# Remove old images
docker image prune -a

# Remove stopped containers
docker container prune
```

### Database connection errors

```bash
# Check if database is healthy
docker-compose -f docker-compose.dev.yml ps

# Restart database
docker-compose -f docker-compose.dev.yml restart postgres

# Reset database
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

---

## Comparison: Docker vs Manual Setup

| Aspect | Manual Setup | Docker Setup |
|--------|--------------|--------------|
| **Setup time** | 15-30 minutes | 3-5 minutes |
| **Commands** | Multiple steps | One command |
| **Dependencies** | Manual install | Automatic |
| **Consistency** | Varies by system | Always same |
| **Cleanup** | Manual | `docker-compose down` |
| **Portability** | OS-specific | Works anywhere |
| **Production** | Different setup | Same as dev |

---

## Production Deployment

The same Docker setup works for production:

```bash
# Build for production
docker-compose -f docker-compose.prod.yml up -d --build

# Or deploy to cloud
# - AWS ECS
# - Google Cloud Run
# - Azure Container Instances
# - DigitalOcean App Platform
# - Render
# - Fly.io
```

---

## File Structure

```
dr-chaffee-ai/
├── docker-compose.dev.yml      # Development setup (all services)
├── docker-compose.yml          # Production setup (backend only)
├── Dockerfile                  # Backend container
├── frontend/
│   └── Dockerfile.dev          # Frontend container (dev)
├── docker-setup.sh             # Setup script (Unix)
├── docker-setup.ps1            # Setup script (Windows)
└── .env                        # Configuration
```

---

## Advanced Usage

### Custom Configuration

Edit `docker-compose.dev.yml` to:
- Change ports
- Add environment variables
- Mount additional volumes
- Add new services

### Multi-stage Builds

The Dockerfile uses multi-stage builds for:
- Smaller image size
- Faster builds
- Better caching

### Health Checks

All services have health checks:
- Database: `pg_isready`
- Redis: `redis-cli ping`
- Backend: HTTP health endpoint
- Frontend: Process running

### Networking

All containers are on the same network:
- Services can communicate by name
- Frontend → Backend: `http://backend:8000`
- Backend → Database: `postgresql://postgres:5432`

---

## Summary

**Docker is the recommended way to run Dr. Chaffee AI:**

```bash
# Setup (once)
npm run docker:setup

# Daily use
npm run docker:start    # Start
npm run docker:stop     # Stop
npm run docker:logs     # View logs
npm run docker:ingest   # Run ingestion
```

**That's it!** No Python, no Node.js, no manual dependency management.
