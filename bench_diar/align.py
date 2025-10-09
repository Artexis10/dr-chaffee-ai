"""Alignment utilities for transcript-to-diarization mapping."""
from typing import List, Tuple, Dict


def overlap(a0, a1, b0, b1):
    """Calculate overlap between two time intervals."""
    s = max(a0, b0)
    e = min(a1, b1)
    return max(0.0, e - s)


def map_transcript_to_speakers(transcript, diar):
    """
    Map transcript segments to speaker labels via majority overlap.
    
    Args:
        transcript: list[dict] with keys: start, end, text
        diar: list[tuple] (start, end, label)
    
    Returns:
        list[dict]: {start, end, text, label, conf}
    """
    diar_sorted = sorted(diar, key=lambda x: x[0])
    out = []
    
    for seg in transcript:
        s0, s1 = float(seg["start"]), float(seg["end"])
        votes: Dict[str, float] = {}
        
        for (d0, d1, lab) in diar_sorted:
            if d1 < s0:
                continue
            if d0 > s1:
                break
            ov = overlap(s0, s1, float(d0), float(d1))
            if ov > 0:
                votes[lab] = votes.get(lab, 0.0) + ov
        
        if votes:
            lab = max(votes, key=votes.get)
            conf = votes[lab] / max(1e-9, s1 - s0)
        else:
            lab, conf = "UNK", 0.0
        
        out.append({
            "start": s0,
            "end": s1,
            "text": seg.get("text", ""),
            "label": lab,
            "conf": round(conf, 3)
        })
    
    return out


def summarize_segments(diar, duration):
    """
    Compute summary statistics for diarization output.
    
    Args:
        diar: list[(start, end, label)]
        duration: total audio duration
    
    Returns:
        dict with metrics
    """
    diar = sorted(diar, key=lambda x: x[0])
    
    if not diar:
        return dict(
            n_speakers=0,
            n_turns=0,
            avg_turn_s=0,
            first_split_s=None,
            switches_per_min=0,
            pct_top=None
        )
    
    # Merge contiguous same-label segments into turns
    turns = []
    for s, e, l in diar:
        if not turns or turns[-1][2] != l:
            turns.append([s, e, l])
        else:
            turns[-1][1] = e
    
    # Calculate statistics
    n_turns = len(turns)
    labels = sorted({l for _, _, l in turns})
    
    # Find first speaker change
    first_split = None
    seen = {turns[0][2]}
    for s, e, l in turns:
        if l not in seen and first_split is None:
            first_split = s
        seen.add(l)
    
    # Time per speaker
    per = {}
    for s, e, l in turns:
        per[l] = per.get(l, 0.0) + (e - s)
    
    pct_top = 100.0 * max(per.values()) / max(duration, 1e-9) if per else 0
    avg_turn = sum(e - s for s, e, _ in turns) / max(1, len(turns))
    
    # Switches per minute
    switches = sum(1 for i in range(1, len(turns)) if turns[i][2] != turns[i-1][2])
    dur_min = max((turns[-1][1] - turns[0][0]) / 60.0, 1e-9)
    spm = switches / dur_min
    
    return dict(
        n_speakers=len(labels),
        n_turns=n_turns,
        avg_turn_s=round(avg_turn, 2),
        first_split_s=(None if first_split is None else round(first_split, 2)),
        switches_per_min=round(spm, 2),
        pct_top=round(pct_top, 1)
    )
