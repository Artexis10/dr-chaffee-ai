"""Quick diarization comparison without database dependency."""
import sys
from pathlib import Path
import pandas as pd
import soundfile as sf
import torch

sys.path.insert(0, str(Path(__file__).parent))
from align import summarize_segments
from viz import plot_timeline
from py_run import run_pyannote
from sb_run import sb_diarize


def main():
    import argparse
    import datetime
    
    ap = argparse.ArgumentParser(description="Quick diarization comparison")
    ap.add_argument("--audio", required=True, help="Path to 16kHz mono WAV file")
    ap.add_argument("--output", default="bench_diar/quick_runs", help="Output directory")
    
    args = ap.parse_args()
    
    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"[error] Audio file not found: {audio_path}")
        sys.exit(1)
    
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(args.output) / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    
    duration = sf.info(str(audio_path)).duration
    use_cuda = torch.cuda.is_available()
    
    print(f"\n{'='*60}")
    print(f"Quick Diarization Comparison")
    print(f"{'='*60}")
    print(f"Audio: {audio_path}")
    print(f"Duration: {duration:.2f}s")
    print(f"CUDA: {use_cuda}")
    print(f"Output: {run_dir}")
    print(f"{'='*60}\n")
    
    results = {}
    
    # Run all systems
    for mode, tag in [("auto", "py_auto"), ("bounded", "py_bounded"), ("forced2", "py_forced2")]:
        try:
            print(f"\n[{tag}] Running...")
            start = datetime.datetime.now()
            segs = run_pyannote(str(audio_path), mode, use_cuda)
            elapsed = (datetime.datetime.now() - start).total_seconds()
            
            pd.DataFrame(segs, columns=["start", "end", "label"]).to_csv(
                run_dir / f"{tag}.csv", index=False
            )
            plot_timeline(segs, duration, str(run_dir / f"timeline_{tag}.png"))
            
            results[tag] = summarize_segments(segs, duration)
            results[tag]["elapsed"] = round(elapsed, 2)
            print(f"[{tag}] Complete in {elapsed:.2f}s - {results[tag]['n_speakers']} speakers, {results[tag]['n_turns']} turns")
        except Exception as e:
            print(f"[{tag}] Failed: {e}")
    
    # SpeechBrain
    try:
        print(f"\n[speechbrain] Running...")
        start = datetime.datetime.now()
        sb_segs = sb_diarize(str(audio_path))
        elapsed = (datetime.datetime.now() - start).total_seconds()
        
        if sb_segs:
            pd.DataFrame(sb_segs, columns=["start", "end", "label"]).to_csv(
                run_dir / "speechbrain_sc.csv", index=False
            )
            plot_timeline(sb_segs, duration, str(run_dir / "timeline_speechbrain_sc.png"))
            
            results["speechbrain_sc"] = summarize_segments(sb_segs, duration)
            results["speechbrain_sc"]["elapsed"] = round(elapsed, 2)
            print(f"[speechbrain] Complete in {elapsed:.2f}s - {results['speechbrain_sc']['n_speakers']} speakers, {results['speechbrain_sc']['n_turns']} turns")
    except Exception as e:
        print(f"[speechbrain] Failed: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}\n")
    
    # Table
    cols = ["System", "Speakers", "Turns", "AvgTurn(s)", "FirstSplit(s)", "Switches/min", "%Top", "Time(s)"]
    print(" | ".join(cols))
    print("|".join(["---"] * len(cols)))
    
    for name, data in results.items():
        print(" | ".join([
            name,
            str(data.get("n_speakers")),
            str(data.get("n_turns")),
            str(data.get("avg_turn_s")),
            str(data.get("first_split_s")),
            str(data.get("switches_per_min")),
            str(data.get("pct_top")),
            str(data.get("elapsed"))
        ]))
    
    # Verdict
    print(f"\n{'='*60}")
    auto_spk = results.get("py_auto", {}).get("n_speakers", 1)
    forced_spk = results.get("py_forced2", {}).get("n_speakers", 1)
    sb_spk = results.get("speechbrain_sc", {}).get("n_speakers", 1)
    
    auto_split = results.get("py_auto", {}).get("first_split_s")
    forced_split = results.get("py_forced2", {}).get("first_split_s")
    sb_split = results.get("speechbrain_sc", {}).get("first_split_s")
    
    print("VERDICT:")
    if auto_spk < max(forced_spk, sb_spk):
        print("  ⚠️  AUTO mode under-counts speakers")
    
    if auto_split and forced_split and abs(auto_split - forced_split) > 5:
        print(f"  ⚠️  First split differs: auto={auto_split:.1f}s vs forced={forced_split:.1f}s")
    
    if sb_split and forced_split and abs(sb_split - forced_split) > 5:
        print(f"  ⚠️  SpeechBrain detects earlier split: {sb_split:.1f}s vs pyannote {forced_split:.1f}s")
    
    if auto_spk == forced_spk == sb_spk and auto_split and forced_split and abs(auto_split - forced_split) < 2:
        print("  ✅ All systems agree - results consistent")
    
    print(f"\nResults saved to: {run_dir.absolute()}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
