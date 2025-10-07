#!/usr/bin/env python3
"""
Voice enrollment system with optimized audio loading
"""

import os
import json
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import threading

logger = logging.getLogger(__name__)

# Global cache for profiles to avoid reloading
_profile_cache = {}
_profile_cache_lock = threading.Lock()

class VoiceEnrollment:
    """Voice enrollment and speaker identification system"""
    
    def __init__(self, voices_dir: str = 'voices'):
        self.voices_dir = Path(voices_dir)
        self.voices_dir.mkdir(exist_ok=True)
        
        # Lazy-loaded models
        self._embedding_model = None
        self._device = None
        
        logger.info(f"Voice enrollment initialized with profiles directory: {self.voices_dir}")
    
    def _get_embedding_model(self):
        """Lazy-load SpeechBrain ECAPA-TDNN model with Windows-safe loading"""
        if self._embedding_model is None:
            import torch
            from speechbrain.inference.speaker import EncoderClassifier
            import os
            import shutil
            from pathlib import Path
            
            # Determine device
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Use cache directory for models
            cache_dir = Path(os.getenv('PRETRAINED_MODELS_DIR', 'pretrained_models'))
            cache_dir.mkdir(exist_ok=True)
            
            logger.info(f"Loading SpeechBrain ECAPA-TDNN model on {self._device}")
            logger.info(f"Cache directory: {cache_dir}")
            
            # Windows workaround: Manually copy files from HF cache to avoid symlink issues
            try:
                hf_cache = Path.home() / '.cache' / 'huggingface' / 'hub' / 'models--speechbrain--spkrec-ecapa-voxceleb'
                
                if hf_cache.exists():
                    logger.info("Found HuggingFace cache, manually copying files to avoid symlink issues...")
                    
                    # Find the snapshot directory
                    snapshots_dir = hf_cache / 'snapshots'
                    if snapshots_dir.exists():
                        snapshot_dirs = list(snapshots_dir.iterdir())
                        if snapshot_dirs:
                            snapshot = snapshot_dirs[0]  # Use first (latest) snapshot
                            
                            # Copy required files (including label_encoder.txt)
                            files_to_copy = [
                                ('hyperparams.yaml', 'hyperparams.yaml'),
                                ('embedding_model.ckpt', 'embedding_model.ckpt'),
                                ('mean_var_norm_emb.ckpt', 'mean_var_norm_emb.ckpt'),
                                ('classifier.ckpt', 'classifier.ckpt'),
                                ('label_encoder.txt', 'label_encoder.ckpt'),  # Note: .txt -> .ckpt rename
                            ]
                            
                            for src_name, dst_name in files_to_copy:
                                src = snapshot / src_name
                                dst = cache_dir / dst_name
                                
                                if src.exists() and not dst.exists():
                                    logger.debug(f"Copying {src_name} -> {dst_name}...")
                                    shutil.copy2(src, dst)
                            
                            logger.info("✅ Files copied successfully")
            except Exception as e:
                logger.debug(f"Could not pre-copy files (will download): {e}")
            
            # Now load the model (files are already in place, no symlinks needed)
            try:
                self._embedding_model = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb",
                    savedir=str(cache_dir),
                    run_opts={"device": self._device}
                )
                
                logger.info(f"✅ Successfully loaded SpeechBrain ECAPA-TDNN model on {self._device}")
                
            except Exception as e:
                logger.error(f"Failed to load SpeechBrain model: {e}")
                import traceback
                traceback.print_exc()
                raise RuntimeError(f"Could not load SpeechBrain ECAPA model. Install with: pip install speechbrain") from e
        
        return self._embedding_model
    
    def list_profiles(self) -> List[str]:
        """List available voice profiles (excludes backups)"""
        profiles = []
        for file_path in self.voices_dir.glob("*.json"):
            # Skip meta files and backup profiles
            if not file_path.name.endswith(".meta.json") and "_backup_" not in file_path.name:
                profiles.append(file_path.stem)
        return profiles
    
    def load_profile(self, name: str) -> Optional[Dict]:
        """Load a voice profile by name"""
        profile_path = self.voices_dir / f"{name.lower()}.json"
        
        # Check if we have a cached profile
        with _profile_cache_lock:
            if name in _profile_cache:
                return _profile_cache[name]
        
        # Try to load from file
        if profile_path.exists():
            try:
                with open(profile_path, 'r') as f:
                    profile = json.load(f)
                    
                with _profile_cache_lock:
                    _profile_cache[name] = profile
                    
                # Log profile info
                if 'centroid' in profile:
                    logger.debug(f"Loaded profile for {name}: centroid-based ({len(profile['centroid'])} dims)")
                elif 'embeddings' in profile:
                    logger.debug(f"Loaded profile for {name}: {len(profile.get('embeddings', []))} embeddings")
                else:
                    logger.warning(f"Profile {name} has no centroid or embeddings!")
                    
                return profile
            except Exception as e:
                logger.error(f"Failed to load profile {name}: {e}")
                return None
        
        logger.error(f"Profile not found: {profile_path}")
        return None
    
    def _extract_embeddings_from_audio(self, audio_path: str) -> List[np.ndarray]:
        """Extract speaker embeddings from audio file using sliding window with robust error handling"""
        try:
            # Use soundfile for faster loading when possible
            import soundfile as sf
            import librosa
            import numpy as np
            import torch
            import os
            
            # Ensure audio_path is a string
            audio_path_str = str(audio_path)
            
            # Check if file exists
            if not os.path.exists(audio_path_str):
                logger.error(f"Audio file does not exist: {audio_path_str}")
                return []
                
            # WORKAROUND: Convert MP4 to WAV first (soundfile/librosa can't handle MP4 on Windows)
            import tempfile
            import subprocess
            import shutil
            
            # Check if it's an MP4 file and ffmpeg is available
            ffmpeg_path = shutil.which('ffmpeg')
            if audio_path_str.lower().endswith('.mp4') and ffmpeg_path:
                logger.debug(f"Converting MP4 to WAV for audio loading: {audio_path_str}")
                
                # Create temporary WAV file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
                    wav_path = tmp_wav.name
                
                try:
                    # Convert to WAV using ffmpeg
                    cmd = [
                        ffmpeg_path, '-i', audio_path_str,
                        '-ar', '16000',  # 16kHz sample rate
                        '-ac', '1',       # Mono
                        '-y',             # Overwrite
                        '-loglevel', 'error',  # Suppress output
                        wav_path
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode != 0:
                        raise Exception(f"ffmpeg failed: {result.stderr}")
                    
                    # Load the WAV file
                    audio, sr = librosa.load(wav_path, sr=16000)
                    
                finally:
                    # Clean up temp WAV
                    try:
                        if os.path.exists(wav_path):
                            os.unlink(wav_path)
                    except:
                        pass
            elif audio_path_str.lower().endswith('.mp4'):
                # ffmpeg not available, try librosa directly (may fail but worth a try)
                logger.warning("ffmpeg not found in PATH, trying librosa directly on MP4 (may fail)")
                audio, sr = librosa.load(audio_path_str, sr=16000)
            else:
                # Try soundfile first for WAV files (much faster)
                try:
                    logger.debug(f"Loading audio with soundfile: {audio_path_str}")
                    
                    with sf.SoundFile(audio_path_str) as f:
                        sr = f.samplerate
                        audio = f.read()
                        
                        # Convert to mono if needed
                        if len(audio.shape) > 1 and audio.shape[1] > 1:
                            audio = np.mean(audio, axis=1)
                        
                        # Resample to 16kHz if needed
                        if sr != 16000:
                            try:
                                import resampy
                                audio = resampy.resample(audio, sr, 16000)
                            except ImportError:
                                from scipy import signal
                                audio = signal.resample(audio, int(len(audio) * 16000 / sr))
                            sr = 16000
                
                except Exception as e:
                    # Fallback to librosa
                    logger.debug(f"Soundfile failed, using librosa: {e}")
                    audio, sr = librosa.load(audio_path_str, sr=16000)
            
            logger.debug(f"Loaded audio: {len(audio)} samples at {sr}Hz")
            
            if len(audio) == 0:
                logger.error(f"Empty audio file: {audio_path}")
                return []
                
            # Normalize audio to prevent numerical issues
            max_abs = np.max(np.abs(audio))
            if max_abs > 0:
                audio = audio / max_abs
            
            # Get embedding model
            model = self._get_embedding_model()
            if model is None:
                logger.error("Failed to get embedding model")
                return []
            
            # Extract embeddings using sliding window (smaller window for better coverage)
            window_size = 3 * sr  # 3 seconds
            stride = 1.5 * sr  # 1.5 seconds
            
            # Ensure audio is long enough for at least one window
            if len(audio) < window_size:
                # Pad audio if it's too short
                padding = np.zeros(window_size - len(audio))
                audio = np.concatenate([audio, padding])
            
            # OPTIMIZATION: Batch process segments instead of one-by-one
            # Collect all segments first
            segments = []
            segment_indices = []
            for start in range(0, len(audio) - window_size + 1, int(stride)):
                end = start + window_size
                segment = audio[start:end]
                
                # Skip segments with very low energy (likely silence)
                if np.mean(np.abs(segment)) < 0.0001:
                    continue
                
                segments.append(segment)
                segment_indices.append(start)
            
            if not segments:
                logger.warning("No valid segments found in audio")
                return []
            
            # Batch process all segments at once (much faster!)
            embeddings = []
            batch_size = 32  # Process 32 segments at a time
            
            logger.info(f"Processing {len(segments)} segments in batches of {batch_size}")
            
            for batch_start in range(0, len(segments), batch_size):
                batch_end = min(batch_start + batch_size, len(segments))
                batch_segments = segments[batch_start:batch_end]
                
                try:
                    # Stack segments into batch tensor
                    batch_tensor = torch.tensor(np.stack(batch_segments), dtype=torch.float32)
                    
                    # Move to correct device
                    if self._device:
                        batch_tensor = batch_tensor.to(self._device)
                    
                    # Extract embeddings for entire batch
                    with torch.no_grad():
                        batch_embeddings = model.encode_batch(batch_tensor)
                        
                        # Convert to numpy
                        if hasattr(batch_embeddings, 'cpu'):
                            batch_embeddings_np = batch_embeddings.cpu().numpy()
                        else:
                            batch_embeddings_np = np.array(batch_embeddings)
                        
                        # Add each embedding to list
                        for i in range(len(batch_segments)):
                            emb = batch_embeddings_np[i] if batch_embeddings_np.ndim > 1 else batch_embeddings_np
                            embeddings.append(emb.astype(np.float64))
                    
                    logger.debug(f"✅ Batch {batch_start//batch_size + 1}: Processed {len(batch_segments)} segments")
                            
                except Exception as batch_error:
                    logger.error(f"❌ Batch processing failed, falling back to sequential: {batch_error}")
                    import traceback
                    traceback.print_exc()
                    # Fallback to sequential processing for this batch
                    for segment in batch_segments:
                        try:
                            segment_tensor = torch.tensor(segment, dtype=torch.float32).unsqueeze(0)
                            if self._device:
                                segment_tensor = segment_tensor.to(self._device)
                            
                            with torch.no_grad():
                                embedding = model.encode_batch(segment_tensor)
                                embedding_np = embedding.squeeze().cpu().numpy() if hasattr(embedding, 'squeeze') else np.array(embedding)
                                if embedding_np.size > 0:
                                    embeddings.append(embedding_np.astype(np.float64))
                        except Exception as e:
                            continue
                    
            logger.info(f"Extracted {len(embeddings)} embeddings from {audio_path}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to extract embeddings: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def compute_embedding(self, audio_path: Union[str, Path]) -> Optional[np.ndarray]:
        """Compute voice embedding from audio file using optimized loading"""
        try:
            # Use soundfile for faster loading when possible
            import soundfile as sf
            import librosa
            import numpy as np
            import torch
            
            # Try soundfile first (much faster)
            try:
                audio_path_str = str(audio_path)
                logger.debug(f"Loading audio with soundfile: {audio_path_str}")
                
                # Use chunks to avoid loading entire file for long audio
                with sf.SoundFile(audio_path_str) as f:
                    sr = f.samplerate
                    # Only read first 30 seconds max for voice profile
                    max_samples = min(sr * 30, f.frames)
                    audio = f.read(max_samples)
                    
                    # Convert to mono if needed
                    if len(audio.shape) > 1 and audio.shape[1] > 1:
                        audio = np.mean(audio, axis=1)
                    
                    # Resample to 16kHz if needed
                    if sr != 16000:
                        import resampy
                        audio = resampy.resample(audio, sr, 16000)
                        sr = 16000
            
            except Exception as e:
                # Fallback to librosa
                logger.debug(f"Soundfile failed, using librosa: {e}")
                audio, sr = librosa.load(audio_path, sr=16000, duration=30)  # Only load 30s max
            
            logger.debug(f"Loaded audio: {len(audio)} samples at {sr}Hz")
            
            # Get embedding model
            model = self._get_embedding_model()
            
            # Convert to tensor and move to device
            audio_tensor = torch.tensor(audio, dtype=torch.float32).unsqueeze(0)
            if self._device:
                audio_tensor = audio_tensor.to(self._device)
            
            with torch.no_grad():
                embedding = model.encode_batch(audio_tensor)
                embedding = embedding.squeeze().cpu().numpy()
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to compute embedding: {e}")
            return None
    
    def compute_similarity(self, embedding1, embedding2) -> float:
        """Compute cosine similarity between two embeddings or between embedding and profile"""
        try:
            # Handle case where embedding2 is a profile dictionary
            if isinstance(embedding2, dict) and 'embeddings' in embedding2:
                # Compare with all embeddings in profile and return max similarity
                profile_embeddings = embedding2['embeddings']
                similarities = []
                
                # Use a subset of profile embeddings for efficiency
                max_embeddings = 10  # Use at most 10 embeddings for comparison
                step = max(1, len(profile_embeddings) // max_embeddings)
                
                for i in range(0, len(profile_embeddings), step):
                    if len(similarities) >= max_embeddings:
                        break
                        
                    profile_emb = profile_embeddings[i]
                    sim = self._compute_single_similarity(embedding1, profile_emb)
                    similarities.append(sim)
                
                # Return max similarity with any profile embedding
                return max(similarities) if similarities else 0.0
            
            # Handle case where embedding2 is a profile with centroid (older format)
            elif isinstance(embedding2, dict) and 'centroid' in embedding2:
                # Use the centroid for comparison
                return self._compute_single_similarity(embedding1, embedding2['centroid'])
            else:
                # Direct comparison between two embeddings
                return self._compute_single_similarity(embedding1, embedding2)
                
        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            return 0.0
            
    def _compute_single_similarity(self, embedding1, embedding2) -> float:
        """Compute cosine similarity between two individual embeddings"""
        try:
            # Ensure both embeddings are numpy arrays with the same dtype
            if isinstance(embedding1, list):
                embedding1 = np.array(embedding1, dtype=np.float64)
            if isinstance(embedding2, list):
                embedding2 = np.array(embedding2, dtype=np.float64)
                
            # Handle torch tensors
            if hasattr(embedding1, 'detach') and hasattr(embedding1, 'cpu') and hasattr(embedding1, 'numpy'):
                embedding1 = embedding1.detach().cpu().numpy()
            if hasattr(embedding2, 'detach') and hasattr(embedding2, 'cpu') and hasattr(embedding2, 'numpy'):
                embedding2 = embedding2.detach().cpu().numpy()
                
            # Convert to float64 to avoid type mismatch
            embedding1 = embedding1.astype(np.float64)
            embedding2 = embedding2.astype(np.float64)
            
            # Ensure embeddings are flattened
            embedding1 = embedding1.flatten()
            embedding2 = embedding2.flatten()
            
            # Ensure embeddings have the same length
            min_len = min(len(embedding1), len(embedding2))
            if min_len == 0:
                return 0.0
                
            embedding1 = embedding1[:min_len]
            embedding2 = embedding2[:min_len]
            
            # Manual cosine similarity calculation (more reliable than sklearn)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            # Compute dot product and divide by norms
            dot_product = np.dot(embedding1, embedding2)
            similarity = dot_product / (norm1 * norm2)
            
            # Ensure it's a native Python float
            return float(similarity)
                
        except Exception as e:
            logger.error(f"Failed to compute single similarity: {e}")
            return 0.0
    
    def enroll_speaker(self, name: str, audio_sources: List[str], overwrite: bool = False, update: bool = False, min_duration: float = 30.0) -> Optional[Dict]:
        """
        Enroll a speaker from audio sources
        
        Args:
            name: Name for the speaker profile
            audio_sources: List of audio sources (file paths or YouTube URLs)
            overwrite: Whether to overwrite existing profile
            update: Whether to update existing profile
            min_duration: Minimum audio duration required
            
        Returns:
            Speaker profile dictionary if successful, None otherwise
        """
        try:
            # Check if profile exists
            profile_path = self.voices_dir / f"{name.lower()}.json"
            
            if profile_path.exists():
                if not (overwrite or update):
                    logger.error(f"Profile '{name}' already exists. Use overwrite=True or update=True")
                    return None
                    
                if update:
                    # Load existing profile
                    with open(profile_path, 'r', encoding='utf-8') as f:
                        profile = json.load(f)
                        
                    # Get existing embeddings
                    existing_embeddings = [np.array(emb) for emb in profile.get('embeddings', [])]
                    logger.info(f"Loaded {len(existing_embeddings)} existing embeddings from profile '{name}'")
                else:
                    # For overwrite, start with empty embeddings
                    existing_embeddings = []
            else:
                # New profile
                existing_embeddings = []
            
            # Process new sources
            all_embeddings = list(existing_embeddings)  # Start with existing embeddings if updating
            processed_sources = []
            total_duration = 0.0
            
            # Process each audio source
            for source in audio_sources:
                logger.info(f"Processing audio source: {source}")
                
                # Handle YouTube URLs
                if source.startswith('http') and ('youtube.com' in source or 'youtu.be' in source):
                    # Extract video ID
                    import re
                    video_id = None
                    patterns = [
                        r'(?:youtube\.com/watch\?v=|youtu.be/)([a-zA-Z0-9_-]+)',
                        r'youtube\.com/shorts/([a-zA-Z0-9_-]+)'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, source)
                        if match:
                            video_id = match.group(1)
                            break
                    
                    if not video_id:
                        logger.error(f"Could not extract video ID from URL: {source}")
                        continue
                    
                    # Check if audio file already exists in audio_storage
                    audio_storage_dir = Path(os.getenv('AUDIO_STORAGE_DIR', 'audio_storage'))
                    audio_file = audio_storage_dir / f"{video_id}.wav"
                    
                    if audio_file.exists():
                        logger.info(f"Using existing audio file: {audio_file}")
                        source = str(audio_file)
                    else:
                        logger.warning(f"Audio file not found for {video_id}, skipping URL: {source}")
                        continue
                
                # Handle local audio files
                if os.path.exists(source):
                    # Extract embeddings
                    embeddings = self._extract_embeddings_from_audio(source)
                    
                    if embeddings:
                        # Get audio duration
                        import librosa
                        duration = librosa.get_duration(path=source)
                        
                        if duration >= min_duration:
                            all_embeddings.extend(embeddings)
                            processed_sources.append(source)
                            total_duration += duration
                            logger.info(f"Added {len(embeddings)} embeddings from {source} ({duration:.1f}s)")
                            
                            # Clean up audio file if flag is set
                            if os.getenv('CLEANUP_AUDIO_AFTER_PROCESSING', 'false').lower() == 'true':
                                try:
                                    os.remove(source)
                                    logger.info(f"Cleaned up audio file: {source}")
                                except Exception as e:
                                    logger.warning(f"Failed to clean up {source}: {e}")
                        else:
                            logger.warning(f"Audio too short: {duration:.1f}s < {min_duration:.1f}s")
                    else:
                        logger.warning(f"No embeddings extracted from {source}")
                else:
                    logger.error(f"Audio source not found: {source}")
            
            if not all_embeddings:
                logger.error("No embeddings extracted from any source")
                return None
                
            logger.info(f"Extracted a total of {len(all_embeddings)} embeddings")
            
            # Calculate centroid
            centroid = np.mean(all_embeddings, axis=0).tolist()
            
            # Create profile
            profile = {
                'name': name.lower(),
                'centroid': centroid,
                'embeddings': [emb.tolist() for emb in all_embeddings],
                'threshold': 0.62,  # Default threshold
                'created_at': datetime.now().isoformat(),
                'audio_sources': processed_sources,
                'metadata': {
                    'source': 'voice_enrollment_optimized.py',
                    'num_embeddings': len(all_embeddings),
                    'total_duration': total_duration
                }
            }
            
            # Backup existing profile before overwriting
            if profile_path.exists():
                backup_dir = self.voices_dir / "backups"
                backup_dir.mkdir(exist_ok=True)
                
                # Create backup with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"{name.lower()}_backup_{timestamp}.json"
                
                try:
                    import shutil
                    shutil.copy2(profile_path, backup_path)
                    logger.info(f"📦 Backed up existing profile to: backups/{backup_path.name}")
                    
                    # Clean up old backups (keep only last 3)
                    backups = sorted(backup_dir.glob(f"{name.lower()}_backup_*.json"))
                    if len(backups) > 3:
                        for old_backup in backups[:-3]:
                            old_backup.unlink()
                            logger.info(f"🗑️  Removed old backup: {old_backup.name}")
                except Exception as e:
                    logger.warning(f"Failed to backup profile: {e}")
            
            # Save profile
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2)
                
            logger.info(f"✅ Successfully {'updated' if update else 'created'} profile '{name}' with {len(all_embeddings)} embeddings")
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to enroll speaker: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def identify_speaker(self, audio_path: Union[str, Path], threshold: float = 0.75) -> Tuple[Optional[str], float]:
        """Identify speaker from audio file"""
        # Compute embedding for input audio
        embedding = self.compute_embedding(audio_path)
        if embedding is None:
            return None, 0.0
        
        # Compare with all profiles
        best_match = None
        best_score = 0.0
        
        for profile_name in self.list_profiles():
            profile = self.load_profile(profile_name)
            if not profile:
                continue
            
            # Compare with profile
            similarity = self.compute_similarity(embedding, profile)
            
            if similarity > best_score:
                best_score = similarity
                best_match = profile_name
        
        # Check if best match exceeds threshold
        if best_match and best_score >= threshold:
            return best_match, best_score
        else:
            return None, best_score
