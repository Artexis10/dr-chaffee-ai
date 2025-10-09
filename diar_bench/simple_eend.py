"""
Simple End-to-End style diarization using sliding windows and spectral clustering.
This is a simplified approach that processes audio in small windows.
"""
import argparse
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from pyannote.audio import Model
from sklearn.cluster import SpectralClustering
import pandas as pd


def extract_embeddings_sliding_window(audio_path: Path, window_size: float = 1.5, hop_size: float = 0.75):
    """
    Extract speaker embeddings using sliding windows.
    
    Args:
        audio_path: Path to audio file
        window_size: Window size in seconds
        hop_size: Hop size in seconds
    
    Returns:
        embeddings: (n_windows, embedding_dim) array
        timestamps: (n_windows, 2) array of (start, end) times
    """
    print(f"Loading audio from {audio_path}...")
    waveform, sr = sf.read(audio_path)
    
    # Convert to mono if stereo
    if len(waveform.shape) > 1:
        waveform = waveform.mean(axis=1)
    
    # Load pyannote embedding model
    print("Loading pyannote embedding model...")
    model = Model.from_pretrained("pyannote/embedding", use_auth_token=None)
    
    if torch.cuda.is_available():
        model = model.cuda()
    
    # Calculate window parameters
    window_samples = int(window_size * sr)
    hop_samples = int(hop_size * sr)
    
    embeddings = []
    timestamps = []
    
    print(f"Extracting embeddings (window={window_size}s, hop={hop_size}s)...")
    
    for start_sample in range(0, len(waveform) - window_samples, hop_samples):
        end_sample = start_sample + window_samples
        window = waveform[start_sample:end_sample]
        
        # Convert to tensor
        window_tensor = torch.from_numpy(window).float().unsqueeze(0)
        if torch.cuda.is_available():
            window_tensor = window_tensor.cuda()
        
        # Extract embedding
        with torch.no_grad():
            embedding = model(window_tensor)
            embeddings.append(embedding.cpu().numpy().flatten())
        
        # Store timestamp
        start_time = start_sample / sr
        end_time = end_sample / sr
        timestamps.append((start_time, end_time))
    
    embeddings = np.array(embeddings)
    timestamps = np.array(timestamps)
    
    print(f"Extracted {len(embeddings)} embeddings")
    
    return embeddings, timestamps


def cluster_embeddings(embeddings, n_speakers: int = 2):
    """
    Cluster embeddings using spectral clustering.
    
    Args:
        embeddings: (n_windows, embedding_dim) array
        n_speakers: Number of speakers
    
    Returns:
        labels: (n_windows,) array of speaker labels
    """
    print(f"Clustering into {n_speakers} speakers...")
    
    # Normalize embeddings
    embeddings_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
    
    # Compute affinity matrix (cosine similarity)
    affinity = np.dot(embeddings_norm, embeddings_norm.T)
    
    # Spectral clustering
    clustering = SpectralClustering(
        n_clusters=n_speakers,
        affinity='precomputed',
        random_state=42
    )
    
    labels = clustering.fit_predict(affinity)
    
    print(f"Clustering complete")
    
    return labels


def merge_consecutive_segments(timestamps, labels):
    """Merge consecutive segments with the same speaker."""
    if len(labels) == 0:
        return []
    
    segments = []
    current_speaker = labels[0]
    current_start = timestamps[0][0]
    current_end = timestamps[0][1]
    
    for i in range(1, len(labels)):
        if labels[i] == current_speaker:
            # Extend current segment
            current_end = timestamps[i][1]
        else:
            # Save current segment and start new one
            segments.append((current_start, current_end, f"SPEAKER_{current_speaker}"))
            current_speaker = labels[i]
            current_start = timestamps[i][0]
            current_end = timestamps[i][1]
    
    # Add final segment
    segments.append((current_start, current_end, f"SPEAKER_{current_speaker}"))
    
    return segments


def run_simple_eend(audio_path: Path, n_speakers: int = 2, window_size: float = 1.5, hop_size: float = 0.75):
    """
    Run simple E2E-style diarization.
    
    Args:
        audio_path: Path to audio file
        n_speakers: Number of speakers
        window_size: Window size in seconds
        hop_size: Hop size in seconds
    
    Returns:
        segments: List of (start, end, speaker) tuples
    """
    # Extract embeddings
    embeddings, timestamps = extract_embeddings_sliding_window(audio_path, window_size, hop_size)
    
    # Cluster
    labels = cluster_embeddings(embeddings, n_speakers)
    
    # Merge consecutive segments
    segments = merge_consecutive_segments(timestamps, labels)
    
    print(f"\nFound {len(segments)} segments")
    print(f"Speakers: {set(seg[2] for seg in segments)}")
    
    return segments


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Simple E2E-style diarization")
    parser.add_argument('--audio', required=True, help="Path to audio file")
    parser.add_argument('--speakers', type=int, default=2, help="Number of speakers")
    parser.add_argument('--window', type=float, default=1.5, help="Window size (seconds)")
    parser.add_argument('--hop', type=float, default=0.75, help="Hop size (seconds)")
    parser.add_argument('--output', help="Output CSV file")
    
    args = parser.parse_args()
    
    segments = run_simple_eend(
        Path(args.audio),
        n_speakers=args.speakers,
        window_size=args.window,
        hop_size=args.hop
    )
    
    # Print first 20 segments
    print("\nFirst 20 segments:")
    for i, (start, end, speaker) in enumerate(segments[:20]):
        print(f"{i+1:3d}. {start:7.2f}s - {end:7.2f}s: {speaker}")
    
    # Save to CSV if requested
    if args.output:
        df = pd.DataFrame(segments, columns=['start', 'end', 'speaker'])
        df.to_csv(args.output, index=False)
        print(f"\nSaved to {args.output}")
