#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect('postgresql://postgres:password@localhost:5432/askdrchaffee')
cur = conn.cursor()

try:
    cur.execute('DELETE FROM segments')
    cur.execute('DELETE FROM sources')
    conn.commit()
    print('✅ Cleared: segments and sources tables')
    
    # Verify
    cur.execute('SELECT COUNT(*) FROM sources')
    sources_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM segments')
    segments_count = cur.fetchone()[0]
    print(f'   Sources: {sources_count} rows')
    print(f'   Segments: {segments_count} rows')
except Exception as e:
    print(f'❌ Error: {e}')
    conn.rollback()
finally:
    cur.close()
    conn.close()
