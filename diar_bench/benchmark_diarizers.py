"""Benchmark diarization systems: pyannote Community-1 (3 modes) + optional FS-EEND."""
import argparse
import json
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd
import torch
from pyannote.audio import Pipeline

from utils_audio import ensure_local_or_download
from viz import plot_timeline, plot_change_cues


def trim_audio(input_path: Path, output_path: Path, seconds: int):
    """Trim audio to first N seconds."""
    cmd = [
        'ffmpeg', '-y', '-i', str(input_path),
        '-t', str(seconds),
        '-c', 'copy',
        str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def run_pyannote(audio_path: Path, mode: str, device: str = "cpu") -> tuple:
    """
    Run pyannote Community-1 diarization.
    
    Args:
        audio_path: Path to 16kHz mono WAV
        mode: 'auto', 'bounded', or 'forced'
        device: 'cpu' or 'cuda'
    
    Returns:
        (segments, metrics_dict)
        segments: list of (start, end, label)
        metrics: dict with n_speakers, n_turns, etc.
    """
    import soundfile as sf
    import torch
    
    print(f"\n{'='*60}")
    print(f"Running pyannote Community-1 - {mode.upper()} mode")
    print(f"{'='*60}")
    
    # Load pipeline
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1")
    
    if device == "cuda" and torch.cuda.is_available():
        pipeline.to(torch.device("cuda"))
        print("Using CUDA")
    else:
        print("Using CPU")
    
    # Set parameters based on mode
    params = {}
    if mode == 'bounded':
        params['min_speakers'] = 2
        params['max_speakers'] = 4
        print("Parameters: min_speakers=2, max_speakers=4")
    elif mode == 'forced':
        params['num_speakers'] = 2
        print("Parameters: num_speakers=2")
    else:  # auto
        print("Parameters: auto (no constraints)")
    
    # Load audio in memory to avoid AudioDecoder issues
    waveform, sample_rate = sf.read(str(audio_path))
    # Convert to torch tensor and add channel dimension if needed
    if len(waveform.shape) == 1:
        waveform = waveform.reshape(1, -1)
    else:
        waveform = waveform.T  # (channels, samples)
    
    waveform_tensor = torch.from_numpy(waveform).float()
    
    audio_dict = {
        "waveform": waveform_tensor,
        "sample_rate": sample_rate
    }
    
    # Run diarization
    start_time = time.time()
    diarization = pipeline(audio_dict, **params)
    elapsed = time.time() - start_time
    
    print(f"Diarization completed in {elapsed:.2f}s")
    
    # Extract segments
    segments = []
    # Use speaker_diarization attribute
    diar = diarization.speaker_diarization if hasattr(diarization, 'speaker_diarization') else diarization
    for turn, _, speaker in diar.itertracks(yield_label=True):
        segments.append((turn.start, turn.end, speaker))
    
    # Calculate metrics
    speakers = list(set(seg[2] for seg in segments))
    n_speakers = len(speakers)
    n_turns = len(segments)
    
    # Duration per speaker
    speaker_durations = Counter()
    for start, end, label in segments:
        speaker_durations[label] += (end - start)
    
    total_duration = sum(speaker_durations.values())
    speaker_percentages = {spk: (dur / total_duration * 100) 
                          for spk, dur in speaker_durations.items()}
    
    # Average turn duration per speaker
    speaker_turn_counts = Counter(seg[2] for seg in segments)
    avg_turn_duration = {spk: speaker_durations[spk] / speaker_turn_counts[spk]
                        for spk in speakers}
    
    # Find first split (when second speaker appears)
    first_split_s = None
    if n_speakers > 1:
        first_speaker = segments[0][2]
        for start, end, label in segments:
            if label != first_speaker:
                first_split_s = start
                break
    
    # Calculate speaker switches per minute
    switches = sum(1 for i in range(1, len(segments)) 
                  if segments[i][2] != segments[i-1][2])
    switches_per_min = (switches / total_duration) * 60 if total_duration > 0 else 0
    
    # Top speaker percentage
    top_speaker_pct = max(speaker_percentages.values()) if speaker_percentages else 0
    
    metrics = {
        'mode': mode,
        'n_speakers': n_speakers,
        'n_turns': n_turns,
        'speakers': speakers,
        'speaker_percentages': speaker_percentages,
        'avg_turn_duration': avg_turn_duration,
        'first_split_s': first_split_s,
        'switches_per_min': switches_per_min,
        'top_speaker_pct': top_speaker_pct,
        'total_duration': total_duration,
        'elapsed_time': elapsed,
    }
    
    print(f"\nResults:")
    print(f"  Speakers detected: {n_speakers}")
    print(f"  Total turns: {n_turns}")
    print(f"  First split at: {first_split_s:.2f}s" if first_split_s else "  No split detected")
    print(f"  Switches/min: {switches_per_min:.2f}")
    print(f"  Top speaker: {top_speaker_pct:.1f}%")
    
    return segments, metrics


def run_speechbrain(audio_path: Path, device: str = "cpu") -> tuple:
    """
    Run SpeechBrain ECAPA-TDNN based diarization.
    Returns (segments, metrics) or (None, None) if failed.
    """
    print(f"\n{'='*60}")
    print("Running SpeechBrain Diarization")
    print(f"{'='*60}")
    
    try:
        from speechbrain.inference.speaker import SpeakerRecognition
        import torch
        import soundfile as sf
        
        # Load pretrained model
        print("Loading SpeechBrain ECAPA-TDNN model...")
        verification = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models/spkrec-ecapa-voxceleb",
            run_opts={"device": device}
        )
        
        # Load audio
        waveform, sample_rate = sf.read(str(audio_path))
        
        # SpeechBrain diarization is more complex - for now, just note it's available
        print("SpeechBrain loaded successfully")
        print("Note: SpeechBrain requires additional pipeline setup for full diarization")
        print("Skipping for now - would need clustering + VAD integration")
        
        return None, None
        
    except Exception as e:
        print(f"SpeechBrain failed: {e}")
        return None, None


