"""Visualization utilities for diarization results."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path


def plot_timeline(segments, duration, out_png_path, title="Speaker Timeline"):
    """
    Plot speaker diarization timeline.
    
    Args:
        segments: List of (start, end, label) tuples
        duration: Total audio duration in seconds
        out_png_path: Output PNG file path
        title: Plot title
    """
    if not segments:
        print(f"No segments to plot for {title}")
        return
    
    # Get unique speakers
    speakers = sorted(set(seg[2] for seg in segments))
    speaker_to_idx = {spk: idx for idx, spk in enumerate(speakers)}
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, max(3, len(speakers) * 0.8)))
    
    # Plot each segment
    colors = plt.cm.Set3(np.linspace(0, 1, len(speakers)))
    
    for start, end, label in segments:
        y_pos = speaker_to_idx[label]
        width = end - start
        rect = mpatches.Rectangle(
            (start, y_pos - 0.4), width, 0.8,
            facecolor=colors[y_pos],
            edgecolor='black',
            linewidth=0.5
        )
        ax.add_patch(rect)
    
    # Configure axes
    ax.set_xlim(0, duration)
    ax.set_ylim(-0.5, len(speakers) - 0.5)
    ax.set_yticks(range(len(speakers)))
    ax.set_yticklabels(speakers)
    ax.set_xlabel('Time (seconds)', fontsize=10)
    ax.set_ylabel('Speaker', fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(True, axis='x', alpha=0.3)
    
    # Add legend
    patches = [mpatches.Patch(color=colors[i], label=spk) 
               for i, spk in enumerate(speakers)]
    ax.legend(handles=patches, loc='upper right', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(out_png_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Saved timeline: {out_png_path}")


def plot_change_cues(audio_path, segments, out_png_path):
    """
    Optional: Plot MFCC-based change detection alongside diarization.
    This is a bonus feature to visualize likely boundary points.
    """
    try:
        import librosa
        
        # Load audio
        y, sr = librosa.load(audio_path, sr=16000)
        
        # Compute MFCC
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        
        # Compute frame-to-frame difference
        mfcc_delta = np.sum(np.abs(np.diff(mfcc, axis=1)), axis=0)
        
        # Normalize
        mfcc_delta = (mfcc_delta - mfcc_delta.min()) / (mfcc_delta.max() - mfcc_delta.min() + 1e-8)
        
        # Time axis
        times = librosa.frames_to_time(np.arange(len(mfcc_delta)), sr=sr)
        
        # Plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
        
        # MFCC change
        ax1.plot(times, mfcc_delta, linewidth=0.5, alpha=0.7)
        ax1.set_ylabel('MFCC Change')
        ax1.set_title('Acoustic Change Detection')
        ax1.grid(True, alpha=0.3)
        
        # Diarization
        speakers = sorted(set(seg[2] for seg in segments))
        colors = plt.cm.Set3(np.linspace(0, 1, len(speakers)))
        speaker_to_color = {spk: colors[i] for i, spk in enumerate(speakers)}
        
        for start, end, label in segments:
            ax2.axvspan(start, end, alpha=0.5, color=speaker_to_color[label], label=label)
        
        # Remove duplicate labels
        handles, labels = ax2.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax2.legend(by_label.values(), by_label.keys(), loc='upper right')
        
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('Speaker')
        ax2.set_title('Diarization Result')
        ax2.set_ylim(0, 1)
        ax2.set_yticks([])
        
        plt.tight_layout()
        plt.savefig(out_png_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Saved change cues plot: {out_png_path}")
        
    except Exception as e:
        print(f"Could not create change cues plot: {e}")
