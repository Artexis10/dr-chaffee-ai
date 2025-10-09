"""Pyannote Community-1 diarization runner."""
from typing import List, Tuple


def run_pyannote(wav_path: str, mode: str, use_cuda: bool) -> List[Tuple[float, float, str]]:
    """
    Run pyannote Community-1 in specified mode.
    
    Args:
        wav_path: Path to 16kHz mono WAV
        mode: 'auto', 'bounded', or 'forced2'
        use_cuda: Whether to use CUDA
    
    Returns:
        list[(start, end, label)]
    """
    from pyannote.audio import Pipeline
    import torch
    import soundfile as sf
    
    print(f"[pyannote] Loading pipeline for mode={mode}...")
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1")
    
    if use_cuda:
        try:
            pipeline.to(torch.device("cuda"))
            print("[pyannote] Using CUDA")
        except Exception as e:
            print(f"[pyannote] CUDA failed: {e}, using CPU")
    
    # Load audio in memory to avoid AudioDecoder issues
    waveform, sample_rate = sf.read(wav_path)
    if len(waveform.shape) == 1:
        waveform = waveform.reshape(1, -1)
    else:
        waveform = waveform.T
    
    waveform_tensor = torch.from_numpy(waveform).float()
    audio_dict = {"waveform": waveform_tensor, "sample_rate": sample_rate}
    
    # Set parameters based on mode
    if mode == "auto":
        print("[pyannote] Running auto-K (no constraints)")
        out = pipeline(audio_dict)
    elif mode == "bounded":
        print("[pyannote] Running bounded (min=2, max=4)")
        out = pipeline(audio_dict, min_speakers=2, max_speakers=4)
    elif mode == "forced2":
        print("[pyannote] Running forced K=2")
        out = pipeline(audio_dict, num_speakers=2)
    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    # Extract segments
    segs = []
    
    # Try v4-style speaker_diarization attribute
    if hasattr(out, "speaker_diarization"):
        diar = out.speaker_diarization
        try:
            for (turn, _, spk) in diar.itertracks(yield_label=True):
                segs.append((float(turn.start), float(turn.end), str(spk)))
            return segs
        except Exception:
            pass
        
        # Try pairs
        try:
            for (turn, spk) in diar:
                segs.append((float(turn.start), float(turn.end), str(spk)))
            return segs
        except Exception:
            pass
    
    # v3 fallback
    try:
        for (turn, _, spk) in out.itertracks(yield_label=True):
            segs.append((float(turn.start), float(turn.end), str(spk)))
    except Exception:
        pass
    
    print(f"[pyannote] Extracted {len(segs)} segments")
    return segs
