"""
ASR + Diarization using faster-whisper + pyannote.audio v4

Replaces WhisperX with a simpler, more maintainable solution:
- Transcription: faster-whisper (CTranslate2) with word timestamps
- Diarization: pyannote.audio v4 "pyannote/speaker-diarization-community-1" with exclusive=True
- Simple in-process merger that assigns speakers to words

Benefits:
- No WhisperX dependency conflicts
- Faster and more reliable
- Better speaker separation with exclusive mode
- Cleaner API and easier to maintain
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from faster_whisper import WhisperModel
from pyannote.audio import Pipeline

logger = logging.getLogger(__name__)


# ---------- Data models ----------

@dataclass
class WordItem:
    """Single word with timing and optional speaker"""
    start: float
    end: float
    word: str
    prob: Optional[float] = None
    speaker: Optional[str] = None


@dataclass
class Turn:
    """Speaker turn from diarization"""
    start: float
    end: float
    speaker: str


@dataclass
class TranscriptSegment:
    """Segment with text and speaker attribution"""
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    words: Optional[List[WordItem]] = None


# ---------- ASR (faster-whisper) ----------

def transcribe_words(
    audio_path: str | Path,
    model_name: str = "large-v3",
    device: str = "auto",
    compute_type: str = "float16",
    beam_size: int = 5,
    language: Optional[str] = None,
    vad_filter: bool = True,
) -> List[WordItem]:
    """
    Transcribe audio to word-level items using faster-whisper.
    
    Args:
        audio_path: Path to audio file
        model_name: Whisper model name (e.g., "large-v3", "distil-large-v3")
        device: "cuda", "cpu", or "auto"
        compute_type: "float16", "int8", "int8_float16"
        beam_size: Beam size for decoding
        language: Language code or None for auto-detect
        vad_filter: Use VAD to filter silence
    
    Returns:
        List of WordItem with start/end/word/prob
    """
    logger.info(f"Loading faster-whisper model: {model_name} on {device}")
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    
    logger.info(f"Transcribing: {audio_path}")
    segments, info = model.transcribe(
        str(audio_path),
        vad_filter=vad_filter,
        vad_parameters=dict(min_silence_duration_ms=250) if vad_filter else None,
        word_timestamps=True,
        beam_size=beam_size,
        language=language,
    )
    
    logger.info(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
    
    words: List[WordItem] = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                words.append(WordItem(
                    start=float(w.start),
                    end=float(w.end),
                    word=w.word,
                    prob=getattr(w, "probability", None)
                ))
    
    logger.info(f"Extracted {len(words)} words")
    return words


# ---------- Diarization (pyannote v4) ----------

def diarize_turns(
    audio_path: str | Path,
    hf_token: Optional[str] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
) -> List[Turn]:
    """
    Perform speaker diarization using pyannote.audio v4.
    
    Args:
        audio_path: Path to audio file
        hf_token: HuggingFace token for gated models
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers
    
    Returns:
        List of Turn with start/end/speaker (non-overlapping due to exclusive=True)
    """
    import torch
    
    logger.info("Loading pyannote speaker-diarization-community-1 pipeline")
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-community-1",
        token=hf_token  # Changed from use_auth_token in pyannote v4
    )
    
    # Build diarization parameters
    params = {}
    if min_speakers is not None:
        params['min_speakers'] = min_speakers
    if max_speakers is not None:
        params['max_speakers'] = max_speakers
    
    # WORKAROUND for AudioDecoder error: Preload audio with librosa
    # pyannote v4 has issues with torchcodec on Windows
    # soundfile can't read MP4, so use librosa which handles all formats
    logger.info(f"Preloading audio to avoid AudioDecoder error: {audio_path}")
    try:
        import librosa
        import numpy as np
        
        # Load audio with librosa (handles MP4, WAV, etc.)
        waveform, sample_rate = librosa.load(str(audio_path), sr=16000, mono=True)
        
        # Convert to torch tensor and ensure correct shape (channels, samples)
        waveform = waveform[None, :]  # Add channel dimension (1, samples)
        waveform_tensor = torch.from_numpy(waveform).float()
        
        # Pass preloaded audio as dict to avoid file loading
        audio_dict = {
            "waveform": waveform_tensor,
            "sample_rate": sample_rate
        }
        
        logger.info(f"Running diarization with exclusive=True, params: {params}")
        diarization = pipeline(audio_dict, exclusive=True, **params)
    except Exception as e:
        logger.warning(f"Preloading failed, falling back to file path: {e}")
        # Fallback to direct file path (may fail with AudioDecoder error)
        diarization = pipeline(str(audio_path), exclusive=True, **params)
    
    turns: List[Turn] = []
    for segment, _, speaker in diarization.itertracks(yield_label=True):
        turns.append(Turn(
            start=float(segment.start),
            end=float(segment.end),
            speaker=str(speaker)
        ))
    
    logger.info(f"Detected {len(set(t.speaker for t in turns))} speakers in {len(turns)} turns")
    return turns


# ---------- Word-Speaker Assignment ----------

def assign_speakers_to_words(
    words: List[WordItem],
    turns: List[Turn]
) -> List[WordItem]:
    """
    Assign speaker labels to words based on diarization turns.
    
    Uses word midpoint to determine which turn it belongs to.
    
    Args:
        words: List of WordItem from transcription
        turns: List of Turn from diarization
    
    Returns:
        List of WordItem with speaker labels assigned
    """
    if not turns:
        logger.warning("No diarization turns provided, words will have no speaker labels")
        return words
    
    # Sort turns by start time for efficient lookup
    turns_sorted = sorted(turns, key=lambda t: t.start)
    
    assigned_count = 0
    for word in words:
        # Use word midpoint for assignment
        word_mid = (word.start + word.end) / 2
        
        # Find the turn that contains this word
        for turn in turns_sorted:
            if turn.start <= word_mid < turn.end:
                word.speaker = turn.speaker
                assigned_count += 1
                break
        
        # If no turn found, leave speaker as None
    
    logger.info(f"Assigned speakers to {assigned_count}/{len(words)} words")
    return words


# ---------- Segment Creation ----------

def words_to_segments(
    words: List[WordItem],
    max_segment_length: float = 30.0,
    max_words_per_segment: int = 50
) -> List[TranscriptSegment]:
    """
    Group words into segments based on speaker changes and length limits.
    
    Args:
        words: List of WordItem with speaker labels
        max_segment_length: Maximum segment duration in seconds
        max_words_per_segment: Maximum words per segment
    
    Returns:
        List of TranscriptSegment
    """
    if not words:
        return []
    
    segments: List[TranscriptSegment] = []
    current_words: List[WordItem] = []
    current_speaker: Optional[str] = None
    segment_start: Optional[float] = None
    
    for word in words:
        # Start new segment if:
        # 1. Speaker changed
        # 2. Segment too long (duration)
        # 3. Too many words
        should_split = False
        
        if current_words:
            duration = word.end - segment_start
            if (word.speaker != current_speaker or
                duration > max_segment_length or
                len(current_words) >= max_words_per_segment):
                should_split = True
        
        if should_split:
            # Save current segment
            text = " ".join(w.word for w in current_words)
            segments.append(TranscriptSegment(
                start=segment_start,
                end=current_words[-1].end,
                text=text,
                speaker=current_speaker,
                words=current_words.copy()
            ))
            current_words = []
            current_speaker = None
            segment_start = None
        
        # Add word to current segment
        if not current_words:
            segment_start = word.start
            current_speaker = word.speaker
        current_words.append(word)
    
    # Save final segment
    if current_words:
        text = " ".join(w.word for w in current_words)
        segments.append(TranscriptSegment(
            start=segment_start,
            end=current_words[-1].end,
            text=text,
            speaker=current_speaker,
            words=current_words.copy()
        ))
    
    logger.info(f"Created {len(segments)} segments from {len(words)} words")
    return segments


# ---------- Main Pipeline ----------

def transcribe_and_diarize(
    audio_path: str | Path,
    model_name: str = "large-v3",
    device: str = "auto",
    compute_type: str = "float16",
    hf_token: Optional[str] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
    enable_diarization: bool = True,
) -> List[TranscriptSegment]:
    """
    Complete pipeline: transcribe + diarize + merge.
    
    Args:
        audio_path: Path to audio file
        model_name: Whisper model name
        device: "cuda", "cpu", or "auto"
        compute_type: "float16", "int8", "int8_float16"
        hf_token: HuggingFace token for pyannote
        min_speakers: Minimum speakers for diarization
        max_speakers: Maximum speakers for diarization
        enable_diarization: Whether to perform diarization
    
    Returns:
        List of TranscriptSegment with speaker labels
    """
    logger.info(f"Starting transcription + diarization pipeline for: {audio_path}")
    
    # Step 1: Transcribe to words
    words = transcribe_words(
        audio_path=audio_path,
        model_name=model_name,
        device=device,
        compute_type=compute_type
    )
    
    # Step 2: Diarize (if enabled)
    if enable_diarization:
        turns = diarize_turns(
            audio_path=audio_path,
            hf_token=hf_token,
            min_speakers=min_speakers,
            max_speakers=max_speakers
        )
        
        # Step 3: Assign speakers to words
        words = assign_speakers_to_words(words, turns)
    else:
        logger.info("Diarization disabled, all words will have no speaker labels")
    
    # Step 4: Group words into segments
    segments = words_to_segments(words)
    
    logger.info(f"Pipeline complete: {len(segments)} segments")
    return segments


# ---------- Utility Functions ----------

def get_speaker_stats(segments: List[TranscriptSegment]) -> Dict[str, Any]:
    """Get statistics about speakers in segments"""
    speakers = {}
    total_duration = 0.0
    
    for seg in segments:
        duration = seg.end - seg.start
        total_duration += duration
        
        speaker = seg.speaker or "UNKNOWN"
        if speaker not in speakers:
            speakers[speaker] = {"count": 0, "duration": 0.0, "words": 0}
        
        speakers[speaker]["count"] += 1
        speakers[speaker]["duration"] += duration
        if seg.words:
            speakers[speaker]["words"] += len(seg.words)
    
    return {
        "total_segments": len(segments),
        "total_duration": total_duration,
        "speakers": speakers,
        "num_speakers": len(speakers)
    }
