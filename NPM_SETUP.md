# NPM-Based Setup (Better Approach)

## Why NPM Instead of PowerShell?

**Advantages:**
- ✅ **Cross-platform** - Works on Windows, macOS, Linux
- ✅ **Standard** - npm is the standard package manager for Node projects
- ✅ **Portable** - No platform-specific scripts needed
- ✅ **Maintainable** - JavaScript is easier to understand than PowerShell
- ✅ **Composable** - Can chain commands easily
- ✅ **Familiar** - Developers already know npm scripts

**Before (PowerShell only):**
```powershell
powershell -ExecutionPolicy Bypass -File setup-windows.ps1
```

**After (Universal):**
```bash
npm run setup
```

Works on Windows, macOS, and Linux!

---

## Setup Scripts Created

### 1. `scripts/setup.js`
Main setup orchestrator that:
- Checks prerequisites (Python, Node.js, Docker)
- Creates .env file
- Runs backend setup
- Runs frontend setup
- Starts Docker containers
- Creates convenience scripts

**Run with:** `npm run setup`

### 2. `scripts/setup-backend.js`
Backend-specific setup that:
- Creates Python virtual environment
- Installs Python dependencies
- Handles compilation issues

**Run with:** `npm run setup:backend`

### 3. Updated `package.json`
Added npm scripts for all common tasks:
- `npm run setup` - One-command setup
- `npm start` - Start everything
- `npm run start:frontend` - Start frontend only
- `npm run start:backend` - Start backend only
- `npm run start:docker` - Start database only
- `npm run stop` - Stop everything
- `npm run ingest` - Ingest all videos
- `npm run ingest:test` - Ingest 10 test videos
- `npm run db:reset` - Reset database
- `npm run db:status` - Check database status

---

## New Setup Flow

### First Time (5 minutes)

```bash
# 1. Install prerequisites (if needed)
# Windows:
winget install Python.Python.3.12
winget install OpenJS.NodeJS
winget install Docker.DockerDesktop

# macOS:
brew install python@3.12
brew install node
brew install docker

# Linux:
sudo apt-get install python3.12 nodejs docker.io

# 2. Run setup
npm run setup

# 3. Edit .env with API keys
# Add YOUTUBE_API_KEY

# 4. Start the app
npm start
```

### Daily Usage

```bash
# Start
npm start

# Stop
npm stop

# Ingest test data
npm run ingest:test
```

---

## Comparison: Old vs New

### Old (PowerShell)
```powershell
powershell -ExecutionPolicy Bypass -File setup-windows.ps1
.\start.ps1
.\stop.ps1
backend\venv\Scripts\python.exe backend\scripts\ingest_youtube.py --limit 10
```

### New (npm)
```bash
npm run setup
npm start
npm stop
npm run ingest:test
```

**Much simpler and cross-platform!**

---

## Benefits

### For Users
- One command to setup everything
- Works on any OS
- Clear error messages
- Easy to remember commands

### For Developers
- Standard npm scripts
- Easy to add new commands
- JavaScript is more portable than PowerShell
- Can be extended easily

### For CI/CD
- Can run `npm run setup` in Docker
- Can run `npm test` for testing
- Can run `npm run build` for production

---

## Migration from PowerShell

If you have the old PowerShell setup:

```bash
# 1. Delete old scripts (optional)
rm setup-windows.ps1
rm start.ps1
rm stop.ps1

# 2. Run new setup
npm run setup

# 3. Use new commands
npm start
npm stop
```

---

## File Structure

```
dr-chaffee-ai/
├── scripts/
│   ├── setup.js              # Main setup orchestrator
│   └── setup-backend.js      # Backend setup
├── package.json              # npm scripts
├── QUICKSTART.md             # Quick start guide
├── TROUBLESHOOTING.md        # Common issues
└── README.md                 # Updated with npm commands
```

---

## Future Improvements

### Possible npm Scripts

```bash
# Development
npm run dev              # Start with hot reload
npm run lint            # Lint code
npm run format          # Format code

# Production
npm run build           # Build for production
npm run start:prod      # Start production build

# Maintenance
npm run migrate         # Run database migrations
npm run seed           # Seed database with test data
npm run backup         # Backup database
npm run restore        # Restore database

# Monitoring
npm run logs           # Show all logs
npm run health         # Check system health
npm run stats          # Show ingestion stats
```

---

## Troubleshooting npm Scripts

### "npm: command not found"
Install Node.js: https://nodejs.org/

### "npm run setup" fails
Check prerequisites:
```bash
python --version
node --version
docker --version
```

### "Permission denied"
On macOS/Linux, make scripts executable:
```bash
chmod +x scripts/setup.js
chmod +x scripts/setup-backend.js
```

---

## Summary

**Old approach:** Platform-specific PowerShell script
**New approach:** Universal npm scripts

**Result:** Same functionality, better portability, easier maintenance!
