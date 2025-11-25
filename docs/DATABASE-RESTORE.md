# Database Backup & Restore Guide

This guide covers backing up the local PostgreSQL database and restoring it to the Hetzner/Coolify production instance.

## Prerequisites

- Local PostgreSQL with `pg_dump` available
- Access to Coolify dashboard for production credentials
- `psql` client installed locally

## Production Database Details

| Setting | Value |
|---------|-------|
| Host | Get from Coolify Connection tab |
| Port | **5434** |
| User | `postgres` |
| Database | Get from Coolify Connection tab |
| Password | Get from Coolify Connection tab |

---

## 1. Create a Backup (Local)

### Option A: Command Line

```bash
pg_dump --format=p --no-owner --no-acl -h localhost -p 5432 -U postgres -d drchaffee > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Flags explained:**
- `--format=p` — Plain SQL format (required for cross-version compatibility)
- `--no-owner` — Omit ownership commands
- `--no-acl` — Omit access control (GRANT/REVOKE)

### Option B: DBeaver GUI

1. Right-click database → **Tools** → **Backup**
2. Set **Format** to **Plain**
3. Enable **No owner** and **No ACL**
4. Choose output file location
5. Click **Start**

> ⚠️ **Never use custom format (`-Fc`)** — it requires matching `pg_restore` versions and causes compatibility issues.

---

## 2. Reset Production Schema

Before restoring, reset the public schema to avoid conflicts:

```bash
psql -h <host> -p 5434 -U postgres -d <dbname> -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
"
```

Replace `<host>` and `<dbname>` with values from Coolify.

---

## 3. Restore to Production

```bash
psql -h <host> -p 5434 -U postgres -d <dbname> -f backup_YYYYMMDD_HHMMSS.sql
```

You'll be prompted for the password (get from Coolify Connection tab).

### Example with actual values:

```bash
psql -h your-coolify-host.example.com -p 5434 -U postgres -d drchaffee -f backup_20251125_220000.sql
```

---

## 4. Verify Restore

Connect and check key tables:

```bash
psql -h <host> -p 5434 -U postgres -d <dbname>
```

```sql
-- Check row counts
SELECT 'sources' AS table_name, COUNT(*) FROM sources
UNION ALL
SELECT 'segments', COUNT(*) FROM segments
UNION ALL
SELECT 'custom_instructions', COUNT(*) FROM custom_instructions;

-- Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check embedding dimensions
SELECT pg_typeof(embedding), array_length(embedding::real[], 1) 
FROM segments 
WHERE embedding IS NOT NULL 
LIMIT 1;
```

---

## Troubleshooting

### "relation already exists" errors
You forgot to reset the schema. Run the schema reset commands from Step 2.

### "pg_restore: error: input file does not appear to be a valid archive"
You're trying to use `pg_restore` on a plain SQL file. Use `psql -f` instead.

### Version mismatch warnings
Plain SQL format is version-agnostic. Warnings about version differences can be safely ignored.

### pgvector extension missing
If the restore fails on vector columns, ensure pgvector is installed on production:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Backup (local) | `pg_dump --format=p -h localhost -p 5432 -U postgres -d drchaffee > backup.sql` |
| Reset schema | `psql -h <host> -p 5434 -U postgres -d <dbname> -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"` |
| Restore | `psql -h <host> -p 5434 -U postgres -d <dbname> -f backup.sql` |
| Connect | `psql -h <host> -p 5434 -U postgres -d <dbname>` |
