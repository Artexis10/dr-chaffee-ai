#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect('postgresql://postgres:password@localhost:5432/askdrchaffee')
cur = conn.cursor()

try:
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = cur.fetchall()
    print("Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
except Exception as e:
    print(f'Error: {e}')
finally:
    cur.close()
    conn.close()
