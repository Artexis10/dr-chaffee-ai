#!/usr/bin/env python3
"""
Sync local database to production without overwriting existing data.

This script safely replicates new segments and sources from local to production.
"""
import os
import sys
import logging
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


def get_connection(db_url: str):
    """Get database connection."""
    return psycopg2.connect(db_url)


def get_last_sync_time(prod_conn) -> datetime:
    """Get the timestamp of the last sync."""
    cur = prod_conn.cursor()
    try:
        # Check if sync_log table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'sync_log'
            )
        """)
        if not cur.fetchone()[0]:
            # Create sync_log table
            cur.execute("""
                CREATE TABLE sync_log (
                    id SERIAL PRIMARY KEY,
                    sync_time TIMESTAMP NOT NULL,
                    sources_synced INTEGER,
                    segments_synced INTEGER
                )
            """)
            prod_conn.commit()
            logger.info("Created sync_log table")
            return datetime(2000, 1, 1)  # Sync everything
        
        # Get last sync time
        cur.execute("SELECT MAX(sync_time) FROM sync_log")
        last_sync = cur.fetchone()[0]
        return last_sync or datetime(2000, 1, 1)
    finally:
        cur.close()


def sync_sources(local_conn, prod_conn, since: datetime) -> int:
    """Sync sources created after 'since' timestamp."""
    local_cur = local_conn.cursor()
    prod_cur = prod_conn.cursor()
    
    try:
        # Get new sources from local
        local_cur.execute("""
            SELECT id, source_type, source_id, title, published_at, duration_s,
                   view_count, metadata, created_at, channel_name, channel_url,
                   thumbnail_url, like_count, comment_count, tags, description, url
            FROM sources
            WHERE created_at > %s
            ORDER BY created_at
        """, (since,))
        
        new_sources = local_cur.fetchall()
        logger.info(f"Found {len(new_sources)} new sources to sync")
        
        synced = 0
        for source in new_sources:
            # Check if source already exists in production
            prod_cur.execute("SELECT id FROM sources WHERE source_id = %s", (source[2],))
            if prod_cur.fetchone():
                logger.debug(f"Source {source[2]} already exists, skipping")
                continue
            
            # Convert dict/list to Json for JSONB columns (metadata, tags)
            source_data = list(source[1:])
            # metadata is at index 6 in source_data (after skipping id)
            if source_data[6] is not None and isinstance(source_data[6], dict):
                source_data[6] = psycopg2.extras.Json(source_data[6])
            # tags is at index 13 in source_data (after skipping id)
            if source_data[13] is not None and isinstance(source_data[13], (dict, list)):
                source_data[13] = psycopg2.extras.Json(source_data[13])
            
            # Insert source
            prod_cur.execute("""
                INSERT INTO sources (
                    source_type, source_id, title, published_at, duration_s,
                    view_count, metadata, created_at, channel_name, channel_url,
                    thumbnail_url, like_count, comment_count, tags, description, url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_type, source_id) DO NOTHING
            """, source_data)
            synced += 1
        
        prod_conn.commit()
        logger.info(f"✅ Synced {synced} sources")
        return synced
    finally:
        local_cur.close()
        prod_cur.close()


def sync_segments(local_conn, prod_conn, since: datetime) -> int:
    """Sync segments created after 'since' timestamp."""
    local_cur = local_conn.cursor()
    prod_cur = prod_conn.cursor()
    
    try:
        # Get new segments from local (including voice_embedding)
        local_cur.execute("""
            SELECT video_id, start_sec, end_sec, speaker_label, speaker_conf,
                   text, avg_logprob, compression_ratio, no_speech_prob,
                   temperature_used, re_asr, is_overlap, needs_refinement,
                   embedding, voice_embedding, created_at
            FROM segments
            WHERE created_at > %s
            ORDER BY created_at
        """, (since,))
        
        new_segments = local_cur.fetchall()
        logger.info(f"Found {len(new_segments)} new segments to sync")
        
        synced = 0
        batch_size = 1000
        batch = []
        
        for segment in new_segments:
            # Convert voice_embedding to Json if present
            segment_data = list(segment)
            # voice_embedding is at index 14 (15th column)
            if segment_data[14] is not None:
                # Convert dict or list to Json for JSONB column
                if isinstance(segment_data[14], (dict, list)):
                    segment_data[14] = psycopg2.extras.Json(segment_data[14])
            
            batch.append(tuple(segment_data))
            
            if len(batch) >= batch_size:
                # Insert batch (including voice_embedding)
                prod_cur.executemany("""
                    INSERT INTO segments (
                        video_id, start_sec, end_sec, speaker_label, speaker_conf,
                        text, avg_logprob, compression_ratio, no_speech_prob,
                        temperature_used, re_asr, is_overlap, needs_refinement,
                        embedding, voice_embedding, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, batch)
                prod_conn.commit()
                synced += len(batch)
                logger.info(f"Synced {synced}/{len(new_segments)} segments...")
                batch = []
        
        # Insert remaining (including voice_embedding)
        if batch:
            prod_cur.executemany("""
                INSERT INTO segments (
                    video_id, start_sec, end_sec, speaker_label, speaker_conf,
                    text, avg_logprob, compression_ratio, no_speech_prob,
                    temperature_used, re_asr, is_overlap, needs_refinement,
                    embedding, voice_embedding, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, batch)
            prod_conn.commit()
            synced += len(batch)
        
        logger.info(f"✅ Synced {synced} segments")
        return synced
    finally:
        local_cur.close()
        prod_cur.close()


def log_sync(prod_conn, sources_synced: int, segments_synced: int):
    """Log sync operation."""
    cur = prod_conn.cursor()
    try:
        cur.execute("""
            INSERT INTO sync_log (sync_time, sources_synced, segments_synced)
            VALUES (NOW(), %s, %s)
        """, (sources_synced, segments_synced))
        prod_conn.commit()
    finally:
        cur.close()


def main():
    """Main sync function."""
    logger.info("=" * 80)
    logger.info("DATABASE SYNC: Local → Production")
    logger.info("=" * 80)
    
    # Get database URLs
    local_db_url = os.getenv('LOCAL_DATABASE_URL') or os.getenv('DATABASE_URL')
    prod_db_url = os.getenv('PRODUCTION_DATABASE_URL')
    
    if not prod_db_url:
        logger.error("❌ PRODUCTION_DATABASE_URL not set")
        logger.error("Set in .env: PRODUCTION_DATABASE_URL=postgresql://...")
        sys.exit(1)
    
    if local_db_url == prod_db_url:
        logger.error("❌ LOCAL and PRODUCTION database URLs are the same!")
        logger.error("This would sync to itself. Please set different URLs.")
        sys.exit(1)
    
    logger.info(f"Local DB: {local_db_url[:30]}...")
    logger.info(f"Production DB: {prod_db_url[:30]}...")
    
    # Connect to databases
    try:
        local_conn = get_connection(local_db_url)
        prod_conn = get_connection(prod_db_url)
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    try:
        # Get last sync time
        last_sync = get_last_sync_time(prod_conn)
        logger.info(f"Last sync: {last_sync}")
        logger.info(f"Syncing data created after {last_sync}")
        
        # Sync sources
        logger.info("\n📦 Syncing sources...")
        sources_synced = sync_sources(local_conn, prod_conn, last_sync)
        
        # Sync segments
        logger.info("\n📝 Syncing segments...")
        segments_synced = sync_segments(local_conn, prod_conn, last_sync)
        
        # Log sync
        log_sync(prod_conn, sources_synced, segments_synced)
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ SYNC COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Sources synced: {sources_synced}")
        logger.info(f"Segments synced: {segments_synced}")
        logger.info(f"Sync time: {datetime.now()}")
        logger.info("=" * 80)
        
    finally:
        local_conn.close()
        prod_conn.close()


if __name__ == '__main__':
    main()
