"""Visualization utilities for diarization timelines."""
import matplotlib.pyplot as plt


def plot_timeline(segments, duration, out_png_title):
    """
    Plot speaker diarization timeline.
    
    Args:
        segments: list[(start, end, label)]
        duration: total duration in seconds
        out_png_title: output PNG path
    """
    if not segments:
        print(f"[warn] No segments to plot for {out_png_title}")
        return
    
    labels = sorted({lab for _, _, lab in segments})
    ymap = {lab: i for i, lab in enumerate(labels)}
    
    fig = plt.figure(figsize=(12, 1.2 + 0.4 * len(labels)))
    ax = plt.gca()
    
    for s, e, lab in segments:
        ax.broken_barh([(s, e - s)], (ymap[lab] - 0.4, 0.8))
    
    ax.set_xlim(0, max(1.0, duration))
    ax.set_ylim(-1, len(labels))
    ax.set_xlabel("Time (s)")
    ax.set_yticks(list(ymap.values()))
    ax.set_yticklabels(labels)
    ax.set_title(out_png_title.split('/')[-1].replace('.png', ''))
    
    fig.tight_layout()
    fig.savefig(out_png_title, dpi=150)
    plt.close(fig)
    
    print(f"[saved] {out_png_title}")
