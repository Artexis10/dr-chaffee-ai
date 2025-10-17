# Local Development Environment Setup

## Quick Start

### Backend Setup

```bash
cd backend

# Copy example to .env
cp .env.example.local .env

# Edit with your API keys
nano .env
```

**Required variables:**
```bash
DATABASE_URL=postgresql://drchaffee_db_user:R3shsw9dirMQQcnO8hFqO9L0MU8OSV4t@dpg-d3o0evc9c44c73cep47g-a.frankfurt-postgres.render.com/drchaffee_db
NOMIC_API_KEY=nk-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here
```

**Start backend:**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Setup

```bash
cd frontend

# Copy example to .env.local
cp .env.local.example .env.local

# Edit with your API keys
nano .env.local
```

**Required variables:**
```bash
DATABASE_URL=postgresql://drchaffee_db_user:R3shsw9dirMQQcnO8hFqO9L0MU8OSV4t@dpg-d3o0evc9c44c73cep47g-a.frankfurt-postgres.render.com/drchaffee_db
BACKEND_API_URL=http://localhost:8001
OPENAI_API_KEY=sk-proj-your-key-here
```

**Start frontend:**
```bash
npm run dev
```

---

## API Keys You Need

### 1. Nomic API Key (Free)
- Go to: https://atlas.nomic.ai/
- Sign up / Login
- Go to API Keys section
- Create new key
- Copy: `nk-...`
- Free tier: 10M tokens/month

### 2. OpenAI API Key
- Go to: https://platform.openai.com/api-keys
- Create new secret key
- **Set permissions**: Only `model.request`
- **Set limits**: $50/month, 60 RPM
- Copy: `sk-proj-...`

### 3. Database URL (Already Provided)
- Production database (read-only safe)
- Already in example files

---

## Local Development Modes

### Mode 1: Full Local (Recommended)
```bash
# Terminal 1: Backend
cd backend
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Access: http://localhost:3000
```

**Frontend → Local Backend → Production DB**

### Mode 2: Frontend Only
```bash
# Frontend only, use production backend
cd frontend

# Edit .env.local:
# BACKEND_API_URL=https://drchaffee-backend.onrender.com

npm run dev
```

**Frontend → Production Backend → Production DB**

### Mode 3: Backend Only
```bash
# Test backend API directly
cd backend
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload

# Test with curl:
curl -X POST http://localhost:8001/search \
  -H "Content-Type: application/json" \
  -d '{"query": "carnivore diet benefits", "top_k": 10}'
```

---

## Testing Your Setup

### 1. Test Backend

```bash
# Health check
curl http://localhost:8001/health

# Test search
curl -X POST http://localhost:8001/search \
  -H "Content-Type: application/json" \
  -d '{"query": "carnivore diet", "top_k": 5}'

# Test answer (requires OPENAI_API_KEY)
curl -X GET "http://localhost:8001/answer?query=carnivore+diet+benefits&top_k=5"
```

### 2. Test Frontend

1. Open http://localhost:3000
2. Type query: "carnivore diet benefits"
3. Should see search results
4. Should see AI-generated answer

---

## Troubleshooting

### Backend won't start
```bash
# Check if port 8001 is in use
lsof -i :8001

# Kill process if needed
kill -9 <PID>

# Or use different port
uvicorn api.main:app --port 8002
```

### Frontend won't start
```bash
# Check if port 3000 is in use
lsof -i :3000

# Install dependencies
npm install

# Clear cache
rm -rf .next
npm run dev
```

### Database connection fails
```bash
# Test connection
psql "postgresql://drchaffee_db_user:R3shsw9dirMQQcnO8hFqO9L0MU8OSV4t@dpg-d3o0evc9c44c73cep47g-a.frankfurt-postgres.render.com/drchaffee_db" -c "SELECT COUNT(*) FROM segments;"
```

### OpenAI API fails
```bash
# Check if key is set
echo $OPENAI_API_KEY

# Test key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## Environment Variables Reference

### Backend (.env)
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | - | PostgreSQL connection |
| `NOMIC_API_KEY` | ✅ | - | Nomic embeddings |
| `OPENAI_API_KEY` | ✅ | - | OpenAI for answers |
| `OPENAI_MODEL` | ❌ | `gpt-4-turbo` | Model to use |
| `PORT` | ❌ | `8001` | Server port |
| `LOG_LEVEL` | ❌ | `DEBUG` | Logging level |

### Frontend (.env.local)
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | - | PostgreSQL connection |
| `BACKEND_API_URL` | ✅ | - | Backend API URL |
| `OPENAI_API_KEY` | ⚠️ | - | Fallback RAG (optional) |
| `ANSWER_ENABLED` | ❌ | `true` | Enable answers |
| `NODE_ENV` | ❌ | `development` | Environment |

---

## Security Notes

### ⚠️ Never Commit .env Files
```bash
# Already in .gitignore:
.env
.env.local
.env*.local

# Safe to commit:
.env.example
.env.example.local
```

### 🔒 API Key Security
- ✅ Use environment variables
- ✅ Set OpenAI usage limits
- ✅ Use restricted permissions
- ❌ Never hardcode keys
- ❌ Never commit keys to Git
- ❌ Never share keys in chat/Slack

---

## Next Steps

1. ✅ Copy example files to `.env` / `.env.local`
2. ✅ Add your API keys
3. ✅ Start backend: `uvicorn api.main:app --port 8001 --reload`
4. ✅ Start frontend: `npm run dev`
5. ✅ Test: http://localhost:3000

**Happy coding! 🚀**
