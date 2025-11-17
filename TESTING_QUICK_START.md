# Frontend Testing - Quick Start

## 🚀 Start Here

**Everything is running and ready to test!**

```
✅ Backend:  http://localhost:8000
✅ Frontend: http://localhost:3000
✅ Database: 468 videos, 340k segments
✅ APIs:    All working
```

---

## 📋 5-Minute Test

### 1. Test Main Page (Answer Interface)
```
1. Go to http://localhost:3000
2. Type: "What are the benefits of carnivore diet?"
3. Click Submit
4. Verify: Answer appears with citations and sources
```

### 2. Test Custom Instructions
```
1. Go to http://localhost:3000/tuning
2. Scroll to "Custom Instructions" section
3. Click "Activate This Set" on "Concise Mode"
4. Go back to home page
5. Ask same question again
6. Verify: Answer is shorter/different
```

### 3. Test Tuning Dashboard
```
1. Still on /tuning page
2. Try switching to "Technical Mode"
3. Try creating a new instruction set
4. Try previewing a merged prompt
5. Try viewing history
```

---

## 🧪 Full Test Checklist

### Main Page
- [ ] Page loads
- [ ] Can type question
- [ ] Submit works
- [ ] Answer appears
- [ ] Citations show
- [ ] Sources display

### Tuning Dashboard
- [ ] Page loads
- [ ] See 5 instruction sets
- [ ] Can activate sets
- [ ] Can create new set
- [ ] Can preview prompt
- [ ] Can view history
- [ ] Can edit instructions
- [ ] Can delete sets

### API Endpoints
- [ ] GET /api/tuning/instructions (list)
- [ ] POST /api/tuning/instructions (create)
- [ ] GET /api/tuning/summarizer/models (list models)
- [ ] GET /api/tuning/summarizer/config (get config)

### Responsive Design
- [ ] Works on mobile (375px)
- [ ] Works on tablet (768px)
- [ ] Works on desktop (1920px)

---

## 🎯 Test Queries

Use these to test the system:

1. **"What are the benefits of carnivore diet?"**
   - Should get detailed answer about carnivore benefits

2. **"How does insulin affect metabolism?"**
   - Should explain insulin's role in metabolism

3. **"What is your stance on seed oils?"**
   - Should be critical of seed oils

4. **"Explain autophagy"**
   - Should explain cellular autophagy mechanism

5. **"What about autoimmune conditions?"**
   - Should discuss autoimmune and diet connection

---

## 🔍 What to Look For

### Good Signs ✅
- Answers cite Dr. Chaffee's videos
- Timestamps included (e.g., "Video @ 12:34")
- Multiple sources when relevant
- Clear, direct tone
- Proper formatting

### Bad Signs ❌
- Generic answers without citations
- No timestamps
- Grammatical errors
- Broken formatting
- Missing sources

---

## 🐛 If Something Breaks

1. **Check browser console** (F12 → Console tab)
   - Any red errors?
   - Copy error message

2. **Check network tab** (F12 → Network tab)
   - Any failed requests (red)?
   - Check response status codes

3. **Check backend logs**
   ```bash
   docker-compose -f docker-compose.dev.yml logs backend --tail 50
   ```

4. **Check frontend logs**
   ```bash
   docker-compose -f docker-compose.dev.yml logs frontend --tail 50
   ```

---

## 📊 System Info

**Database:**
- Videos: 468
- Segments: 340,564
- Embeddings: (depends on ingestion status)

**Custom Instructions:**
- Default (active)
- Concise Mode
- Technical Mode
- General Audience
- Metabolic Focus

**Summarizer Model:**
- Current: gpt-4-turbo
- Temperature: 0.1
- Max tokens: 2000

---

## 🎬 Record Your Findings

When testing, note:
1. **What you tested**
2. **What happened**
3. **What you expected**
4. **Any errors** (screenshot console)
5. **Browser/Device**

---

## 📞 Need Help?

- **API Docs:** http://localhost:8000/docs
- **Backend Logs:** `docker-compose logs backend`
- **Frontend Logs:** `docker-compose logs frontend`
- **Database:** `docker exec drchaffee-db psql -U postgres -d askdrchaffee`

---

## ✨ You're Ready!

**Go test the frontend! 🚀**

Start with the 5-minute test above, then dive into the full checklist.

Questions? Check `FRONTEND_TESTING_GUIDE.md` for detailed instructions.
