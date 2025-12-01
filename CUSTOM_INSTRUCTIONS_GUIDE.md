# Custom Instructions - Layered Prompt System

## Overview

The custom instructions feature allows Dr. Chaffee to tune the AI's behavior **without exposing or modifying core safety rules**. This implements a two-layer architecture:

1. **Baseline Layer (Protected)** - Core persona, medical accuracy, and safety guardrails
2. **Custom Layer (User-Editable)** - Additional guidance for tone, depth, emphasis, etc.

## Architecture

```
┌─────────────────────────────────────────┐
│  User sees: "Custom Instructions"       │
│  (Simple textarea, max 5000 chars)      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Runtime Merge:                         │
│  Baseline + Custom → Final Prompt       │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Sent to OpenAI:                        │
│  - Baseline persona (always included)   │
│  - Custom instructions (if active)      │
│  - Schema requirements                  │
│  - User query + RAG context             │
└─────────────────────────────────────────┘
```

## Key Benefits

✅ **Safety First** - Core medical accuracy rules can't be accidentally broken  
✅ **Non-Technical UX** - Simple textarea, no code or technical jargon  
✅ **Version Control** - Automatic history tracking with rollback capability  
✅ **Preview Before Save** - See exactly how instructions merge with baseline  
✅ **Zero Downtime** - Switch instruction sets instantly without redeployment  

## Database Schema

### Tables Created

**`custom_instructions`** - Main storage
- `id` - Primary key
- `name` - Unique identifier (e.g., "Enhanced Medical Focus")
- `instructions` - Custom text (max 5000 chars)
- `description` - What these instructions do
- `is_active` - Only one can be active at a time
- `version` - Auto-incremented on each update
- `created_at`, `updated_at` - Timestamps

**`custom_instructions_history`** - Version history
- Automatic archiving on every update
- Enables rollback to previous versions
- Tracks when changes were made

### Triggers

- `update_custom_instructions_timestamp()` - Auto-updates version and archives old content

## API Endpoints

All endpoints are under `/api/tuning/instructions`:

### List All Instruction Sets
```http
GET /api/tuning/instructions
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "default",
    "instructions": "",
    "description": "Default empty instruction set",
    "is_active": true,
    "version": 1,
    "created_at": "2025-01-13T12:00:00",
    "updated_at": "2025-01-13T12:00:00"
  }
]
```

### Get Active Instructions
```http
GET /api/tuning/instructions/active
```

Returns the currently active instruction set.

### Create New Instruction Set
```http
POST /api/tuning/instructions
Content-Type: application/json

{
  "name": "Enhanced Medical Focus",
  "instructions": "- Emphasize autoimmune conditions\n- Cite clinical studies when available\n- Use more technical terminology",
  "description": "Deeper medical focus for healthcare professionals",
  "is_active": false
}
```

### Update Instruction Set
```http
PUT /api/tuning/instructions/{id}
Content-Type: application/json

{
  "name": "Enhanced Medical Focus",
  "instructions": "Updated instructions...",
  "description": "Updated description",
  "is_active": true
}
```

**Note:** Updating automatically archives the previous version to history.

### Activate Instruction Set
```http
POST /api/tuning/instructions/{id}/activate
```

Deactivates all others and activates the specified set.

### Delete Instruction Set
```http
DELETE /api/tuning/instructions/{id}
```

**Note:** Cannot delete the "default" instruction set.

### Preview Merged Prompt
```http
POST /api/tuning/instructions/preview
Content-Type: application/json

{
  "name": "test",
  "instructions": "Your custom instructions here",
  "description": "Test preview"
}
```

**Response:**
```json
{
  "baseline_prompt": "You are Emulated Dr Anthony Chaffee...",
  "custom_instructions": "Your custom instructions here",
  "merged_prompt": "You are Emulated Dr Anthony Chaffee...\n\n## Additional Custom Instructions\n\nYour custom instructions here",
  "character_count": 1234,
  "estimated_tokens": 308
}
```

### Get Version History
```http
GET /api/tuning/instructions/{id}/history
```

Returns all previous versions of an instruction set.

### Rollback to Previous Version
```http
POST /api/tuning/instructions/{id}/rollback/{version}
```

Restores the instruction set to a previous version.

## Frontend UI

### Location
`http://localhost:3000/tuning` → "Custom Instructions" section

### Features

**List View:**
- Shows all instruction sets
- Active set highlighted in green
- Quick actions: Edit, View History, Delete, Activate

**Edit Mode:**
- Name field (max 255 chars)
- Description field (max 500 chars)
- Instructions textarea (max 5000 chars) with character counter
- "Activate immediately" checkbox
- Preview button - shows merged prompt before saving
- Save/Cancel buttons

**Preview Modal:**
- Shows baseline prompt (read-only)
- Shows custom instructions
- Shows merged result
- Character count and estimated token count

**History Modal:**
- Lists all previous versions with timestamps
- One-click rollback to any version
- Shows full instruction text for each version

## Usage Examples

### Example 1: Emphasize Specific Topics
```
Name: Autoimmune Focus
Description: Emphasize autoimmune conditions and elimination protocols

Instructions:
- When discussing diet, prioritize autoimmune condition context
- Emphasize elimination protocols and reintroduction strategies
- Reference clinical outcomes for autoimmune patients when available
- Use terms like "autoimmune protocol", "elimination phase", "reintroduction"
```

### Example 2: Adjust Tone for Audience
```
Name: Healthcare Professional Mode
Description: More technical language for medical professionals

Instructions:
- Use medical terminology (e.g., "hyperinsulinemia" vs "high insulin")
- Cite specific studies with PMID when available
- Include mechanism of action details
- Reference clinical markers and lab values
```

