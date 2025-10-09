"""SpeechBrain baseline diarization."""
from typing import List, Tuple
import soundfile as sf
import numpy as np


def sb_diarize(wav_path: str) -> List[Tuple[float, float, str]]:
    """
    SpeechBrain-based diarization using VAD + ECAPA embeddings + clustering.
    
    Args:
        wav_path: Path to 16kHz mono WAV
    
    Returns:
        list[(start, end, label)]
    """
    import torch
    import os
    import sys
    
    try:
        from speechbrain.inference.VAD import VAD
        from speechbrain.inference.speaker import EncoderClassifier
    except ImportError:
        print("[speechbrain] Not available, skipping")
        return []
    
    print("[speechbrain] Loading models...")
    
    # Load audio
    wav, sr = sf.read(wav_path)
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    
    # VAD to find speech segments
    try:
        vad = VAD.from_hparams(source="speechbrain/vad-crdnn-libriparty")
        speech = vad.get_speech_segments(wav_path)
    except Exception as e:
        print(f"[speechbrain] VAD failed: {e}")
        return []
    
    if not speech:
        print("[speechbrain] No speech detected")
        return []
    
    print(f"[speechbrain] Found {len(speech)} speech segments")
    
    # Create windows inside VAD speech: 1.5s window, 0.75s hop
    W, H = 1.5, 0.75
    windows = []
    for s, e in speech:
        t = s
        while t + 0.8 <= e:
            end = min(t + W, e)
            if end - t >= 0.8:
                windows.append((t, end))
            t += H
    
    if not windows:
        print("[speechbrain] No valid windows")
        return []
    
    print(f"[speechbrain] Created {len(windows)} windows")
    
    # Extract embeddings
    try:
        enc = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")
    except Exception as e:
        print(f"[speechbrain] Encoder failed: {e}")
        return []
    
    embs = []
    for (s, e) in windows:
        a = int(s * sr)
        b = int(e * sr)
        seg = torch.tensor(wav[a:b]).float().unsqueeze(0)
        
        with torch.no_grad():
            emb = enc.encode_batch(seg).squeeze().cpu().numpy()
        
        embs.append(emb / (np.linalg.norm(emb) + 1e-9))
    
    X = np.stack(embs, 0)
    print(f"[speechbrain] Extracted {len(X)} embeddings")
    
    # Clustering - try spectralcluster first
    labels = None
    try:
        from spectralcluster import SpectralClusterer
        clusterer = SpectralClusterer(min_clusters=1, max_clusters=5)
        labels = clusterer.predict(X)
        print("[speechbrain] Used spectralcluster")
    except ImportError:
        # Try ad-hoc install
        try:
            print("[speechbrain] Installing spectralcluster...")
            os.system(f"{sys.executable} -m pip install spectralcluster -q")
            from spectralcluster import SpectralClusterer
            clusterer = SpectralClusterer(min_clusters=1, max_clusters=5)
            labels = clusterer.predict(X)
            print("[speechbrain] Used spectralcluster (installed)")
        except Exception:
            # Greedy cosine threshold fallback
            print("[speechbrain] Using greedy clustering fallback")
            thr = 0.72
            cents = []
            labels = []
            
            for v in X:
                if not cents:
                    cents = [v]
                    labels.append(0)
                    continue
                
                sims = [float((v @ c) / (np.linalg.norm(c) + 1e-9)) for c in cents]
                k = int(np.argmax(sims))
                
                if sims[k] >= thr:
                    labels.append(k)
                    cents[k] = (cents[k] + v)
                    cents[k] /= (np.linalg.norm(cents[k]) + 1e-9)
                else:
                    labels.append(len(cents))
                    cents.append(v)
    
    # Stitch windows by label
    out = []
    cur_lab = labels[0]
    cur_s, cur_e = windows[0]
    
    for (lab, (s, e)) in zip(labels, windows):
        if lab == cur_lab and s <= cur_e + 0.25:
            cur_e = max(cur_e, e)
        else:
            out.append((cur_s, cur_e, f"SB_SPK_{int(cur_lab):02d}"))
            cur_lab, cur_s, cur_e = lab, s, e
    
    out.append((cur_s, cur_e, f"SB_SPK_{int(cur_lab):02d}"))
    
    print(f"[speechbrain] Generated {len(out)} segments")
    return out
