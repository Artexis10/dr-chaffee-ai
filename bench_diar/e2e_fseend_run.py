"""FS-EEND (End-to-End Neural Diarization) runner."""
import os
import sys
import subprocess
import json
from pathlib import Path
import pandas as pd


def ensure_repo(root: Path) -> Path:
    """Clone FS-EEND repo if not present."""
    third = root / "_third_party"
    third.mkdir(parents=True, exist_ok=True)
    repo = third / "FS-EEND"
    
    if not repo.exists():
        print("[fseend] Cloning FS-EEND repository...")
        try:
            # Use HTTPS URL explicitly
            subprocess.check_call(
                f'git -c core.sshCommand= clone https://github.com/Audio-WestlakeU/FS-EEND.git "{repo}"',
                shell=True
            )
        except Exception as e:
            print(f"[fseend] Clone failed: {e}")
            return None
    
    return repo


def install_dependencies(repo: Path) -> bool:
    """Install FS-EEND dependencies in current venv."""
    req = repo / "requirements.txt"
    
    if req.exists():
        print("[fseend] Installing dependencies...")
        try:
            subprocess.check_call(
                f'{sys.executable} -m pip install -r "{req}" -q',
                shell=True
            )
            return True
        except Exception as e:
            print(f"[fseend] Dependency install failed: {e}")
            return False
    
    return True


def run_fseend(wav: Path, seconds: int, out_csv: Path) -> bool:
    """
    Run FS-EEND diarization.
    
    Args:
        wav: Path to 16kHz mono WAV
        seconds: Duration to process (0 = full)
        out_csv: Output CSV path
    
    Returns:
        True if successful
    """
    print(f"[fseend] Starting FS-EEND diarization...")
    
    root = Path(__file__).resolve().parent
    repo = ensure_repo(root)
    
    if repo is None:
        return False
    
    # Install dependencies
    if not install_dependencies(repo):
        return False
    
    # Trim audio if needed
    head = wav
    if seconds and seconds > 0:
        head = wav.with_name(wav.stem + f"_head{seconds}.wav")
        print(f"[fseend] Trimming to {seconds}s...")
        try:
            subprocess.check_call(
                f'ffmpeg -y -i "{wav}" -t {int(seconds)} "{head}" -loglevel error',
                shell=True
            )
        except Exception as e:
            print(f"[fseend] Trim failed: {e}")
            return False
    
    # Try to run inference
    # Note: FS-EEND may have different entry points - adapt based on repo structure
    rttm = out_csv.with_suffix(".rttm")
    
    # Attempt 1: Look for inference script
    inference_script = repo / "inference.py"
    if not inference_script.exists():
        inference_script = repo / "eend" / "infer.py"
    
    if not inference_script.exists():
        print("[fseend] No inference script found in standard locations")
        print("[fseend] Checking for alternative entry points...")
        
        # Try to import and use Python API
        sys.path.insert(0, str(repo))
        try:
            # This is a placeholder - actual API depends on repo structure
            print("[fseend] Attempting to use Python API...")
            print("[fseend] Note: FS-EEND requires model weights and config")
            print("[fseend] Skipping - manual setup required")
            return False
        except Exception as e:
            print(f"[fseend] Python API failed: {e}")
            return False
    
    # Run inference
    try:
        cmd = f'{sys.executable} "{inference_script}" --audio "{head}" --out_rttm "{rttm}"'
        print(f"[fseend] Running: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[fseend] Inference failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[fseend] Execution failed: {e}")
        return False
    
    # Parse RTTM to CSV
    if not rttm.exists():
        print(f"[fseend] RTTM output not found: {rttm}")
        return False
    
    print("[fseend] Parsing RTTM output...")
    segs = []
    
    try:
        for line in rttm.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            
            parts = line.split()
            # RTTM format: SPEAKER <file> <chan> <start> <dur> <..> <..> <spklabel>
            if parts[0] != "SPEAKER":
                continue
            
            start = float(parts[3])
            dur = float(parts[4])
            lab = parts[-1]
            
            segs.append((start, start + dur, f"EEND_{lab}"))
    except Exception as e:
        print(f"[fseend] RTTM parsing failed: {e}")
        return False
    
    if not segs:
        print("[fseend] No segments found in RTTM")
        return False
    
    # Save CSV
    pd.DataFrame(segs, columns=["start", "end", "label"]).to_csv(out_csv, index=False)
    print(f"[fseend] Saved {len(segs)} segments to {out_csv}")
    
    return True


if __name__ == "__main__":
    import argparse
    
    ap = argparse.ArgumentParser(description="FS-EEND diarization runner")
    ap.add_argument("--wav", required=True, help="Path to 16kHz mono WAV")
    ap.add_argument("--seconds", type=int, default=120, help="Duration to process (0=full)")
    ap.add_argument("--out", required=True, help="Output CSV path")
    
    args = ap.parse_args()
    
    ok = run_fseend(Path(args.wav), args.seconds, Path(args.out))
    sys.exit(0 if ok else 2)
