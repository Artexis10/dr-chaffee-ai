#!/usr/bin/env python3
"""
Enhanced segments database integration for distil-large-v3 + Chaffee-aware system
Replaces the old chunks-based system with proper speaker attribution

Supports dual-write architecture:
- Legacy: segments.embedding column
- Normalized: segment_embeddings table (multi-model support)
"""

import os
import uuid
import json
import logging
import psycopg2
import psycopg2.extras
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Import embedding config helpers (with fallback for standalone usage)
try:
    from api.embedding_config import (
        get_active_model_key,
        get_model_dimensions,
        use_dual_write,
        use_normalized_storage,
    )
    _HAS_EMBEDDING_CONFIG = True
except ImportError:
    _HAS_EMBEDDING_CONFIG = False
    logger.debug("embedding_config not available, using defaults")


def _get_embedding_config_fallback():
    """Fallback embedding config when api.embedding_config is not available"""
    return {
        'model_key': os.getenv('EMBEDDING_MODEL_KEY', 'bge-small-en-v1.5'),
        'dimensions': int(os.getenv('EMBEDDING_DIMENSIONS', '384')),
        'use_dual_write': os.getenv('EMBEDDING_DUAL_WRITE', 'true').lower() in ('1', 'true', 'yes'),
        'use_normalized': os.getenv('EMBEDDING_STORAGE_STRATEGY', 'normalized') == 'normalized',
    }

