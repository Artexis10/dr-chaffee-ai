# Frontend Testing Guide

**Date:** Nov 17, 2025  
**Status:** Ready for Testing  
**Data:** 468 videos, 340k segments (70% of content)

## System Status ✅

All services running:
- ✅ Backend API: http://localhost:8000
- ✅ Frontend: http://localhost:3000
- ✅ Database: PostgreSQL with 468 videos
- ✅ Redis: Cache layer active

## Test Plan

### 1. Main Page (Home) - Answer Interface

**URL:** http://localhost:3000

**What to Test:**
- [ ] Page loads without errors
- [ ] Search bar is visible and functional
- [ ] Can type a question
- [ ] Submit button works
- [ ] Results display with citations
- [ ] Formatting is clean and readable

**Test Queries:**
1. "What are the benefits of carnivore diet?"
2. "How does insulin affect metabolism?"
3. "What is your stance on seed oils?"
4. "Explain autophagy"
5. "What about autoimmune conditions?"

**Expected Results:**
- Answers should cite Dr. Chaffee's videos
- Include timestamps (e.g., "Video Title @ 12:34")
- Show relevant sources with links
- Display cost information

---

### 2. Tuning Dashboard - Custom Instructions

**URL:** http://localhost:3000/tuning

**What to Test:**

#### A. View Instruction Sets
- [ ] Page loads
- [ ] See list of 5 instruction sets:
  - default (active)
  - Concise Mode
  - Technical Mode
  - General Audience
  - Metabolic Focus
- [ ] Each shows description and status

#### B. Activate Different Sets
- [ ] Click "Activate This Set" on "Concise Mode"
- [ ] Verify it becomes active (badge changes)
- [ ] Switch to "Technical Mode"
- [ ] Verify activation works

#### C. Create New Instruction Set
- [ ] Click "New Instruction Set" button
- [ ] Fill in:
  - Name: "Test Mode"
  - Description: "Test instruction set"
  - Instructions: "Keep answers under 100 words"
- [ ] Click Save
- [ ] Verify it appears in list
- [ ] Verify character counter works (shows X/10000)

#### D. Preview Merged Prompt
- [ ] Click "Preview" on any instruction set
- [ ] Modal shows merged prompt
- [ ] Can see baseline + custom instructions combined
- [ ] Modal closes properly

#### E. View History
- [ ] Click "History" on any instruction set
- [ ] See version history
- [ ] Can rollback to previous version
- [ ] Verify version numbers increment

#### F. Edit Instruction Set
- [ ] Click "Edit" on an instruction set
- [ ] Modify the instructions
- [ ] Click Save
- [ ] Verify version increments
- [ ] Verify in history

#### G. Delete Instruction Set
- [ ] Click "Delete" on a test set
- [ ] Confirm deletion
- [ ] Verify it's removed from list

---

### 3. Embedding Models Section

**What to Test:**
- [ ] See list of available embedding models
- [ ] Each shows:
  - Model name
  - Provider
  - Dimensions
  - Cost per 1k tokens
  - Description
- [ ] Can switch between models (if embeddings exist)
- [ ] Active model is highlighted

---

### 4. Search Configuration Section

**What to Test:**
- [ ] Adjust "Results to Return (top_k)"
  - Try: 10, 20, 50, 100
  - Verify input validation (1-100)
- [ ] Adjust "Similarity Threshold"
  - Try: 0.0, 0.5, 1.0
  - Verify input validation (0.0-1.0)
- [ ] Toggle "Enable Reranker"
  - When enabled, "Rerank Candidates" field appears
  - Can adjust rerank_top_k (1-500)
- [ ] Changes save (check console for API calls)

---

### 5. Statistics Section

**What to Test:**
- [ ] Stats display:
  - Total segments: 340,564
  - Total videos: 468
  - Segments with embeddings: (depends on ingestion)
  - Unique speakers
  - Embedding dimensions
  - Coverage percentage

---

### 6. API Integration Testing

**Test Custom Instructions API:**
```bash
# List all instruction sets
curl http://localhost:8000/api/tuning/instructions

# Get active instruction set
curl http://localhost:8000/api/tuning/instructions/active

# Create new instruction set
curl -X POST http://localhost:8000/api/tuning/instructions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Test",
    "instructions": "Test from API",
    "description": "Testing API"
  }'

# Activate instruction set
curl -X POST http://localhost:8000/api/tuning/instructions/1/activate

# Preview merged prompt
curl -X POST http://localhost:8000/api/tuning/instructions/preview \
  -H "Content-Type: application/json" \
  -d '{"instruction_id": 1}'

# Get history
curl http://localhost:8000/api/tuning/instructions/1/history

# Rollback to version
curl -X POST http://localhost:8000/api/tuning/instructions/1/rollback/1
```

**Test Summarizer Config API:**
```bash
# List available models
curl http://localhost:8000/api/tuning/summarizer/models

# Get current config
curl http://localhost:8000/api/tuning/summarizer/config

# Update config
curl -X POST http://localhost:8000/api/tuning/summarizer/config \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "temperature": 0.1,
    "max_tokens": 2000
  }'
```

---

### 7. Test with Different Instruction Sets

**Workflow:**
1. Go to tuning dashboard
2. Activate "Concise Mode"
3. Go to home page
4. Ask a question
5. Note the response length/style
6. Go back to tuning
7. Activate "Technical Mode"
8. Ask the same question
9. Compare responses

**Expected:** Responses should differ based on active instruction set

---

### 8. Browser DevTools Testing

**Console:**
- [ ] No JavaScript errors
- [ ] No network errors (check Network tab)
- [ ] API calls complete successfully (200 status)

**Network Tab:**
- [ ] Check API response times
- [ ] Verify all requests to `/api/tuning/*` succeed
- [ ] Check payload sizes

**Performance:**
- [ ] Page loads in < 3 seconds
- [ ] Interactions are responsive
- [ ] No lag when switching instruction sets

---

### 9. Edge Cases to Test

- [ ] Create instruction set with max length (10,000 chars)
- [ ] Try to create duplicate name (should fail)
- [ ] Delete active instruction set (should handle gracefully)
- [ ] Rapid switching between instruction sets
- [ ] Very long instruction text
- [ ] Special characters in instructions
- [ ] Empty instruction set (should be allowed)

---

### 10. Mobile/Responsive Testing

- [ ] Test on mobile viewport (375px width)
- [ ] Test on tablet viewport (768px width)
- [ ] Test on desktop (1920px width)
- [ ] All buttons clickable on mobile
- [ ] Text readable on all sizes
- [ ] No horizontal scrolling

---

## Issues to Report

If you find issues, note:
1. **URL** where it occurred
2. **Steps to reproduce**
3. **Expected behavior**
4. **Actual behavior**
5. **Browser/Device**
6. **Screenshot/Video** (if possible)

---

## Success Criteria ✅

Frontend testing is successful when:
- ✅ All pages load without errors
- ✅ Custom instructions work end-to-end
- ✅ API endpoints respond correctly
- ✅ Instruction sets affect AI responses
- ✅ No console errors
- ✅ Responsive on all screen sizes
- ✅ Performance is acceptable

---

## Next Steps

After testing:
1. Document any bugs found
2. Create issues for bugs
3. Test with actual ingestion running
4. Test with different data volumes
5. Performance testing under load
6. User acceptance testing with Dr. Chaffee

---

## Quick Links

- **Frontend:** http://localhost:3000
- **Tuning Dashboard:** http://localhost:3000/tuning
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Database:** localhost:5432 (askdrchaffee)

---

**Happy Testing! 🚀**
