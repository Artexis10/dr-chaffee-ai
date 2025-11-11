#!/usr/bin/env node

/**
 * Backend setup script
 * Creates virtual environment and installs Python dependencies
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const os = require('os');

const isWindows = os.platform() === 'win32';
const backendDir = path.join(process.cwd(), 'backend');
const venvDir = path.join(backendDir, 'venv');
const pythonExe = isWindows
  ? path.join(venvDir, 'Scripts', 'python.exe')
  : path.join(venvDir, 'bin', 'python');
const pipExe = isWindows
  ? path.join(venvDir, 'Scripts', 'pip.exe')
  : path.join(venvDir, 'bin', 'pip');

function log(message) {
  console.log(message);
}

function runCommand(command, cwd = process.cwd()) {
  try {
    execSync(command, { cwd, stdio: 'inherit' });
    return true;
  } catch (error) {
    return false;
  }
}

function main() {
  log('Setting up Python backend...\n');

  // Create virtual environment
  if (!fs.existsSync(venvDir)) {
    log('Creating Python virtual environment...');
    if (!runCommand(`python -m venv venv`, backendDir)) {
      throw new Error('Failed to create virtual environment');
    }
  }

  // Upgrade pip
  log('Upgrading pip...');
  runCommand(`"${pipExe}" install --upgrade pip --quiet`);

  // Install dependencies
  log('Installing Python dependencies...');
  
  // Use simplified requirements that avoid compilation issues
  const requirementsPath = path.join(backendDir, 'requirements-simple.txt');
  
  if (!fs.existsSync(requirementsPath)) {
    // Create simplified requirements if it doesn't exist
    const requirements = `# Core dependencies
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
`;
    fs.writeFileSync(requirementsPath, requirements);
  }

  if (!runCommand(`"${pipExe}" install -r requirements-simple.txt --quiet`, backendDir)) {
    log('Warning: Some dependencies may have failed to install');
    log('Try running manually: backend\\venv\\Scripts\\pip.exe install -r requirements-simple.txt');
  }

  log('✓ Backend setup complete');
}

try {
  main();
} catch (error) {
  console.error(`Error: ${error.message}`);
  process.exit(1);
}