def try_fs_eend(audio_path: Path) -> tuple:
    """
    Attempt to run FS-EEND diarization.
    Returns (segments, metrics) or (None, None) if failed.
    """
    print(f"\n{'='*60}")
    print("Attempting FS-EEND (optional)")
    print(f"{'='*60}")
    
    try:
        # Try to import
        import fs_eend
        print("FS-EEND module found, attempting to run...")
        
        # This is a placeholder - actual FS-EEND implementation would go here
        # Since it's optional and may not be installed, we'll gracefully skip
        print("FS-EEND implementation not available in this environment")
        return None, None
        
    except ImportError:
        print("FS-EEND not installed - skipping (this is expected)")
        return None, None
    except Exception as e:
        print(f"FS-EEND failed: {e} - skipping gracefully")
        return None, None


def save_segments_csv(segments, csv_path: Path):
    """Save segments to CSV."""
    df = pd.DataFrame(segments, columns=['start', 'end', 'speaker'])
    df.to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")


def generate_summary(results: dict, run_dir: Path):
    """Generate SUMMARY.md with comparison table and recommendation."""
    
    # Create comparison table
    table_data = []
    for mode, data in results.items():
        if data is None:
            continue
        metrics = data['metrics']
        table_data.append({
            'Run': mode,
            '#Speakers': metrics['n_speakers'],
            '#Turns': metrics['n_turns'],
            'Avg turn (s)': f"{sum(metrics['avg_turn_duration'].values()) / len(metrics['avg_turn_duration']):.2f}" if metrics['avg_turn_duration'] else "N/A",
            'First split (s)': f"{metrics['first_split_s']:.2f}" if metrics['first_split_s'] else "N/A",
            'Switches/min': f"{metrics['switches_per_min']:.2f}",
            '%TopSpeaker': f"{metrics['top_speaker_pct']:.1f}%",
        })
    
    df = pd.DataFrame(table_data)
    
    # Determine recommendation
    auto_speakers = results['auto']['metrics']['n_speakers'] if results.get('auto') else 0
    bounded_speakers = results['bounded']['metrics']['n_speakers'] if results.get('bounded') else 0
    forced_speakers = results['forced']['metrics']['n_speakers'] if results.get('forced') else 0
    
    auto_split = results['auto']['metrics']['first_split_s'] if results.get('auto') else None
    forced_split = results['forced']['metrics']['first_split_s'] if results.get('forced') else None
    
    meaningful_diff = False
    recommendation = []
    
    if auto_speakers == 1 and (bounded_speakers > 1 or forced_speakers > 1):
        meaningful_diff = True
        recommendation.append("⚠️ AUTO mode found only 1 speaker, but BOUNDED/FORCED found multiple.")
        recommendation.append("This suggests auto-K is too conservative for this audio.")
    
    if forced_speakers == 2 and forced_split and forced_split < 30:
        recommendation.append(f"✓ FORCED K=2 detected second speaker early ({forced_split:.1f}s).")
        recommendation.append("This indicates a true 2-speaker conversation.")
        meaningful_diff = True
    
    if auto_speakers == forced_speakers and auto_split and forced_split:
        if abs(auto_split - forced_split) < 5:
            recommendation.append("✓ AUTO and FORCED modes agree closely - results are consistent.")
        else:
            recommendation.append(f"⚠️ AUTO split at {auto_split:.1f}s vs FORCED at {forced_split:.1f}s - timing differs.")
            meaningful_diff = True
    
    if not recommendation:
        recommendation.append("Results are similar across modes - no major differences detected.")
    
    final_rec = "**Meaningful difference?** " + ("YES" if meaningful_diff else "NO")
    final_rec += "\n\n" + "\n".join(recommendation)
    
    # Write SUMMARY.md
    summary_path = run_dir / "SUMMARY.md"
    with open(summary_path, 'w') as f:
        f.write("# Diarization Benchmark Summary\n\n")
        f.write(f"**Run Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Comparison Table\n\n")
        f.write(df.to_markdown(index=False))
        f.write("\n\n## Recommendation\n\n")
        f.write(final_rec)
        f.write("\n\n## Details\n\n")
        
        for mode, data in results.items():
            if data is None:
                continue
            metrics = data['metrics']
            f.write(f"### {mode.upper()} Mode\n\n")
            f.write(f"- **Speakers:** {', '.join(metrics['speakers'])}\n")
            f.write(f"- **Speaker distribution:**\n")
            for spk, pct in metrics['speaker_percentages'].items():
                f.write(f"  - {spk}: {pct:.1f}%\n")
            f.write(f"- **Processing time:** {metrics['elapsed_time']:.2f}s\n\n")
    
    print(f"\nSaved: {summary_path}")
    
    # Also save JSON
    json_path = run_dir / "summary.json"
    json_data = {mode: data['metrics'] if data else None for mode, data in results.items()}
    # Convert non-serializable types
    for mode in json_data:
        if json_data[mode]:
            json_data[mode]['avg_turn_duration'] = {k: float(v) for k, v in json_data[mode]['avg_turn_duration'].items()}
            json_data[mode]['speaker_percentages'] = {k: float(v) for k, v in json_data[mode]['speaker_percentages'].items()}
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Saved: {json_path}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark diarization systems")
    parser.add_argument('--source', required=True, help="YouTube URL or local audio file path")
    parser.add_argument('--try-fs-eend', action='store_true', help="Attempt to run FS-EEND")
    parser.add_argument('--seconds', type=int, default=120, help="Trim to N seconds (0 = full file)")
    
    args = parser.parse_args()
    
    # Create run directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = Path('runs') / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Diarization Benchmark")
    print(f"Run directory: {run_dir}")
    print(f"{'='*60}\n")
    
    # Get audio
    print("Step 1: Obtaining audio...")
    audio_16k = ensure_local_or_download(args.source, run_dir)
    print(f"Audio ready: {audio_16k}")
    
    # Trim if requested
    if args.seconds > 0:
        print(f"\nStep 2: Trimming to {args.seconds} seconds...")
        trimmed_path = run_dir / "head.wav"
        trim_audio(audio_16k, trimmed_path, args.seconds)
        audio_to_process = trimmed_path
    else:
        audio_to_process = audio_16k
    
    # Get audio duration
    import soundfile as sf
    data, sr = sf.read(audio_to_process)
    duration = len(data) / sr
    print(f"Processing duration: {duration:.2f}s")
    
    # Detect CUDA
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Run benchmarks
    results = {}
    
    # Auto mode
    segments_auto, metrics_auto = run_pyannote(audio_to_process, 'auto', device)
    results['auto'] = {'segments': segments_auto, 'metrics': metrics_auto}
    save_segments_csv(segments_auto, run_dir / "pyannote_auto.csv")
    plot_timeline(segments_auto, duration, run_dir / "timeline_auto.png", "Pyannote Auto-K")
    
    # Bounded mode
    segments_bounded, metrics_bounded = run_pyannote(audio_to_process, 'bounded', device)
    results['bounded'] = {'segments': segments_bounded, 'metrics': metrics_bounded}
    save_segments_csv(segments_bounded, run_dir / "pyannote_bounded.csv")
    plot_timeline(segments_bounded, duration, run_dir / "timeline_bounded.png", "Pyannote Bounded (2-4)")
    
    # Forced mode
    segments_forced, metrics_forced = run_pyannote(audio_to_process, 'forced', device)
    results['forced'] = {'segments': segments_forced, 'metrics': metrics_forced}
    save_segments_csv(segments_forced, run_dir / "pyannote_forced.csv")
    plot_timeline(segments_forced, duration, run_dir / "timeline_forced.png", "Pyannote Forced K=2")
    
    # Optional: FS-EEND
    if args.try_fs_eend:
        segments_fseend, metrics_fseend = try_fs_eend(audio_to_process)
        if segments_fseend:
            results['fs_eend'] = {'segments': segments_fseend, 'metrics': metrics_fseend}
            save_segments_csv(segments_fseend, run_dir / "fs_eend.csv")
            plot_timeline(segments_fseend, duration, run_dir / "timeline_fseend.png", "FS-EEND")
        else:
            results['fs_eend'] = None
    
    # Generate summary
    print(f"\n{'='*60}")
    print("Generating summary...")
    print(f"{'='*60}")
    generate_summary(results, run_dir)
    
    # Print first 10 lines of each CSV
    print(f"\n{'='*60}")
    print("CSV Previews (first 10 lines)")
    print(f"{'='*60}\n")
    
    for csv_file in run_dir.glob("*.csv"):
        print(f"\n{csv_file.name}:")
        print("-" * 40)
        with open(csv_file) as f:
            for i, line in enumerate(f):
                if i >= 10:
                    break
                print(line.rstrip())
    
    print(f"\n{'='*60}")
    print(f"✓ Benchmark complete!")
    print(f"Results in: {run_dir.absolute()}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
