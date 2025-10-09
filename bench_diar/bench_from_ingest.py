"""Benchmark diarization systems using existing ingest_youtube pipeline."""
import os
import json
import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, List
import pandas as pd
import soundfile as sf
import torch

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from align import map_transcript_to_speakers, summarize_segments
from viz import plot_timeline
from py_run import run_pyannote
from sb_run import sb_diarize


def ensure_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        subprocess.run("ffmpeg -version", shell=True, check=True, 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception:
        print("[warn] ffmpeg not found. Install via Scoop/Chocolatey or add to PATH.")
        return False


def call_ingest(video_url: str, run_dir: Path) -> Dict:
    """
    Call existing ingest_youtube.py to get transcript and audio.
    
    Args:
        video_url: YouTube URL
        run_dir: Directory to store outputs
    
    Returns:
        dict with 'transcript' and 'audio_path'
    """
    # Find ingest_youtube.py
    ingest_script = Path("backend/scripts/ingest_youtube.py")
    if not ingest_script.exists():
        ingest_script = Path("ingest_youtube.py")
    
    if not ingest_script.exists():
        raise RuntimeError("ingest_youtube.py not found. Update bench_from_ingest.py with correct path.")
    
    print(f"[ingest] Using {ingest_script}")
    print(f"[ingest] Processing {video_url}...")
    
    # Run ingest with force flag to get fresh data
    # The script will process and store in database
    cmd = [
        sys.executable,
        str(ingest_script),
        "--from-url", video_url,
        "--force",  # Force reprocess
        "--source", "yt-dlp"
    ]
    
    print(f"[ingest] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[ingest] stderr: {result.stderr}")
        raise RuntimeError(f"Ingest failed with code {result.returncode}")
    
    # Extract video ID from URL
    video_id = video_url.split("v=")[-1].split("&")[0] if "v=" in video_url else video_url
    
    # Get segments from database using check_segments.py
    check_script = Path("check_segments.py")
    if check_script.exists():
        print(f"[ingest] Fetching segments from database...")
        result = subprocess.run(
            [sys.executable, str(check_script), video_id],
            capture_output=True,
            text=True
        )
        
        # Parse output to extract transcript
        # For now, we'll use a simpler approach - query DB directly
    
    # Alternative: Query database directly
    try:
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Get segments
        cur.execute("""
            SELECT start_time, end_time, content, speaker
            FROM segments
            WHERE video_id = %s
            ORDER BY start_time
        """, (video_id,))
        
        rows = cur.fetchall()
        transcript = []
        for start, end, text, speaker in rows:
            transcript.append({
                "start": float(start),
                "end": float(end),
                "text": text or "",
                "speaker_db": speaker  # Original speaker from DB
            })
        
        # Get audio path if stored locally
        cur.execute("""
            SELECT local_audio_path
            FROM videos
            WHERE video_id = %s
        """, (video_id,))
        
        row = cur.fetchone()
        audio_path = row[0] if row and row[0] else None
        
        conn.close()
        
        print(f"[ingest] Retrieved {len(transcript)} segments from database")
        
        return {
            "transcript": transcript,
            "audio_path": audio_path,
            "video_id": video_id
        }
        
    except Exception as e:
        print(f"[ingest] Database query failed: {e}")
        raise


def ytdlp_to_wav16k(url: str, out_dir: Path) -> Path:
    """Download and convert to 16kHz mono WAV using yt-dlp."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tmpl = out_dir / "%(id)s.%(ext)s"
    
    # Download
    cmd = f'yt-dlp -x --audio-format wav -f bestaudio --output "{tmpl}" "{url}"'
    code = subprocess.call(cmd, shell=True)
    
    if code != 0:
        # Fallback: bestaudio + transcode
        subprocess.check_call(f'yt-dlp -f bestaudio --output "{tmpl}" "{url}"', shell=True)
    
    latest = max(out_dir.glob("*"), key=lambda p: p.stat().st_mtime)
    
    # Normalize to 16k mono
    dst = latest.with_name(latest.stem + "_16k_mono.wav")
    subprocess.check_call(
        f'ffmpeg -y -i "{latest}" -ac 1 -ar 16000 -sample_fmt s16 "{dst}"',
        shell=True
    )
    
    return dst


def main():
    import argparse
    import datetime
    
    ap = argparse.ArgumentParser(description="Benchmark diarization using ingest pipeline")
    ap.add_argument("--source", required=True, help="YouTube URL or video ID")
    ap.add_argument("--seconds", type=int, default=120, help="Trim head for quick test (0=full)")
    ap.add_argument("--include-e2e", action="store_true", help="Include FS-EEND (E2E model)")
    ap.add_argument("--include-nemo", action="store_true", help="Include NeMo Sortformer (optional)")
    
    args = ap.parse_args()
    
    if not ensure_ffmpeg():
        print("[error] ffmpeg required but not found")
        sys.exit(1)
    
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("bench_diar") / "runs" / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Diarization Benchmark (Ingest Integration)")
    print(f"Run directory: {run_dir}")
    print(f"{'='*60}\n")
    
    # 1) Call ingest to get transcript and audio
    try:
        info = call_ingest(args.source, run_dir)
        transcript = info["transcript"]
        video_id = info["video_id"]
    except Exception as e:
        print(f"[error] Ingest failed: {e}")
        print("[info] Falling back to direct yt-dlp download...")
        transcript = []
        video_id = args.source.split("v=")[-1].split("&")[0] if "v=" in args.source else args.source
        info = {"audio_path": None, "video_id": video_id}
    
    # 2) Ensure local WAV 16k mono
    wav = None
    if info.get("audio_path") and Path(info["audio_path"]).exists():
        wav = Path(info["audio_path"])
        print(f"[audio] Using stored audio: {wav}")
        
        # Check if 16k mono
        try:
            sr = sf.info(str(wav)).samplerate
            ch = sf.info(str(wav)).channels
        except Exception:
            sr, ch = 0, 0
        
        if sr != 16000 or ch != 1:
            print(f"[audio] Converting to 16kHz mono...")
            dst = wav.with_name(wav.stem + "_16k_mono.wav")
            subprocess.check_call(
                f'ffmpeg -y -i "{wav}" -ac 1 -ar 16000 -sample_fmt s16 "{dst}"',
                shell=True
            )
            wav = dst
    else:
        print(f"[audio] Downloading from YouTube...")
        wav = ytdlp_to_wav16k(args.source, Path("bench_diar") / "downloads")
    
    # Optional trim for speed
    if args.seconds and args.seconds > 0:
        print(f"[audio] Trimming to {args.seconds} seconds...")
        head = wav.with_name(wav.stem + f"_head{args.seconds}.wav")
        subprocess.check_call(
            f'ffmpeg -y -i "{wav}" -t {int(args.seconds)} "{head}"',
            shell=True
        )
        wav = head
    
    duration = sf.info(str(wav)).duration
    use_cuda = torch.cuda.is_available()
    
    print(f"[audio] Duration: {duration:.2f}s")
    print(f"[audio] CUDA available: {use_cuda}")
    
    # 3) Run diarizers
    results = {}
    
    for mode, tag in [("auto", "py_auto"), ("bounded", "py_bounded"), ("forced2", "py_forced2")]:
        try:
            print(f"\n[diarize] Running pyannote {mode}...")
            segs = run_pyannote(str(wav), mode, use_cuda)
            pd.DataFrame(segs, columns=["start", "end", "label"]).to_csv(
                run_dir / f"{tag}.csv", index=False
            )
            results[tag] = summarize_segments(segs, duration)
            results[tag]["segments"] = segs
        except Exception as e:
            print(f"[warn] pyannote {mode} failed: {e}")
    
    try:
        print(f"\n[diarize] Running SpeechBrain...")
        sb_segs = sb_diarize(str(wav))
        if sb_segs:
            pd.DataFrame(sb_segs, columns=["start", "end", "label"]).to_csv(
                run_dir / "speechbrain_sc.csv", index=False
            )
            results["speechbrain_sc"] = summarize_segments(sb_segs, duration)
            results["speechbrain_sc"]["segments"] = sb_segs
    except Exception as e:
        print(f"[warn] SpeechBrain failed: {e}")
    
    # E2E Models (optional)
    if args.include_e2e:
        try:
            print(f"\n[diarize] Running FS-EEND (E2E)...")
            # Activate E2E venv and run
            e2e_csv = run_dir / "e2e_fseend.csv"
            cmd = [
                "powershell", "-File", "bench_diar/e2e_env.ps1", ";",
                sys.executable, "bench_diar/e2e_fseend_run.py",
                "--wav", str(wav),
                "--seconds", str(args.seconds),
                "--out", str(e2e_csv)
            ]
            result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and e2e_csv.exists():
                e2e_df = pd.read_csv(e2e_csv)
                e2e_segs = [(row['start'], row['end'], row['label']) for _, row in e2e_df.iterrows()]
                results["e2e_fseend"] = summarize_segments(e2e_segs, duration)
                results["e2e_fseend"]["segments"] = e2e_segs
                print(f"[diarize] FS-EEND complete")
            else:
                print(f"[warn] FS-EEND failed: {result.stderr}")
        except Exception as e:
            print(f"[warn] FS-EEND failed: {e}")
    
    if args.include_nemo:
        try:
            print(f"\n[diarize] Running NeMo Sortformer (E2E)...")
            nemo_csv = run_dir / "e2e_nemo.csv"
            cmd = [
                "powershell", "-File", "bench_diar/e2e_env.ps1", ";",
                sys.executable, "bench_diar/e2e_nemo_run.py",
                "--wav", str(wav),
                "--seconds", str(args.seconds),
                "--out", str(nemo_csv)
            ]
            result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0 and nemo_csv.exists():
                nemo_df = pd.read_csv(nemo_csv)
                nemo_segs = [(row['start'], row['end'], row['label']) for _, row in nemo_df.iterrows()]
                results["e2e_nemo"] = summarize_segments(nemo_segs, duration)
                results["e2e_nemo"]["segments"] = nemo_segs
                print(f"[diarize] NeMo complete")
            else:
                print(f"[warn] NeMo failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"[warn] NeMo timeout")
        except Exception as e:
            print(f"[warn] NeMo failed: {e}")
    
    # 4) Align each diarization to transcript
    if transcript:
        print(f"\n[align] Aligning diarization to transcript...")
        for name in ["py_auto", "py_bounded", "py_forced2", "speechbrain_sc", "e2e_fseend", "e2e_nemo"]:
            if name not in results:
                continue
            
            diar = results[name]["segments"]
            labeled = map_transcript_to_speakers(transcript, diar)
            pd.DataFrame(labeled).to_csv(run_dir / f"transcript_{name}.csv", index=False)
            print(f"[align] Saved transcript_{name}.csv")
    else:
        print("[warn] No transcript available for alignment")
    
    # 5) Timelines
    print(f"\n[viz] Creating timelines...")
    for name in ["py_auto", "py_bounded", "py_forced2", "speechbrain_sc", "e2e_fseend", "e2e_nemo"]:
        if name not in results:
            continue
        
        diar = results[name]["segments"]
        plot_timeline(diar, duration, str(run_dir / f"timeline_{name}.png"))
    
    # 6) SUMMARY.md
    print(f"\n[summary] Generating SUMMARY.md...")
    cols = ["Run", "Speakers", "Turns", "AvgTurn(s)", "FirstSplit(s)", "Switches/min", "%TopSpeaker"]
    lines = [
        "# Diarization Benchmark (Aligned to Ingest Transcript)",
        "",
        f"**Video**: {video_id}",
        f"**Duration**: {duration:.2f}s",
        f"**Transcript segments**: {len(transcript)}",
        "",
        "| " + " | ".join(cols) + " |",
        "|" + " | ".join(["---"] * len(cols)) + "|"
    ]
    
    for k, v in results.items():
        lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            k,
            v.get("n_speakers"),
            v.get("n_turns"),
            v.get("avg_turn_s"),
            v.get("first_split_s"),
            v.get("switches_per_min"),
            v.get("pct_top")
        ))
    
    # Heuristic verdict
    verdict = "NO"
    auto_spk = results.get("py_auto", {}).get("n_speakers", 1)
    bounded_spk = results.get("py_bounded", {}).get("n_speakers", 1)
    sb_spk = results.get("speechbrain_sc", {}).get("n_speakers", 1)
    
    if auto_spk < max(bounded_spk, sb_spk):
        verdict = "YES - auto-K under-counts speakers"
    
    lines += [
        "",
        f"**Meaningful difference?** {verdict}",
        "",
        "## Files",
        "- `*.csv` - Raw diarization outputs",
        "- `transcript_*.csv` - Transcript aligned with speaker labels",
        "- `timeline_*.png` - Visual timelines",
        ""
    ]
    
    (run_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    
    # Print results
    print(f"\n{'='*60}")
    print("Results")
    print(f"{'='*60}\n")
    
    for name in ["py_auto", "py_bounded", "py_forced2", "speechbrain_sc"]:
        p = run_dir / f"{name}.csv"
        if p.exists():
            print(f"\n{name}.csv (head 10):")
            print(pd.read_csv(p).head(10).to_string(index=False))
    
    print(f"\n{'='*60}")
    print(f"✓ Benchmark complete!")
    print(f"Results in: {run_dir.absolute()}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
