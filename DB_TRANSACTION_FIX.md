# Database Transaction Fix - Nothing Saved to DB

**Date**: 2025-10-11 09:31  
**Problem**: Last ingestion didn't save anything to database  
**Root Cause**: Aborted transaction not being reset

---

## The Error

From your logs:
```
2025-10-11 05:40:03,251 - ERROR - scripts.common.segments_database - Failed to upsert source E1Yk-o8xwjw: current transaction is aborted, commands ignored until end of transaction block

2025-10-11 05:40:03,252 - ERROR - __main__ - Batch insert failed for E1Yk-o8xwjw: current transaction is aborted, commands ignored until end of transaction block
```

**What happened**:
1. An earlier database operation failed (unknown error)
2. PostgreSQL aborted the transaction
3. Connection stayed in "aborted transaction" state
4. All subsequent DB operations failed with "transaction is aborted"
5. **Result**: No data saved for any videos!

---

## Root Cause

**PostgreSQL transaction states**:
- `TRANSACTION_STATUS_IDLE` (0): No transaction
- `TRANSACTION_STATUS_ACTIVE` (1): Transaction in progress
- `TRANSACTION_STATUS_INTRANS` (2): Transaction idle
- **`TRANSACTION_STATUS_INERROR` (3): Transaction aborted** ← Problem!

When a transaction is aborted (state 3), PostgreSQL ignores all commands until:
- `ROLLBACK` is called
- Connection is closed

**The bug**: After `rollback()`, the connection wasn't being checked for aborted state on next use.

---

## The Fix

### Change 1: Check Transaction State on Connection Reuse ✅

**File**: `backend/scripts/common/segments_database.py:32-52`

```python
def get_connection(self):
    """Get database connection"""
    if not self.connection or self.connection.closed:
        self.connection = psycopg2.connect(self.db_url)
    else:
        # NEW: Check if connection is in a failed transaction state
        try:
            status = self.connection.get_transaction_status()
            # TRANSACTION_STATUS_INERROR = 3 means transaction aborted
            if status == 3:
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
```

**Impact**: Automatically detects and fixes aborted transactions

### Change 2: Better Error Handling on Rollback ✅

**File**: `backend/scripts/common/segments_database.py:167-182, 272-287`

```python
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
            self.connection = None  # Force new connection
    raise
```

**Impact**: 
- Better error logging (shows error type)
- Handles rollback failures gracefully
- Forces new connection if rollback fails

---

## What This Fixes

### Before Fix
```
Video 1: DB operation fails → transaction aborted
Video 2: "transaction is aborted" → FAIL
Video 3: "transaction is aborted" → FAIL
...
Video 30: "transaction is aborted" → FAIL

Result: 0 videos saved ❌
```

### After Fix
```
Video 1: DB operation fails → transaction aborted → rollback → connection reset
Video 2: New transaction → SUCCESS ✅
Video 3: New transaction → SUCCESS ✅
...
Video 30: New transaction → SUCCESS ✅

Result: 29 videos saved (1 failed, 29 succeeded) ✅
```

---

## Testing

### Test 1: Verify Fix Works
```powershell
python backend/scripts/ingest_youtube.py --limit 5 --newest-first
```

**Watch for**:
- No "transaction is aborted" errors
- Successful segment inserts
- Data actually in database

### Test 2: Check Database
```sql
-- Count segments by video
SELECT video_id, COUNT(*) as segment_count
FROM segments
GROUP BY video_id
ORDER BY created_at DESC
LIMIT 10;

-- Should show recent videos with segments
```

### Test 3: Force Error and Recovery
```python
# Temporarily add to segments_database.py for testing
def test_transaction_recovery(self):
    """Test that connection recovers from aborted transaction"""
    conn = self.get_connection()
    
    # Force a transaction error
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1/0")  # Division by zero
    except:
        pass
    
    # Connection should now be in aborted state
    # Next get_connection() should fix it
    conn = self.get_connection()
    
    # This should work now
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1
```

---

## Why This Happened

### Possible Triggers

1. **Constraint violation** (most likely)
   - Duplicate video_id
   - NULL in NOT NULL column
   - Foreign key violation

2. **Data type mismatch**
   - Inserting string where number expected
   - Invalid JSON in metadata field

3. **Connection timeout**
   - Long-running transaction
   - Network interruption

4. **Resource exhaustion**
   - Out of disk space
   - Too many connections

### Finding the Original Error

The original error that aborted the transaction is NOT in your logs. It happened earlier and wasn't logged properly.

**To find it next time**:
```python
# Add to error handling
except Exception as e:
    logger.error(f"ORIGINAL ERROR: {e}")
    logger.error(f"Error type: {type(e).__name__}")
    logger.error(f"Error args: {e.args}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
```

---

## Prevention

### 1. Add Constraint Checks Before Insert
```python
# Before batch_insert_segments
if self.video_exists(video_id):
    logger.warning(f"Video {video_id} already exists, skipping or updating")
    return 0
```

### 2. Validate Data Before Insert
```python
# Check for None/NULL in required fields
for segment in segments:
    if not segment.get('text'):
        logger.error(f"Segment missing text: {segment}")
        raise ValueError("Segment text is required")
```

### 3. Use Savepoints for Partial Rollback
```python
# Instead of rolling back entire batch, use savepoints
conn.execute("SAVEPOINT batch_insert")
try:
    # Insert segments
    pass
except:
    conn.execute("ROLLBACK TO SAVEPOINT batch_insert")
```

---

## Summary

**Problem**: Aborted transaction not being reset → all DB operations fail  
**Fix**: Check transaction state on connection reuse + better error handling  
**Impact**: Database saves will now work even if one video fails  

**Files modified**:
1. ✅ `backend/scripts/common/segments_database.py:32-52` - Transaction state check
2. ✅ `backend/scripts/common/segments_database.py:167-182` - Better error handling (upsert_source)
3. ✅ `backend/scripts/common/segments_database.py:272-287` - Better error handling (batch_insert)

**Next**: Run test ingestion and verify data is saved to database.
