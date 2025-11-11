# Setup Methods Comparison

Three ways to set up Dr. Chaffee AI, from simplest to most control.

---

## 🏆 Recommended: Docker

**Best for:** Everyone, especially beginners

### Pros
- ✅ **One command** - `npm run docker:setup`
- ✅ **Cross-platform** - Works on Windows, macOS, Linux
- ✅ **No dependencies** - Only Docker needed
- ✅ **Isolated** - No conflicts with other projects
- ✅ **Production-ready** - Same setup for dev and prod
- ✅ **Easy cleanup** - `docker-compose down -v`
- ✅ **Reproducible** - Exact same environment everywhere

### Cons
- ❌ Requires Docker Desktop (1GB+ download)
- ❌ Uses more disk space (~2-3GB)
- ❌ Slightly slower startup (containers need to start)

### Setup

```bash
# 1. Install Docker
winget install Docker.DockerDesktop  # Windows
brew install docker                  # macOS

# 2. Run setup
npm run docker:setup

# 3. Access app
# http://localhost:3000
```

### Daily Use

```bash
npm run docker:start    # Start
npm run docker:stop     # Stop
npm run docker:logs     # View logs
npm run docker:ingest   # Run ingestion
```

**Time:** 3-5 minutes  
**Difficulty:** ⭐ (Very Easy)

📖 **Full guide:** [DOCKER_SETUP.md](DOCKER_SETUP.md)

---

## 🔧 Alternative: NPM Scripts

**Best for:** Developers who want more control

### Pros
- ✅ Cross-platform (Windows, macOS, Linux)
- ✅ Standard npm workflow
- ✅ Direct access to code
- ✅ Faster iteration (no container rebuild)
- ✅ Uses less disk space

### Cons
- ❌ Requires Python, Node.js, Docker installed
- ❌ Potential dependency conflicts
- ❌ Platform-specific issues (especially Windows)
- ❌ Manual cleanup needed

### Setup

```bash
# 1. Install prerequisites
winget install Python.Python.3.12
winget install OpenJS.NodeJS
winget install Docker.DockerDesktop

# 2. Run setup
npm run setup

# 3. Start app
npm start
```

### Daily Use

```bash
npm start              # Start frontend + backend
npm run start:docker   # Start database only
npm run stop           # Stop everything
npm run ingest:test    # Run ingestion
```

**Time:** 5-10 minutes  
**Difficulty:** ⭐⭐ (Easy)

📖 **Full guide:** [QUICKSTART.md](QUICKSTART.md)

---

## 🛠️ Manual: PowerShell/Bash

**Best for:** Advanced users who want full control

### Pros
- ✅ Maximum control
- ✅ Can customize every step
- ✅ Understand what's happening
- ✅ Easier debugging

### Cons
- ❌ Platform-specific (PowerShell for Windows, Bash for Unix)
- ❌ Most complex
- ❌ Most time-consuming
- ❌ Requires deep knowledge

### Setup

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File setup-windows.ps1

# Unix
./setup_dev.sh
```

**Time:** 15-30 minutes  
**Difficulty:** ⭐⭐⭐ (Moderate)

📖 **Full guide:** [SETUP.md](SETUP.md)

---

## Side-by-Side Comparison

| Feature | Docker | NPM | Manual |
|---------|--------|-----|--------|
| **Setup time** | 3-5 min | 5-10 min | 15-30 min |
| **Prerequisites** | Docker only | Python + Node + Docker | All + knowledge |
| **Cross-platform** | ✅ Yes | ✅ Yes | ❌ No |
| **One command** | ✅ Yes | ✅ Yes | ❌ No |
| **Isolated** | ✅ Yes | ⚠️ Partial | ❌ No |
| **Disk space** | ~3GB | ~1GB | ~1GB |
| **Startup time** | ~30s | ~10s | ~10s |
| **Hot reload** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Production ready** | ✅ Yes | ⚠️ Partial | ❌ No |
| **Easy cleanup** | ✅ Yes | ⚠️ Partial | ❌ No |
| **Debugging** | ⚠️ Moderate | ✅ Easy | ✅ Easy |
| **Customization** | ⚠️ Moderate | ✅ Easy | ✅ Full |

---

## Recommendation by Use Case

### 👨‍💻 First-time setup
**Use Docker** - Simplest and most reliable

### 🚀 Quick demo
**Use Docker** - Fastest to get running

### 🔬 Active development
**Use NPM** - Faster iteration, easier debugging

### 🏭 Production deployment
**Use Docker** - Same environment as dev

### 📚 Learning the codebase
**Use NPM** - Direct access to code

### 🐛 Debugging issues
**Use NPM or Manual** - More visibility

### 🔧 Customizing setup
**Use Manual** - Full control

---

## Migration Between Methods

### From Manual → NPM

```bash
# Clean up manual setup
rm -rf backend/venv
rm -rf frontend/node_modules

# Use NPM
npm run setup
npm start
```

### From NPM → Docker

```bash
# Stop NPM services
npm run stop

# Use Docker
npm run docker:setup
```

### From Docker → NPM

```bash
# Stop Docker
npm run docker:stop

# Use NPM
npm run setup
npm start
```

---

## Quick Decision Guide

**Choose Docker if:**
- You want the simplest setup
- You're new to the project
- You want production-like environment
- You don't want to manage dependencies

**Choose NPM if:**
- You're actively developing
- You want faster iteration
- You need to debug code
- You're comfortable with Node.js/Python

**Choose Manual if:**
- You want full control
- You're troubleshooting issues
- You need custom configuration
- You're an advanced user

---

## Summary

| Method | Command | Time | Difficulty |
|--------|---------|------|------------|
| **Docker** ⭐ | `npm run docker:setup` | 3-5 min | Very Easy |
| **NPM** | `npm run setup` | 5-10 min | Easy |
| **Manual** | `./setup-windows.ps1` | 15-30 min | Moderate |

**Recommendation:** Start with Docker, switch to NPM if you need more control.
