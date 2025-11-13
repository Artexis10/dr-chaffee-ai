# WSL 2 + NVIDIA GPU Setup Guide for Docker Desktop

Complete guide to enable GPU acceleration for Docker containers on Windows with RTX 5080.

## Prerequisites

- ✅ Windows 11 or Windows 10 (Build 19041+)
- ✅ NVIDIA GPU (RTX 5080)
- ✅ NVIDIA GPU drivers installed on Windows (latest)
- ✅ Docker Desktop installed
- ✅ Virtualization enabled in BIOS

## Step 1: Enable WSL 2

### 1.1 Install WSL 2

Open **PowerShell as Administrator** and run:

```powershell
wsl --install
```

This will:
- Enable WSL 2 feature
- Install Ubuntu Linux distribution
- Set WSL 2 as default

**Restart your computer** when prompted.

### 1.2 Verify WSL 2 Installation

```powershell
wsl --list --verbose
```

Output should show:
```
NAME      STATE           VERSION
Ubuntu    Running         2
```

If Ubuntu shows VERSION 1, upgrade it:
```powershell
wsl --set-version Ubuntu 2
```

## Step 2: Configure Docker Desktop for WSL 2

### 2.1 Switch to WSL 2 Backend

1. Open **Docker Desktop**
2. Go to **Settings** → **General**
3. ✅ Check **"Use the WSL 2 based engine"**
4. Click **Apply & Restart**

### 2.2 Enable WSL 2 Integration

1. Go to **Settings** → **Resources** → **WSL Integration**
2. ✅ Enable integration with your **Ubuntu** distribution
3. Click **Apply & Restart**

## Step 3: Install NVIDIA Container Toolkit in WSL 2

### 3.1 Open WSL 2 Terminal

```powershell
wsl
```

Or use Windows Terminal and select Ubuntu.

### 3.2 Update Package Manager

```bash
sudo apt update
sudo apt upgrade -y
```

### 3.2b Install Docker in WSL 2 (if not already installed)

Check if Docker is installed:
```bash
docker --version
```

If not found, install it:

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (optional, to avoid sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
```

### 3.3 Install NVIDIA GPU Support

**Option A: Using official NVIDIA repository (recommended)**

```bash
# Add NVIDIA GPG key
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# Add NVIDIA repository
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Update package list
sudo apt update

# Install NVIDIA Container Toolkit
sudo apt install -y nvidia-container-toolkit
```

**Option B: If Option A fails, use direct installation**

```bash
# Install from GitHub releases
wget https://github.com/NVIDIA/nvidia-docker/releases/download/v2.13.0/nvidia-docker_2.13.0_amd64.deb
sudo dpkg -i nvidia-docker_2.13.0_amd64.deb
sudo apt install -f
```

### 3.4 Restart Docker Daemon

```bash
# If Docker is running as systemd service
sudo systemctl restart docker

# If Docker is not running as service, restart it manually
sudo service docker restart

# Or simply exit WSL and restart
exit
# Then in PowerShell:
# wsl --shutdown
# wsl
```

## Step 4: Verify GPU Access

### 4.1 Test GPU in Container

```bash
# Use latest CUDA 13 image (recommended)
docker run --rm --gpus all nvidia/cuda:13.0.0-runtime-ubuntu22.04 nvidia-smi
```

Expected output:
```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 580.XX.XX             Driver Version: 581.XX         CUDA Version: 13.0     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|   0  NVIDIA GeForce RTX 5080        On  |   00000000:26:00.0  On |                  N/A |
|  0%   51C    P5             23W /  360W |    3227MiB /  16303MiB |      2%      Default |
+-----------------------------------------------------------------------------------------+
```

If you see your RTX 5080, GPU access is working! ✅

## Step 5: Enable GPU in Dr. Chaffee Project

### 5.1 Uncomment GPU Runtime

Edit `docker-compose.dev.yml`:

```yaml
backend:
  # ... other config ...
  runtime: nvidia  # ← Uncomment this line
```

### 5.2 Restart Backend

```bash
docker-compose -f docker-compose.dev.yml restart backend
```

### 5.3 Verify GPU Detection

Run ingestion:

```bash
docker-compose -f docker-compose.dev.yml exec backend python scripts/ingest_youtube.py
```

Look for:
```
✅ GPU detected - using CUDA acceleration
```

Instead of:
```
⚠️  No GPU detected - will use CPU (slower)
```

## Step 6: Performance Optimization

### 6.1 Allocate More WSL 2 Resources

Create/edit `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
memory=16GB
processors=8
swap=4GB
localhostForwarding=true
```

Restart WSL:
```powershell
wsl --shutdown
wsl
```

### 6.2 Monitor GPU Usage

In WSL terminal:
```bash
watch -n 1 nvidia-smi
```

## Troubleshooting

### GPU Not Detected

1. **Verify NVIDIA drivers on Windows:**
   ```powershell
   nvidia-smi
   ```
   Should show your RTX 5080

2. **Check WSL 2 GPU support:**
   ```bash
   wsl
   nvidia-smi
   ```

3. **Restart Docker:**
   ```bash
   docker restart
   ```

### Permission Denied Errors

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Container Won't Start

Check logs:
```bash
docker-compose -f docker-compose.dev.yml logs backend
```

## Performance Expectations

With GPU enabled:

| Task | CPU | GPU (RTX 5080) |
|------|-----|---|
| Whisper transcription (1 hour audio) | ~30 min | ~3-5 min |
| Embedding generation (1000 segments) | ~2 min | ~10 sec |
| Full ingestion (100 videos) | ~24 hours | ~2-3 hours |

## References

- [WSL 2 Documentation](https://learn.microsoft.com/en-us/windows/wsl/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)
- [Docker Desktop WSL 2 Backend](https://docs.docker.com/desktop/wsl/)
- [NVIDIA CUDA on WSL 2](https://docs.nvidia.com/cuda/wsl-user-guide/)

## Quick Reference Commands

```bash
# Open WSL 2
wsl

# Check GPU
nvidia-smi

# Monitor GPU
watch -n 1 nvidia-smi

# Restart Docker
sudo systemctl restart docker

# Test GPU in Docker
docker run --rm --gpus all nvidia/cuda:12.0.0-runtime-ubuntu22.04 nvidia-smi

# Run Dr. Chaffee ingestion
docker-compose -f docker-compose.dev.yml exec backend python scripts/ingest_youtube.py
```

## Next Steps

1. ✅ Complete steps 1-4 above
2. ✅ Verify GPU access with test command
3. ✅ Uncomment `runtime: nvidia` in docker-compose.dev.yml
4. ✅ Restart backend and verify GPU detection
5. 🚀 Run ingestion with GPU acceleration!
