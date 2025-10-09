"""NVIDIA NeMo Sortformer diarization runner (optional)."""
import os
import sys
import subprocess
from pathlib import Path
import pandas as pd


def run_nemo_sortformer(wav: Path, seconds: int, out_csv: Path) -> bool:
    """
    Run NeMo Sortformer diarization.
    
    Args:
        wav: Path to 16kHz mono WAV
        seconds: Duration to process (0 = full)
        out_csv: Output CSV path
    
    Returns:
        True if successful
    """
    print(f"[nemo] Starting NeMo Sortformer diarization...")
    
    # Try to install NeMo
    print("[nemo] Installing nemo_toolkit[asr]...")
    try:
        # Windows-compatible pip install
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "nemo_toolkit[asr]", "-q"],
            timeout=300  # 5 minute timeout
        )
    except subprocess.TimeoutExpired:
        print("[nemo] Install timeout - skipping")
        return False
    except Exception as e:
        print(f"[nemo] Install failed: {e}")
        print("[nemo] This is expected - NeMo has complex dependencies")
        return False
    
    # Trim audio if needed
    head = wav
    if seconds and seconds > 0:
        head = wav.with_name(wav.stem + f"_head{seconds}.wav")
        print(f"[nemo] Trimming to {seconds}s...")
        try:
            subprocess.check_call(
                f'ffmpeg -y -i "{wav}" -t {int(seconds)} "{head}" -loglevel error',
                shell=True
            )
        except Exception as e:
            print(f"[nemo] Trim failed: {e}")
            return False
    
    # Try to run NeMo diarization
    rttm = out_csv.with_suffix(".rttm")
    
    # Attempt 1: Use NeMo CLI if available
    try:
        # Note: Actual NeMo CLI may differ - this is a placeholder
        cmd = f'python -m nemo.collections.asr.scripts.diarize_speech --audio "{head}" --out_rttm "{rttm}"'
        print(f"[nemo] Running: {cmd}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"[nemo] CLI failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("[nemo] Inference timeout - skipping")
        return False
    except Exception as e:
        print(f"[nemo] Execution failed: {e}")
        return False
    
    # Parse RTTM to CSV
    if not rttm.exists():
        print(f"[nemo] RTTM output not found: {rttm}")
        return False
    
    print("[nemo] Parsing RTTM output...")
    segs = []
    
    try:
        for line in rttm.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            
            parts = line.split()
            if parts[0] != "SPEAKER":
                continue
            
            start = float(parts[3])
            dur = float(parts[4])
            lab = parts[-1]
            
            segs.append((start, start + dur, f"NEMO_{lab}"))
    except Exception as e:
        print(f"[nemo] RTTM parsing failed: {e}")
        return False
    
    if not segs:
        print("[nemo] No segments found in RTTM")
        return False
    
    # Save CSV
    pd.DataFrame(segs, columns=["start", "end", "label"]).to_csv(out_csv, index=False)
    print(f"[nemo] Saved {len(segs)} segments to {out_csv}")
    
    return True


if __name__ == "__main__":
    import argparse
    
    ap = argparse.ArgumentParser(description="NeMo Sortformer diarization runner")
    ap.add_argument("--wav", required=True, help="Path to 16kHz mono WAV")
    ap.add_argument("--seconds", type=int, default=120, help="Duration to process (0=full)")
    ap.add_argument("--out", required=True, help="Output CSV path")
    
    args = ap.parse_args()
    
    ok = run_nemo_sortformer(Path(args.wav), args.seconds, Path(args.out))
    sys.exit(0 if ok else 2)
