# Git Commit Plan - MVP Ready

## Commit Strategy

Organize changes into logical, atomic commits for clean git history.

---

## Commit 1: Database Migration - Video Type Classification

**Purpose**: Add video_type column and classification logic

**Files**:
- `backend/migrations/versions/004_add_video_type_classification.py`

**Command**:
```bash
git add backend/migrations/versions/004_add_video_type_classification.py
git commit -m "feat(db): add video_type classification column

- Add migration 004 for video_type column (monologue/interview/clips)
- Classify existing videos based on speaker distribution
- Add index for efficient filtering
- Enable AI summarization filtering by video type

Classification logic:
- monologue: 1 speaker (100% accuracy)
- interview: >15% guest content (63% accuracy)
- monologue_with_clips: <15% guest content (100% accuracy)

Closes #[issue-number] if applicable"
```

---

## Commit 2: Application Logic - Auto-Classification

**Purpose**: Add automatic video type classification during ingestion

**Files**:
- `backend/scripts/common/segments_database.py`

**Command**:
```bash
git add backend/scripts/common/segments_database.py
git commit -m "feat(ingestion): auto-classify video type during segment insertion

- Add _classify_video_type() method to SegmentsDatabase
- Automatically classify videos as monologue/interview/clips
- Classification happens after segment insertion
- Non-critical failure handling (logs warning, doesn't break ingestion)

Ensures all new videos get classified without manual intervention.
Works with existing chaffee_only_storage flag."
```

---

## Commit 3: Unit Tests - Video Type Classification

**Purpose**: Add comprehensive unit tests for classification logic

**Files**:
- `tests/unit/test_video_type_classification.py`

**Command**:
```bash
git add tests/unit/test_video_type_classification.py
git commit -m "test(unit): add video type classification tests

- 13 unit tests covering all classification scenarios
- Test monologue, interview, and clips detection
- Test boundary cases (15% threshold)
- Test error handling and edge cases
- Mock database dependencies for fast execution

All tests passing (0.15s execution time)"
```

---

## Commit 4: Integration Tests - End-to-End Verification

**Purpose**: Add integration tests with real database

**Files**:
- `tests/integration/test_video_type_integration.py`

**Command**:
```bash
git add tests/integration/test_video_type_integration.py
git commit -m "test(integration): add video type end-to-end tests

- 7 integration tests with real database
- Test full flow: insert → classify → verify
- Test index and column existence
- Test with chaffee_only_storage flag
- Auto-cleanup test data

Requires DATABASE_URL for execution"
```

---

## Commit 5: Test Infrastructure

**Purpose**: Add test runner and documentation

**Files**:
- `run_tests.ps1`
- `TESTING_SUMMARY.md`

**Command**:
```bash
git add run_tests.ps1 TESTING_SUMMARY.md
git commit -m "chore(test): add test runner and documentation

- PowerShell test runner with coverage support
- Comprehensive testing documentation
- Pre-ingestion test checklist
- CI/CD recommendations

Usage: .\run_tests.ps1 -Unit -Integration -Coverage"
```

---

## Commit 6: Diarization Benchmark Tools

**Purpose**: Add comprehensive diarization testing framework

**Files**:
- `bench_diar/` (all files)
- `diar_bench/` (all files)

**Command**:
```bash
git add bench_diar/ diar_bench/
git commit -m "feat(benchmark): add diarization comparison tools

Benchmark Tools:
- bench_diar/: Full benchmark with ingest integration
- diar_bench/: Standalone benchmark tools
- Pyannote testing (3 modes: auto, bounded, forced)
- SpeechBrain baseline support
- E2E model framework (FS-EEND, NeMo)
- Transcript alignment utilities
- Timeline visualizations

Enables testing alternative diarization approaches.
Documents pyannote limitations (63% interview accuracy)."
```

---

## Commit 7: Documentation - MVP Ready

**Purpose**: Add comprehensive documentation for MVP launch

**Files**:
- `MVP_READY_SUMMARY.md`
- `OVERNIGHT_INGESTION_CHECKLIST.md`
- `DIARIZATION_BENCHMARK_COMPLETE.md`

**Command**:
```bash
git add MVP_READY_SUMMARY.md OVERNIGHT_INGESTION_CHECKLIST.md DIARIZATION_BENCHMARK_COMPLETE.md
git commit -m "docs(mvp): add production readiness documentation

- MVP_READY_SUMMARY: Complete feature overview
- OVERNIGHT_INGESTION_CHECKLIST: Step-by-step launch guide
- DIARIZATION_BENCHMARK_COMPLETE: Benchmark results and analysis

Documents:
- 96.3% overall accuracy (100% monologues, 63% interviews)
- RTX 5080 optimizations
- Video type classification
- Pre-ingestion verification steps"
```