class SegmentsDatabase:
    """Enhanced segments database with speaker attribution and pgvector support"""
    
    @staticmethod
    def _get_segment_value(segment, key, default=None):
        """Helper to get value from either dict or object (handles both TranscriptSegment and dict)"""
        if isinstance(segment, dict):
            return segment.get(key, default)
        else:
            return getattr(segment, key, default)
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.connection = None
        
    def get_connection(self):
        """Get database connection"""
        if not self.connection or self.connection.closed:
            self.connection = psycopg2.connect(self.db_url)
        else:
            # Check if connection is in a failed transaction state
            try:
                # Try to get transaction status
                status = self.connection.get_transaction_status()
                # TRANSACTION_STATUS_INERROR = 3 means transaction aborted
                if status == 3:  # psycopg2.extensions.TRANSACTION_STATUS_INERROR
                    logger.warning("Connection in failed transaction state, rolling back and resetting")
                    self.connection.rollback()
            except Exception as e:
                logger.warning(f"Error checking transaction status: {e}, reconnecting")
                try:
                    self.connection.close()
                except:
                    pass
                self.connection = psycopg2.connect(self.db_url)
        return self.connection
    
    # NOTE: get_cached_voice_embeddings was removed in Dec 2025.
    # Voice embedding / speaker ID feature is not wired end-to-end.
    # The segments.voice_embedding column was never created in production.
    # Re-introduce this method when speaker identification is properly implemented.
    
    def upsert_source(self, video_id: str, title: str, 
                     source_type: str = 'youtube', 
                     metadata: Optional[Dict] = None,
                     published_at = None,
                     duration_s = None,
                     view_count = None,
                     channel_name = None,
                     channel_url = None,
                     thumbnail_url = None,
                     like_count = None,
                     comment_count = None,
                     description = None,
                     tags = None,
                     url = None) -> int:
        """Upsert video source and return source_id"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                import json
                metadata_json = json.dumps(metadata or {})
                # Pass tags as native Python list for PostgreSQL TEXT[] - psycopg2 handles conversion
                tags_array = tags if tags else None
                
                # Use INSERT ... ON CONFLICT for true upsert
                cur.execute("""
                    INSERT INTO sources (
                        source_type, source_id, title, url, channel_name, channel_url,
                        published_at, duration_s, view_count, like_count, comment_count,
                        description, thumbnail_url, tags, metadata, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_type, source_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        url = COALESCE(EXCLUDED.url, sources.url),
                        channel_name = COALESCE(EXCLUDED.channel_name, sources.channel_name),
                        channel_url = COALESCE(EXCLUDED.channel_url, sources.channel_url),
                        published_at = COALESCE(EXCLUDED.published_at, sources.published_at),
                        duration_s = COALESCE(EXCLUDED.duration_s, sources.duration_s),
                        view_count = COALESCE(EXCLUDED.view_count, sources.view_count),
                        like_count = COALESCE(EXCLUDED.like_count, sources.like_count),
                        comment_count = COALESCE(EXCLUDED.comment_count, sources.comment_count),
                        description = COALESCE(EXCLUDED.description, sources.description),
                        thumbnail_url = COALESCE(EXCLUDED.thumbnail_url, sources.thumbnail_url),
                        tags = COALESCE(EXCLUDED.tags, sources.tags),
                        metadata = COALESCE(EXCLUDED.metadata, sources.metadata),
                        updated_at = NOW()
                    RETURNING id
                """, (source_type, video_id, title, url, channel_name, channel_url,
                      published_at, duration_s, view_count, like_count, comment_count,
                      description, thumbnail_url, tags_array, metadata_json, datetime.now()))
                
                source_id = cur.fetchone()[0]
                conn.commit()
                logger.debug(f"Upserted source {video_id} with id {source_id}")
                
                return source_id
                
        except Exception as e:
            logger.error(f"Failed to upsert source {video_id}: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            if conn:
                try:
                    conn.rollback()
                    logger.info("Transaction rolled back successfully")
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback transaction: {rollback_error}")
                    # Force reconnect on next call
                    try:
                        conn.close()
                    except:
                        pass
                    self.connection = None
            raise
    
    def batch_insert_segments(self, segments: List[Dict[str, Any]], 
                            video_id: str,
                            chaffee_only_storage: bool = False,
                            embed_chaffee_only: bool = True) -> int:
        """Batch insert segments with speaker attribution"""
        
        if not segments:
            return 0
        
        # Filter segments if chaffee_only_storage is enabled
        if chaffee_only_storage:
            segments = [seg for seg in segments if self._get_segment_value(seg, 'speaker_label') == 'Chaffee']
            logger.info(f"Chaffee-only storage: filtered to {len(segments)} Chaffee segments")
        
        if not segments:
            logger.info("No segments to insert after filtering")
            return 0
        
        try:
            conn = self.get_connection()
            inserted_count = 0
            
            with conn.cursor() as cur:
                # Get source_id from video_id (YouTube ID)
                cur.execute("SELECT id FROM sources WHERE source_id = %s", (video_id,))
                result = cur.fetchone()
                if not result:
                    logger.error(f"Source not found for video_id {video_id}")
                    return 0
                source_id = result[0]
                
                # Prepare batch insert with ON CONFLICT UPDATE to handle reprocessing
                # NOTE: voice_embedding column removed Dec 2025 - speaker ID not wired end-to-end
                insert_query = """
                    INSERT INTO segments (
                        source_id, start_sec, end_sec, speaker_label, speaker_conf,
                        text, avg_logprob, compression_ratio, no_speech_prob,
                        temperature_used, re_asr, is_overlap, needs_refinement,
                        embedding
                    ) VALUES %s
                    ON CONFLICT (source_id, start_sec, end_sec, text)
                    DO UPDATE SET
                        speaker_label = EXCLUDED.speaker_label,
                        speaker_conf = EXCLUDED.speaker_conf,
                        avg_logprob = EXCLUDED.avg_logprob,
                        compression_ratio = EXCLUDED.compression_ratio,
                        no_speech_prob = EXCLUDED.no_speech_prob,
                        temperature_used = EXCLUDED.temperature_used,
                        re_asr = EXCLUDED.re_asr,
                        is_overlap = EXCLUDED.is_overlap,
                        needs_refinement = EXCLUDED.needs_refinement,
                        embedding = EXCLUDED.embedding
                """
                
                # Helper functions for value conversion
                def to_native(val):
                    """Convert numpy types to Python native types"""
                    if val is None:
                        return None
                    if hasattr(val, 'item'):  # numpy scalar
                        return val.item()
                    return val
                
                def safe_float(val, default=0.0):
                    """Safely convert to float, handling None"""
                    if val is None:
                        return default
                    try:
                        return float(to_native(val))
                    except (ValueError, TypeError):
                        return default
                
                # Prepare values for batch insert
                values = []
                for segment in segments:
                    # Determine if this segment should get text embedding
                    embedding = None
                    if self._get_segment_value(segment, 'embedding'):
                        speaker_label = self._get_segment_value(segment, 'speaker_label', 'Guest')
                        # Only embed Chaffee segments if embed_chaffee_only is enabled
                        # CRITICAL: If speaker_label is None (speaker ID disabled), treat as Chaffee
                        if not embed_chaffee_only or speaker_label == 'Chaffee' or speaker_label is None:
                            embedding = self._get_segment_value(segment, 'embedding')
                    
                    # Clamp speaker confidence to [0.0, 1.0] range
                    speaker_conf = to_native(self._get_segment_value(segment, 'speaker_confidence', None))
                    if speaker_conf is not None:
                        speaker_conf = min(1.0, max(0.0, float(speaker_conf)))
                    
                    values.append((
                        source_id,
                        safe_float(self._get_segment_value(segment, 'start', 0.0)),
                        safe_float(self._get_segment_value(segment, 'end', 0.0)),
                        self._get_segment_value(segment, 'speaker_label', 'Guest'),
                        speaker_conf,
                        self._get_segment_value(segment, 'text', ''),
                        to_native(self._get_segment_value(segment, 'avg_logprob', None)),
                        to_native(self._get_segment_value(segment, 'compression_ratio', None)),
                        to_native(self._get_segment_value(segment, 'no_speech_prob', None)),
                        safe_float(self._get_segment_value(segment, 'temperature_used', 0.0)),
                        bool(self._get_segment_value(segment, 're_asr', False)),
                        bool(self._get_segment_value(segment, 'is_overlap', False)),
                        bool(self._get_segment_value(segment, 'needs_refinement', False)),
                        embedding
                    ))
                # Execute batch insert/update
                psycopg2.extras.execute_values(cur, insert_query, values)
                affected_count = cur.rowcount  # Rows inserted or updated
                total_segments = len(values)
                
                conn.commit()
                if affected_count == total_segments:
                    logger.info(f"Successfully inserted/updated {affected_count} segments for video {video_id}")
                else:
                    logger.info(f"Successfully processed {total_segments} segments for video {video_id} ({affected_count} new/changed)")
                
                # Dual-write to segment_embeddings table if enabled
                self._dual_write_embeddings(cur, conn, source_id, segments, embed_chaffee_only)
                
                # Classify video type based on speaker distribution
                self._classify_video_type(video_id, segments, conn)
                
            return total_segments  # Return total segments processed, not just new/changed
            
        except Exception as e:
            logger.error(f"Failed to insert segments for {video_id}: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            if conn:
                try:
                    conn.rollback()
                    logger.info("Transaction rolled back successfully")
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback transaction: {rollback_error}")
                    # Force reconnect on next call
                    try:
                        conn.close()
                    except:
                        pass
                    self.connection = None
            raise
    
    def _dual_write_embeddings(self, cur, conn, source_id: int, segments: List[Dict[str, Any]], 
                                embed_chaffee_only: bool = True) -> int:
        """
        Dual-write embeddings to segment_embeddings table.
        
        This enables the normalized embedding storage architecture while maintaining
        backward compatibility with the legacy segments.embedding column.
        
        Args:
            cur: Database cursor
            conn: Database connection
            source_id: Source ID (FK to sources table)
            segments: List of segment dicts with embeddings
            embed_chaffee_only: If True, only embed Chaffee segments
            
        Returns:
            Number of embeddings written to segment_embeddings
        """
        # Check if dual-write is enabled
        if _HAS_EMBEDDING_CONFIG:
            if not use_dual_write():
                logger.debug("Dual-write disabled, skipping segment_embeddings")
                return 0
            model_key = get_active_model_key()
            dimensions = get_model_dimensions(model_key)
        else:
            config = _get_embedding_config_fallback()
            if not config['use_dual_write']:
                logger.debug("Dual-write disabled, skipping segment_embeddings")
                return 0
            model_key = config['model_key']
            dimensions = config['dimensions']
        
        # Check if segment_embeddings table exists
        try:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'segment_embeddings'
                )
            """)
            table_exists = cur.fetchone()[0]
            if not table_exists:
                logger.debug("segment_embeddings table does not exist, skipping dual-write")
                return 0
        except Exception as e:
            logger.warning(f"Could not check segment_embeddings table: {e}")
            return 0
        
        # Collect embeddings to write
        embeddings_to_write = []
        
        for segment in segments:
            embedding = self._get_segment_value(segment, 'embedding')
            if embedding is None:
                continue
            
            speaker_label = self._get_segment_value(segment, 'speaker_label', 'Guest')
            
            # Apply same filtering as legacy write
            if embed_chaffee_only and speaker_label != 'Chaffee' and speaker_label is not None:
                continue
            
            # Get segment ID by matching on unique constraint
            start_sec = self._get_segment_value(segment, 'start', 0.0)
            end_sec = self._get_segment_value(segment, 'end', 0.0)
            text = self._get_segment_value(segment, 'text', '')
            
            embeddings_to_write.append({
                'source_id': source_id,
                'start_sec': float(start_sec) if start_sec else 0.0,
                'end_sec': float(end_sec) if end_sec else 0.0,
                'text': text,
                'embedding': embedding,
            })
        
        if not embeddings_to_write:
            logger.debug("No embeddings to dual-write")
            return 0
        
        # Batch insert into segment_embeddings
        try:
            # Use a single query to get segment IDs and insert embeddings
            insert_count = 0
            batch_size = 1000
            
            for i in range(0, len(embeddings_to_write), batch_size):
                batch = embeddings_to_write[i:i + batch_size]
                
                # Build values for batch insert
                values = []
                for emb_data in batch:
                    # Get segment_id from the segments table
                    cur.execute("""
                        SELECT id FROM segments 
                        WHERE source_id = %s AND start_sec = %s AND end_sec = %s AND text = %s
                        LIMIT 1
                    """, (emb_data['source_id'], emb_data['start_sec'], emb_data['end_sec'], emb_data['text']))
                    
                    result = cur.fetchone()
                    if result:
                        segment_id = result[0]
                        embedding = emb_data['embedding']
                        
                        # Convert embedding to list if needed
                        if hasattr(embedding, 'tolist'):
                            embedding = embedding.tolist()
                        
                        values.append((segment_id, model_key, dimensions, embedding))
                
                if values:
                    # Batch insert with ON CONFLICT
                    psycopg2.extras.execute_values(
                        cur,
                        """
                        INSERT INTO segment_embeddings (segment_id, model_key, dimensions, embedding, is_active)
                        VALUES %s
                        ON CONFLICT (segment_id, model_key) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            dimensions = EXCLUDED.dimensions,
                            created_at = now()
                        """,
                        values,
                        template="(%s, %s, %s, %s::vector, TRUE)"
                    )
                    insert_count += len(values)
            
            conn.commit()
            
            if insert_count > 0:
                logger.info(f"Dual-write: {insert_count} embeddings written to segment_embeddings (model: {model_key})")
            
            return insert_count
            
        except Exception as e:
            logger.warning(f"Dual-write to segment_embeddings failed (non-fatal): {e}")
            # Don't raise - dual-write failure should not break ingestion
            try:
                conn.rollback()
            except:
                pass
            return 0
    
    def _classify_video_type(self, video_id: str, segments: List[Dict[str, Any]], conn) -> None:
        """Classify video type based on speaker distribution and update all segments."""
        try:
            # Extract speaker labels
            speaker_labels = [
                self._get_segment_value(seg, 'speaker_label') 
                for seg in segments 
                if self._get_segment_value(seg, 'speaker_label')
            ]
            
            # Initialize stats
            num_speakers = 0
            guest_pct = 0.0
            
            if not speaker_labels:
                video_type = 'monologue'  # Default
            else:
                # Calculate speaker statistics
                num_speakers = len(set(speaker_labels))
                guest_count = sum(1 for s in speaker_labels if s == 'Guest')
                guest_pct = guest_count / len(speaker_labels) if speaker_labels else 0
                
                # Classify based on speaker distribution
                if num_speakers == 1:
                    video_type = 'monologue'
                elif guest_pct > 0.15:
                    video_type = 'interview'
                else:
                    video_type = 'monologue_with_clips'
            
            # Update all segments for this video using source_id FK
            with conn.cursor() as cur:
                # Get source_id from video_id (YouTube ID)
                cur.execute("SELECT id FROM sources WHERE source_id = %s", (video_id,))
                result = cur.fetchone()
                if result:
                    source_id = result[0]
                    cur.execute("""
                        UPDATE segments 
                        SET video_type = %s 
                        WHERE source_id = %s
                    """, (video_type, source_id))
                    conn.commit()
                    logger.info(f"Classified video {video_id} as '{video_type}' ({num_speakers} speaker(s), {guest_pct*100:.1f}% guest)")
                else:
                    logger.warning(f"Source not found for video_id {video_id}, skipping video type classification")
            
        except Exception as e:
            logger.warning(f"Failed to classify video type for {video_id}: {e}")
            # Don't raise - classification is non-critical
    
    def check_video_exists(self, video_id: str) -> Tuple[Optional[int], int]:
        """Check if video exists and return source_id and segment count"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                # Check if source exists
                cur.execute(
                    "SELECT id FROM sources WHERE source_type = 'youtube' AND source_id = %s",
                    (video_id,)
                )
                result = cur.fetchone()
                
                if not result:
                    return None, 0
                
                source_id = result[0]
                
                # Count existing segments using source_id FK
                cur.execute(
                    "SELECT COUNT(*) FROM segments WHERE source_id = %s",
                    (source_id,)
                )
                segment_count = cur.fetchone()[0]
                
                return source_id, segment_count
                
        except Exception as e:
            logger.error(f"Failed to check video existence for {video_id}: {e}")
            # Ensure rollback on error
            try:
                conn = self.get_connection()
                if conn and not conn.closed:
                    conn.rollback()
            except:
                pass
            return None, 0
    
    def get_video_stats(self, video_id: str) -> Dict[str, Any]:
        """Get comprehensive video statistics"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Get source_id from video_id (YouTube ID)
                cur.execute("SELECT id FROM sources WHERE source_id = %s", (video_id,))
                result = cur.fetchone()
                if not result:
                    logger.warning(f"Source not found for video_id {video_id}")
                    return {}
                source_id = result[0]
                
                # Get segment statistics using source_id FK
                cur.execute("""
                    SELECT 
                        speaker_label,
                        COUNT(*) as segment_count,
                        SUM(end_sec - start_sec) as total_duration,
                        AVG(speaker_conf) as avg_confidence,
                        COUNT(*) FILTER (WHERE re_asr = true) as refined_count,
                        COUNT(*) FILTER (WHERE embedding IS NOT NULL) as embedded_count
                    FROM segments 
                    WHERE source_id = %s 
                    GROUP BY speaker_label
                """, (source_id,))
                
                speaker_stats = {}
                total_segments = 0
                total_duration = 0.0
                
                for row in cur.fetchall():
                    speaker_label = row['speaker_label']
                    speaker_stats[speaker_label] = {
                        'segment_count': row['segment_count'],
                        'duration': float(row['total_duration'] or 0),
                        'avg_confidence': float(row['avg_confidence'] or 0),
                        'refined_count': row['refined_count'],
                        'embedded_count': row['embedded_count']
                    }
                    total_segments += row['segment_count']
                    total_duration += float(row['total_duration'] or 0)
                
                # Calculate percentages
                for speaker, stats in speaker_stats.items():
                    if total_duration > 0:
                        stats['percentage'] = (stats['duration'] / total_duration) * 100
                    else:
                        stats['percentage'] = 0
                
                return {
                    'video_id': video_id,
                    'total_segments': total_segments,
                    'total_duration': total_duration,
                    'speaker_stats': speaker_stats,
                    'chaffee_percentage': speaker_stats.get('Chaffee', {}).get('percentage', 0)
                }
                
        except Exception as e:
            logger.error(f"Failed to get video stats for {video_id}: {e}")
            return {}
    
    def create_embedding_index(self):
        """Create pgvector index for embeddings (run after bulk loading)"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                logger.info("Creating pgvector index for embeddings...")
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS segments_embedding_idx
                    ON segments USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)
                """)
                conn.commit()
                logger.info("pgvector index created successfully")
                
        except Exception as e:
            logger.error(f"Failed to create embedding index: {e}")
            if conn:
                conn.rollback()
            raise
    
    def cleanup_old_segments(self, video_id: str):
        """Remove existing segments for a video (for re-processing)"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                # Get source_id from video_id (YouTube ID)
                cur.execute("SELECT id FROM sources WHERE source_id = %s", (video_id,))
                result = cur.fetchone()
                if not result:
                    logger.warning(f"Source not found for video_id {video_id}, nothing to cleanup")
                    return
                source_id = result[0]
                
                cur.execute("DELETE FROM segments WHERE source_id = %s", (source_id,))
                deleted_count = cur.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} existing segments for {video_id}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup segments for {video_id}: {e}")
            if conn:
                conn.rollback()
            raise
    
    def close(self):
        """Close database connection"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            self.connection = None
