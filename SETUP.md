# Setup Guide

## 🔒 Security: Install Git Hooks (REQUIRED)

**After cloning this repo, immediately run:**

```bash
./scripts/setup-hooks.sh
```

This installs a pre-commit hook that prevents accidentally committing secrets like:
- API keys
- Database passwords
- `.env` files
- Private keys

**Why this matters:**
- Prevents credential leaks to GitHub
- Blocks commits with sensitive data
- Runs automatically before every commit

---

## 📦 Quick Start

### 1. Install Git Hooks
```bash
./scripts/setup-hooks.sh
```

### 2. Install Dependencies

**Frontend:**
```bash
cd frontend
npm install
```

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment

**Frontend** - Create `frontend/.env.local`:
```bash
cp frontend/.env.local.example frontend/.env.local
# Edit .env.local with your credentials
```

**Backend** - Create `backend/.env`:
```bash
cp backend/.env.example backend/.env
# Edit .env with your credentials
```

### 4. Run Locally

**Frontend:**
```bash
cd frontend
npm run dev
```

**Backend:**
```bash
cd backend
uvicorn main:app --reload
```

---

## ⚠️ Important Security Notes

1. **Never commit `.env` files** - They're in `.gitignore`
2. **Never commit database passwords** - Use environment variables
3. **Never commit API keys** - Store in `.env.local` or Render
4. **The pre-commit hook will block you** if you try to commit secrets

---

## 🔧 Manual Hook Installation

If the script doesn't work, manually copy the hook:

```bash
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

---

## 🚀 Deployment

See deployment guides:
- Frontend: Deploy to Vercel (auto-detects Next.js)
- Backend: Deploy to Render
- Database: PostgreSQL on Render

---

## 📚 Additional Documentation

- `FRONTEND_UX_IMPROVEMENTS.md` - UI/UX changes
- `DATABASE_MIGRATION_GUIDE.md` - Database setup
- `RENDER_COST_OPTIMIZATION.md` - Cost optimization
