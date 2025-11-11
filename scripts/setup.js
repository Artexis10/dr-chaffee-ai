#!/usr/bin/env node

/**
 * Dr. Chaffee AI - One-Command Setup
 * Run with: npm run setup
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const colors = {
  reset: '\x1b[0m',
  cyan: '\x1b[36m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  gray: '\x1b[90m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logStep(step, total, message) {
  log(`\nStep ${step}/${total}: ${message}`, 'cyan');
}

function logSuccess(message) {
  log(`  ✓ ${message}`, 'green');
}

function logError(message) {
  log(`  ✗ ${message}`, 'red');
}

function logWarning(message) {
  log(`  ⚠ ${message}`, 'yellow');
}

function checkCommand(command) {
  try {
    execSync(`${command} --version`, { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function runCommand(command, cwd = process.cwd()) {
  try {
    execSync(command, { cwd, stdio: 'inherit' });
    return true;
  } catch (error) {
    return false;
  }
}

async function main() {
  log('\n========================================', 'cyan');
  log('  Dr. Chaffee AI - Setup', 'cyan');
  log('========================================\n', 'cyan');

  // Step 1: Check prerequisites
  logStep(1, 6, 'Checking prerequisites');

  const checks = [
    { name: 'Python', command: 'python' },
    { name: 'Node.js', command: 'node' },
    { name: 'Docker', command: 'docker' },
  ];

  const missing = [];

  for (const check of checks) {
    if (checkCommand(check.command)) {
      logSuccess(`${check.name} found`);
    } else {
      logError(`${check.name} not found`);
      missing.push(check.name);
    }
  }

  if (missing.length > 0) {
    log('\n' + '='.repeat(40), 'red');
    logError(`Missing: ${missing.join(', ')}`);
    log('Install with:', 'yellow');
    log('  Python:  winget install Python.Python.3.12', 'gray');
    log('  Node.js: winget install OpenJS.NodeJS', 'gray');
    log('  Docker:  winget install Docker.DockerDesktop', 'gray');
    process.exit(1);
  }

  // Step 2: Create .env file
  logStep(2, 6, 'Setting up environment file');

  const envPath = path.join(process.cwd(), '.env');
  const envExamplePath = path.join(process.cwd(), '.env.example');

  if (!fs.existsSync(envPath)) {
    if (fs.existsSync(envExamplePath)) {
      fs.copyFileSync(envExamplePath, envPath);
      logSuccess('Created .env file');
      logWarning('Edit .env and add your API keys!');
    } else {
      logError('.env.example not found');
      process.exit(1);
    }
  } else {
    logSuccess('.env file already exists');
  }

  // Step 3: Setup backend
  logStep(3, 6, 'Installing backend dependencies');

  if (!runCommand('npm run setup:backend')) {
    logError('Failed to install backend dependencies');
    logWarning('Try running manually: npm run setup:backend');
  } else {
    logSuccess('Backend dependencies installed');
  }

  // Step 4: Setup frontend
  logStep(4, 6, 'Installing frontend dependencies');

  if (!runCommand('npm run setup:frontend')) {
    logError('Failed to install frontend dependencies');
    logWarning('Try running manually: npm run setup:frontend');
  } else {
    logSuccess('Frontend dependencies installed');
  }

  // Step 5: Start Docker
  logStep(5, 6, 'Starting Docker containers');

  try {
    execSync('docker info', { stdio: 'ignore' });
    if (runCommand('npm run setup:docker')) {
      logSuccess('Docker containers started');
      log('  Waiting for database to be ready...', 'gray');
      await new Promise(resolve => setTimeout(resolve, 10000));
    } else {
      logWarning('Could not start Docker containers');
      logWarning('Start Docker Desktop manually, then run: docker-compose up -d');
    }
  } catch {
    logWarning('Docker is not running');
    logWarning('Start Docker Desktop manually, then run: docker-compose up -d');
  }

  // Step 6: Create convenience scripts
  logStep(6, 6, 'Creating convenience scripts');

  const scripts = {
    'start.cmd': `@echo off\necho Starting Dr. Chaffee AI...\nnpm run start\n`,
    'stop.cmd': `@echo off\necho Stopping Dr. Chaffee AI...\nnpm run stop\n`,
  };

  for (const [filename, content] of Object.entries(scripts)) {
    const filepath = path.join(process.cwd(), filename);
    fs.writeFileSync(filepath, content);
  }

  logSuccess('Created start.cmd and stop.cmd');

  // Done!
  log('\n' + '='.repeat(40), 'green');
  log('  ✓ Setup Complete!', 'green');
  log('='.repeat(40) + '\n', 'green');

  log('Next steps:', 'yellow');
  log('');
  log('1. Edit .env with your API keys:', 'white');
  log('   - YOUTUBE_API_KEY (required for ingestion)', 'gray');
  log('   - OPENAI_API_KEY (optional, for answer mode)', 'gray');
  log('');
  log('2. Start the application:', 'white');
  log('   npm start', 'cyan');
  log('');
  log('3. Open in browser:', 'white');
  log('   http://localhost:3000', 'cyan');
  log('');
  log('4. Run test ingestion (10 videos):', 'white');
  log('   npm run ingest:test', 'cyan');
  log('');
  log('Common commands:', 'yellow');
  log('  npm start          - Start frontend + backend', 'gray');
  log('  npm run start:docker - Start database only', 'gray');
  log('  npm run stop       - Stop everything', 'gray');
  log('  npm run ingest     - Ingest all videos', 'gray');
  log('  npm run ingest:test - Ingest 10 test videos', 'gray');
  log('  npm run db:reset   - Reset database (deletes all data)', 'gray');
  log('');
}

main().catch(error => {
  logError(`Setup failed: ${error.message}`);
  process.exit(1);
});
