"""Audio utilities for downloading and preprocessing."""
import subprocess
from pathlib import Path
import yt_dlp


def download_audio_with_ytdlp(url: str, out_dir: Path) -> Path:
    """Download audio from YouTube using yt-dlp."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(out_dir / '%(id)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }],
        'quiet': False,
        'no_warnings': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info['id']
        
    # Find the downloaded WAV file
    wav_path = out_dir / f"{video_id}.wav"
    if not wav_path.exists():
        # Try other extensions
        for ext in ['m4a', 'webm', 'opus']:
            alt_path = out_dir / f"{video_id}.{ext}"
            if alt_path.exists():
                # Convert to WAV
                wav_path = out_dir / f"{video_id}.wav"
                subprocess.run([
                    'ffmpeg', '-y', '-i', str(alt_path),
                    '-acodec', 'pcm_s16le', str(wav_path)
                ], check=True, capture_output=True)
                alt_path.unlink()
                break
    
    return wav_path


def to_wav_16k_mono(src_path: Path, out_dir: Path) -> Path:
    """Convert audio to 16kHz mono WAV."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{src_path.stem}_16k_mono.wav"
    
    cmd = [
        'ffmpeg', '-y', '-i', str(src_path),
        '-ac', '1',  # Mono
        '-ar', '16000',  # 16kHz
        '-sample_fmt', 's16',  # PCM s16le
        str(out_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    
    return out_path


def ensure_local_or_download(source: str, work_dir: Path) -> Path:
    """Get local file or download from URL, then normalize to 16kHz mono."""
    work_dir.mkdir(parents=True, exist_ok=True)
    
    if source.startswith('http'):
        # Download
        downloads_dir = work_dir / 'downloads'
        raw_audio = download_audio_with_ytdlp(source, downloads_dir)
    else:
        # Local file
        raw_audio = Path(source)
        if not raw_audio.exists():
            raise FileNotFoundError(f"Local file not found: {source}")
    
    # Normalize to 16kHz mono
    normalized = to_wav_16k_mono(raw_audio, work_dir)
    return normalized
