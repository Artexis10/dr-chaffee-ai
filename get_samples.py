import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT text 
    FROM segments 
    WHERE speaker_label = 'Chaffee' 
    AND LENGTH(text) > 200 
    ORDER BY RANDOM() 
    LIMIT 5
""")

rows = cur.fetchall()

print('=== Sample Dr. Chaffee Transcripts ===\n')
for i, row in enumerate(rows, 1):
    print(f'{i}. {row[0][:400]}...\n')

cur.close()
conn.close()