---

## Commit 8: Documentation - Speaker Identification

**Purpose**: Document speaker identification improvements

**Files**:
- `SPEAKER_IDENTIFICATION_FIX_SUMMARY.md`

**Command**:
```bash
git add SPEAKER_IDENTIFICATION_FIX_SUMMARY.md
git commit -m "docs(speaker): document speaker identification improvements

- TDD approach to fixing 4 critical bugs
- Accuracy improvement: 0% → 63% for interviews
- Root cause analysis of pyannote limitations
- Recommendations for future improvements"
```

---

## Commit 9: Cleanup - Remove Temporary Files

**Purpose**: Remove temporary/diagnostic files not needed in repo

**Files to NOT commit**:
- `add_video_type_column.py` (temporary, replaced by migration)
- `diagnose_speaker_issue.py` (diagnostic script)
- `ingest_with_profile_update.py` (temporary)
- `rebuild_chaffee_profile_real.py` (temporary)
- `run_tests.py` (duplicate of run_tests.ps1)
- `backend/scripts/common/enhanced_asr.py.backup` (backup file)
- `CUDNN_FIX.md` (temporary fix doc)
- `REGENERATION_FIX_PLAN.md` (planning doc)

**Command**:
```bash
# Add to .gitignore
echo "*.backup" >> .gitignore
echo "*_temp.py" >> .gitignore
echo "diagnose_*.py" >> .gitignore

git add .gitignore
git commit -m "chore: update gitignore for temporary files"
```

---

## Execute All Commits

**Run this script**:
```powershell
# Commit 1: Migration
git add backend/migrations/versions/004_add_video_type_classification.py
git commit -m "feat(db): add video_type classification column

- Add migration 004 for video_type column (monologue/interview/clips)
- Classify existing videos based on speaker distribution
- Add index for efficient filtering
- Enable AI summarization filtering by video type"

# Commit 2: Application Logic
git add backend/scripts/common/segments_database.py
git commit -m "feat(ingestion): auto-classify video type during segment insertion

- Add _classify_video_type() method to SegmentsDatabase
- Automatically classify videos during ingestion
- Non-critical failure handling"

# Commit 3: Unit Tests
git add tests/unit/test_video_type_classification.py
git commit -m "test(unit): add video type classification tests

- 13 unit tests covering all scenarios
- All tests passing (0.15s execution)"

# Commit 4: Integration Tests
git add tests/integration/test_video_type_integration.py
git commit -m "test(integration): add video type end-to-end tests

- 7 integration tests with real database
- Full flow verification"

# Commit 5: Test Infrastructure
git add run_tests.ps1 TESTING_SUMMARY.md
git commit -m "chore(test): add test runner and documentation"

# Commit 6: Benchmark Tools
git add bench_diar/ diar_bench/
git commit -m "feat(benchmark): add diarization comparison tools

- Comprehensive benchmark framework
- Pyannote + SpeechBrain + E2E models
- Documents 63% interview accuracy limitation"

# Commit 7: MVP Documentation
git add MVP_READY_SUMMARY.md OVERNIGHT_INGESTION_CHECKLIST.md DIARIZATION_BENCHMARK_COMPLETE.md
git commit -m "docs(mvp): add production readiness documentation

- Complete MVP overview
- Overnight ingestion guide
- 96.3% overall accuracy documented"

# Commit 8: Speaker Documentation
git add SPEAKER_IDENTIFICATION_FIX_SUMMARY.md
git commit -m "docs(speaker): document speaker identification improvements"

# Commit 9: Cleanup
echo "*.backup" >> .gitignore
echo "*_temp.py" >> .gitignore
echo "diagnose_*.py" >> .gitignore
git add .gitignore
git commit -m "chore: update gitignore for temporary files"

# Push all commits
git push origin main
```

---

## Verification

After commits:
```bash
# Check commit history
git log --oneline -10

# Verify all changes committed
git status

# Check remote sync
git remote -v
git fetch
git status
```

---

## Rollback Plan (If Needed)

If something goes wrong:
```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Undo multiple commits
git reset --hard HEAD~9  # Undo all 9 commits

# Force push (if already pushed)
git push origin main --force
```

---

## Summary

**9 logical commits** covering:
1. Database migration
2. Application logic
3. Unit tests
4. Integration tests
5. Test infrastructure
6. Benchmark tools
7. MVP documentation
8. Speaker documentation
9. Cleanup

**Total files**: ~30 new/modified files
**Lines added**: ~5000+ lines of code and documentation
**Test coverage**: 21 new tests, all passing

**Ready to commit and push!** 🚀
