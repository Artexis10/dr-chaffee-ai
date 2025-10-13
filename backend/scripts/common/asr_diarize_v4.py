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
import os

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
    num_speakers: Optional[int] = None,
) -> List[Turn]:
    """
    Perform speaker diarization using pyannote.audio v4.
    
    Args:
        audio_path: Path to audio file
        hf_token: HuggingFace token for gated models
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers
        num_speakers: Exact number of speakers (when known)
    
    Returns:
        List of Turn with start/end/speaker (non-overlapping due to exclusive=True)
    """
    import torch
    
    # PERFORMANCE FIX: Use pyannote v3.1 (MUCH faster than v4)
    # v3.1 is 5-10x faster and doesn't have the AudioDecoder bugs
    from pathlib import Path as PathLib
    local_model_path = PathLib(__file__).parent.parent.parent / "pretrained_models" / "pyannote-speaker-diarization-3.1"
    
    if local_model_path.exists():
        logger.info(f"Loading pyannote v3.1 from local cache (FAST): {local_model_path}")
        # v3.1 doesn't need auth token for local models
        pipeline = Pipeline.from_pretrained(str(local_model_path))
    else:
        logger.info("Loading pyannote speaker-diarization-3.1 from HuggingFace")
        # Try 'token' first (v4+), fall back to 'use_auth_token' (v3.1)
        try:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=hf_token
            )
        except TypeError:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token
            )
    
    # CRITICAL: Move pipeline to GPU for 5-10x speedup
    import torch
    if torch.cuda.is_available():
        pipeline = pipeline.to(torch.device("cuda"))
        logger.info("✅ Pyannote pipeline moved to GPU")
    else:
        logger.warning("⚠️ CUDA not available, pyannote will run on CPU (slow)")
    
    # CRITICAL: Configure clustering threshold to detect distinct speakers
    # Lower threshold = more sensitive to voice differences
    # Default: 0.6 (pyannote default, merges similar voices)
    # Our setting: 0.4 (more sensitive, better for interviews)
    # Range: 0.0-1.0 (lower = more clusters, higher = fewer clusters)
    clustering_threshold = float(os.getenv('PYANNOTE_CLUSTERING_THRESHOLD', '0.4'))
    
    if hasattr(pipeline, 'clustering') and hasattr(pipeline.clustering, 'threshold'):
        old_threshold = pipeline.clustering.threshold
        pipeline.clustering.threshold = clustering_threshold
        logger.info(f"✓ Set clustering threshold: {old_threshold} → {clustering_threshold}")
    else:
        logger.warning(f"✗ Could not set clustering threshold - no clustering.threshold attribute")
    
    # Build diarization parameters
    params = {}
    if num_speakers is not None:
        # Use exact speaker count when known (more precise)
        params['num_speakers'] = num_speakers
        logger.info(f"Using exact speaker count: {num_speakers}")
    else:
        # Use bounds when exact count unknown
        if min_speakers is not None:
            params['min_speakers'] = min_speakers
        if max_speakers is not None:
            params['max_speakers'] = max_speakers
    
    # Configure for detecting short utterances (like brief guest questions)
    # NOTE: min_duration_on/off are only supported in some pyannote versions
    # Try to set them, but don't fail if not supported
    try:
        params['min_duration_on'] = 0.0  # Detect even very short speech
        params['min_duration_off'] = 0.0  # Don't require long silences between speakers
    except:
        logger.debug("min_duration_on/off not supported in this pyannote version")
    
    # PERFORMANCE: Try direct audio file first, fall back to preloaded audio if AudioDecoder fails
    logger.info(f"Running diarization on {audio_path} with params: {params}")
    
    import time
    import torchaudio
    
    start_time = time.time()
    diarization = None
    
    # Helper function to preload audio (handles MP4/video files)
    def preload_audio(path):
        import subprocess
        import tempfile
        from pathlib import Path
        
        # Check if file is MP4/video - convert to WAV first
        path_obj = Path(path)
        if path_obj.suffix.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
            # Convert to WAV using ffmpeg
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
                tmp_wav_path = tmp_wav.name
            
            try:
                logger.info(f"Converting MP4 to WAV: {path} → {tmp_wav_path}")
                result = subprocess.run([
                    'ffmpeg', '-i', str(path),
                    '-ar', '16000',  # 16kHz sample rate
                    '-ac', '1',      # Mono
                    '-y',            # Overwrite
                    '-loglevel', 'error',  # Only show errors
                    tmp_wav_path
                ], check=True, capture_output=True, text=True)
                
                logger.info(f"✅ Conversion complete, loading WAV with torchaudio")
                waveform, sample_rate = torchaudio.load(tmp_wav_path)
                
                # Clean up temp file
                try:
                    Path(tmp_wav_path).unlink()
                except:
                    pass
            except subprocess.CalledProcessError as e:
                logger.error(f"ffmpeg conversion failed: {e.stderr}")
                raise
            except Exception as e:
                logger.error(f"Failed to convert {path} to WAV: {e}")
                raise
        else:
            # Direct load for WAV/FLAC/etc
            waveform, sample_rate = torchaudio.load(str(path))
        
        # Convert to mono if needed
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        
        return {"waveform": waveform, "sample_rate": sample_rate}
    
    try:
        # Try direct file path first (works if AudioDecoder is available)
        diarization = pipeline(str(audio_path), **params)
    except (NameError, Exception) as e:
        if 'AudioDecoder' in str(e):
            # AudioDecoder not available - preload audio manually
            logger.warning(f"AudioDecoder issue: {e}, preloading audio with torchaudio")
            audio_dict = preload_audio(audio_path)
            logger.info(f"Retrying with preloaded audio (shape: {audio_dict['waveform'].shape}, sr: {audio_dict['sample_rate']})")
            
            try:
                diarization = pipeline(audio_dict, **params)
            except (TypeError, Exception) as e2:
                if 'min_duration' in str(e2):
                    # Remove unsupported params and retry
                    logger.warning("min_duration params not supported, retrying without them")
                    params_clean = {k: v for k, v in params.items() if k not in ['min_duration_on', 'min_duration_off']}
                    diarization = pipeline(audio_dict, **params_clean)
                else:
                    raise
        elif 'min_duration' in str(e):
            # min_duration params not supported
            logger.warning("min_duration params not supported, retrying without them")
            params_clean = {k: v for k, v in params.items() if k not in ['min_duration_on', 'min_duration_off']}
            diarization = pipeline(str(audio_path), **params_clean)
        else:
            raise
    
    elapsed = time.time() - start_time
    logger.info(f"Diarization completed in {elapsed:.1f}s")
    
    turns: List[Turn] = []
    
    # Use exclusive_speaker_diarization if available (community-1 feature)
    # This simplifies reconciliation with transcription timestamps
    if hasattr(diarization, 'exclusive_speaker_diarization'):
        logger.info("Using exclusive speaker diarization for better timestamp alignment")
        diarization_to_use = diarization.exclusive_speaker_diarization
    else:
        diarization_to_use = diarization
    
    for segment, _, speaker in diarization_to_use.itertracks(yield_label=True):
        turns.append(Turn(
            start=float(segment.start),
            end=float(segment.end),
            speaker=str(speaker)
        ))
    
    num_speakers = len(set(t.speaker for t in turns))
    logger.info(f"Detected {num_speakers} speakers in {len(turns)} turns")
    
    # Log speaker distribution
    from collections import Counter
    speaker_times = Counter()
    for turn in turns:
        speaker_times[turn.speaker] += turn.end - turn.start
    
    logger.info("Speaker time distribution:")
    for speaker, duration in speaker_times.most_common():
        pct = (duration / sum(speaker_times.values())) * 100
        logger.info(f"  {speaker}: {duration:.1f}s ({pct:.1f}%)")
    
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
