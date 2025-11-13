#!/usr/bin/env python3
"""
Apply custom instructions migration to database
"""

import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

def apply_migration():
    """Apply the custom instructions migration"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    migration_file = Path(__file__).parent.parent.parent / "db" / "migrations" / "014_custom_instructions.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"📄 Reading migration: {migration_file.name}")
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        print("⚙️  Applying migration...")
        cur.execute(migration_sql)
        
        conn.commit()
        
        # Verify tables created
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name IN ('custom_instructions', 'custom_instructions_history')
        """)
        
        tables = [row[0] for row in cur.fetchall()]
        
        if 'custom_instructions' in tables and 'custom_instructions_history' in tables:
            print("✅ Migration applied successfully!")
            print(f"   - Created table: custom_instructions")
            print(f"   - Created table: custom_instructions_history")
            
            # Check if default instruction set exists
            cur.execute("SELECT COUNT(*) FROM custom_instructions WHERE name = 'default'")
            count = cur.fetchone()[0]
            
            if count > 0:
                print(f"   - Default instruction set created")
            
            cur.close()
            conn.close()
            return True
        else:
            print("⚠️  Migration executed but tables not found")
            cur.close()
            conn.close()
            return False
            
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Custom Instructions Migration")
    print("=" * 60)
    
    success = apply_migration()
    
    if success:
        print("\n✅ Migration complete! You can now use custom instructions.")
        print("\nNext steps:")
        print("1. Access tuning dashboard: http://localhost:3000/tuning")
        print("2. Or use API: http://localhost:8000/api/tuning/instructions")
        sys.exit(0)
    else:
        print("\n❌ Migration failed. Check errors above.")
        sys.exit(1)