### Example 3: Citation Preferences
```
Name: Enhanced Citations
Description: More detailed source citations

Instructions:
- Always include video title and timestamp for every claim
- Prefer citing multiple sources when available
- Mention if a topic has limited coverage in the source material
- Note when extrapolating beyond direct quotes
```

### Example 4: Depth Control
```
Name: Concise Answers
Description: Shorter, more direct responses

Instructions:
- Keep answers under 200 words unless explicitly asked for detail
- Lead with the direct answer, then supporting evidence
- Use bullet points for multiple related points
- Avoid lengthy explanations unless requested
```

## Setup Instructions

### 1. Apply Database Migration

**Option A: Using Docker (Recommended)**
```bash
# From project root
docker-compose -f docker-compose.dev.yml exec backend python utils/database/apply_custom_instructions_migration.py
```

**Option B: Direct Python**
```bash
cd backend
python ../utils/database/apply_custom_instructions_migration.py
```

### 2. Verify Migration
```bash
# Check tables exist
docker-compose -f docker-compose.dev.yml exec db psql -U postgres -d drchaffee -c "\dt custom_instructions*"
```

Expected output:
```
                    List of relations
 Schema |            Name                | Type  |  Owner
--------+--------------------------------+-------+----------
 public | custom_instructions            | table | postgres
 public | custom_instructions_history    | table | postgres
```

### 3. Restart Backend (if running)
```bash
docker-compose -f docker-compose.dev.yml restart backend
```

### 4. Access UI
Navigate to: `http://localhost:3000/tuning`

The "Custom Instructions" section should appear at the top of the page.

## Testing

### Run Unit Tests
```bash
cd tests
python test_custom_instructions.py
```

Expected output:
```
Testing Custom Instructions System...
============================================================
✅ Baseline prompt loads
✅ Custom instructions merge
✅ Prompt structure correct
✅ Custom instructions optional
✅ Schema loading works
✅ Full prompt creation works
============================================================
All tests passed! ✅
```

### Manual API Testing

**Test Preview:**
```bash
curl -X POST http://localhost:8000/api/tuning/instructions/preview \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test",
    "instructions": "- Test instruction 1\n- Test instruction 2"
  }'
```

**Test Create:**
```bash
curl -X POST http://localhost:8000/api/tuning/instructions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-set",
    "instructions": "Test instructions",
    "description": "Test description",
    "is_active": false
  }'
```

## How It Works Internally

### Prompt Assembly Flow

1. **User makes query** → Frontend sends to `/api/answer`
2. **Backend retrieves RAG context** → Semantic search for relevant segments
3. **Prompt loader called** → `ChaffeePromptLoader.load_system_prompt()`
4. **Baseline loaded** → Reads `shared/prompts/chaffee_persona.md`
5. **Custom instructions queried** → Checks DB for active instruction set
6. **Merge performed** → Appends custom under "## Additional Custom Instructions"
7. **Schema added** → Response format requirements appended
8. **Sent to OpenAI** → Complete prompt with user query and context

### Code Locations

**Backend:**
- Migration: `db/migrations/014_custom_instructions.sql`
- API: `backend/api/tuning.py` (lines 326-676)
- Prompt Loader: `shared/prompts/prompt_loader.py` (updated `load_system_prompt()`)
- Migration Script: `utils/database/apply_custom_instructions_migration.py`

**Frontend:**
- Component: `frontend/src/components/CustomInstructionsEditor.tsx`
- Integration: `frontend/src/app/tuning/page.tsx` (line 212)

**Tests:**
- Unit Tests: `tests/test_custom_instructions.py`

## Security Considerations

✅ **Baseline Protected** - Core safety rules in `chaffee_persona.md` are never exposed to UI  
✅ **Input Validation** - Character limits enforced (5000 chars for instructions)  
✅ **SQL Injection Safe** - All queries use parameterized statements  
✅ **No Code Execution** - Instructions are plain text, no eval/exec  
✅ **Version Control** - Can always rollback if instructions cause issues  

## Troubleshooting

### Issue: "No active instruction set found"
**Solution:** Run migration script to create default instruction set:
```bash
python utils/database/apply_custom_instructions_migration.py
```

### Issue: Custom instructions not appearing in responses
**Check:**
1. Is an instruction set marked as active? (Check UI or DB)
2. Are instructions non-empty?
3. Backend logs for warnings about loading custom instructions

**Debug:**
```bash
# Check active instruction
docker-compose -f docker-compose.dev.yml exec db psql -U postgres -d drchaffee -c "SELECT * FROM custom_instructions WHERE is_active = true;"
```

### Issue: Frontend component not showing
**Check:**
1. Migration applied successfully?
2. Backend API responding? Test: `curl http://localhost:8000/api/tuning/instructions`
3. Frontend console for errors

### Issue: Preview shows wrong baseline
**Solution:** Baseline path is hardcoded in `tuning.py` line 650. Verify:
```python
baseline_path = Path(__file__).parent.parent.parent / "shared" / "prompts" / "chaffee_persona.md"
```

## Future Enhancements

Potential additions (not implemented):

- **A/B Testing** - Compare responses with different instruction sets
- **Templates** - Pre-built instruction sets for common use cases
- **Per-User Instructions** - Different instruction sets for different users
- **Instruction Analytics** - Track which instructions improve response quality
- **Import/Export** - Share instruction sets between deployments
- **Instruction Validation** - AI-powered check for conflicting instructions

## Summary

This layered instruction system gives Dr. Chaffee full control over AI behavior while maintaining safety guardrails. The non-technical UI, version control, and preview capability make it safe and easy to experiment with different instruction sets.

**Key Principle:** Baseline rules are immutable and hidden. Custom instructions are additive and transparent.
