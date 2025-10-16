#!/usr/bin/env python3
"""Count segments with empty text in production"""
import os
import sys
import psycopg2
from pathlib import Path

# Load from backend/.env
backend_env = Path(__file__).parent / 'backend' / '.env'
from dotenv import load_dotenv
load_dotenv(backend_env)

PROD_DB = os.getenv('PRODUCTION_DATABASE_URL')

print("Connecting to production database...")
conn = psycopg2.connect(PROD_DB)
cur = conn.cursor()

# Count total segments
cur.execute("SELECT COUNT(*) FROM segments")
total = cur.fetchone()[0]

# Count segments with empty or null text
cur.execute("SELECT COUNT(*) FROM segments WHERE text IS NULL OR text = ''")
empty = cur.fetchone()[0]

# Count segments with text
cur.execute("SELECT COUNT(*) FROM segments WHERE text IS NOT NULL AND text != ''")
with_text = cur.fetchone()[0]

print(f"\nSegment Text Statistics:")
print(f"  Total segments: {total:,}")
print(f"  With text: {with_text:,} ({with_text/total*100:.1f}%)")
print(f"  Empty/null text: {empty:,} ({empty/total*100:.1f}%)")

cur.close()
conn.close()
