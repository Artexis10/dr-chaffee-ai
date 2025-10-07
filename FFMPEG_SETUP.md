# FFmpeg Setup for yt-dlp

## Issue

yt-dlp requires FFmpeg for audio extraction:
```
ERROR: Postprocessing: ffprobe and ffmpeg not found. 
Please install or provide the path using --ffmpeg-location
```

## Solution

### Option 1: Install FFmpeg (Recommended)

#### Windows:
1. **Download FFmpeg**:
   - Go to https://www.gyan.dev/ffmpeg/builds/
   - Download "ffmpeg-release-essentials.zip"
   - Or use: https://github.com/BtbN/FFmpeg-Builds/releases

2. **Extract and Add to PATH**:
   ```powershell
   # Extract to C:\ffmpeg
   # Add to PATH
   $env:Path += ";C:\ffmpeg\bin"
   
   # Or permanently:
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\ffmpeg\bin", "User")
   ```

3. **Verify Installation**:
   ```bash
   ffmpeg -version
   ffprobe -version
   ```

#### Using Chocolatey (Windows):
```powershell
choco install ffmpeg
```

#### Using Scoop (Windows):
```powershell
scoop install ffmpeg
```

### Option 2: Use Embedded FFmpeg

yt-dlp can download FFmpeg automatically:
```bash
yt-dlp --update-to nightly
```

### Option 3: Specify FFmpeg Location

If FFmpeg is installed but not in PATH:
```bash
# Set environment variable
export FFMPEG_LOCATION="C:\path\to\ffmpeg\bin"

# Or in Python
os.environ['FFMPEG_LOCATION'] = r'C:\path\to\ffmpeg\bin'
```

## Verification

After installation, test:
```bash
# Test FFmpeg
ffmpeg -version

# Test with yt-dlp
yt-dlp --version
yt-dlp -f bestaudio --extract-audio --audio-format mp3 "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## For Production

Add FFmpeg to your deployment:
1. Include FFmpeg binaries in deployment package
2. Set FFMPEG_LOCATION environment variable
3. Or ensure FFmpeg is in system PATH

## Quick Fix for Current Session

```powershell
# Download portable FFmpeg
Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile "ffmpeg.zip"
Expand-Archive -Path "ffmpeg.zip" -DestinationPath "C:\ffmpeg"

# Add to PATH for current session
$env:Path += ";C:\ffmpeg\ffmpeg-7.1-essentials_build\bin"

# Verify
ffmpeg -version
```

## Alternative: Use YouTube Transcripts

If FFmpeg is not available, you can use YouTube's built-in transcripts:
```bash
python backend/scripts/ingest_youtube.py --use-youtube-transcripts
```

Note: This won't have speaker diarization or voice embeddings.
