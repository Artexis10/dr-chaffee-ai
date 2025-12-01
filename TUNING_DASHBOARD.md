# Tuning Dashboard

The Tuning Dashboard provides administrative controls for configuring the Dr. Chaffee AI system.

## Access

- **URL**: `/tuning`
- **Authentication**: Password-protected via `TUNING_PASSWORD` environment variable
- **Cookie**: `tuning_auth` (httpOnly, secure in production, 24-hour expiration)

## Features

### 1. Summarizer Model Selection (`/tuning/models`)

Configure which OpenAI model generates answers from search results.

**Available Models**:
- `gpt-4.1` - Best quality, higher cost
- `gpt-4o-mini` - Good balance of quality and cost (default)
- `gpt-4o` - High quality, fast
- `gpt-3.5-turbo` - Budget option

**How it works**:
- Model selection is stored in `SUMMARIZER_MODEL` environment variable at runtime
- Temperature is configurable via `SUMMARIZER_TEMPERATURE` (default: 0.3)
- Changes take effect immediately for new queries
- Does NOT affect search/embeddings (those use local models)

### 2. Search Configuration (`/tuning/search`)

Tune search parameters for vector similarity search.

**Parameters**:
- `top_k` - Initial results to consider (default: 100)
- `min_similarity` - Minimum relevance threshold 0-1 (default: 0.3)
- `enable_reranker` - Use AI reranking for better accuracy (slower)
- `rerank_top_k` - Results to rerank if enabled (default: 200)
- `return_top_k` - Final clips to use in answer (default: 20)

**Persistence**:
- Stored in `search_config` database table
- Requires migration `003_api_cache_table.sql` or later
- Falls back to defaults if table doesn't exist

### 3. Custom Instructions (`/tuning/instructions`)

Add custom guidance to the AI without modifying core safety rules.

**Features**:
- Create multiple instruction sets
- Activate/deactivate sets instantly
- Version history with rollback
- Preview merged prompt before saving
- Character limit: 10,000 characters

**How it works**:
- Instructions are layered on top of baseline `chaffee_persona.md`
- Stored in `custom_instructions` table with versioning
- Active instructions are merged at runtime via `prompt_loader.py`

## Authentication Flow

1. User visits `/tuning` → redirected to `/tuning/auth` if not authenticated
2. User enters password → frontend proxy calls backend `/api/tuning/auth/verify`
3. Backend validates against `TUNING_PASSWORD` env var
4. On success:
   - Backend sets `tuning_auth` cookie (httpOnly, secure in prod)
   - Frontend proxy also sets `auth_token` for main app SSO
5. Subsequent requests include cookie → `require_tuning_auth` dependency validates

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TUNING_PASSWORD` | Dashboard access password | Required |
| `SUMMARIZER_MODEL` | OpenAI model for answers | `gpt-4.1` |
| `SUMMARIZER_TEMPERATURE` | Model temperature | `0.3` |
| `ENVIRONMENT` | `production` or `development` | `development` |

## Theme

- Default: **Dark mode**
- Toggle available in sidebar footer
- Persisted in `localStorage` key: `askdrchaffee.theme`
- Smooth transitions on all elements (0.3s ease)

## API Endpoints

All endpoints require `tuning_auth` cookie (except `/auth/verify`).

### Authentication
- `POST /api/tuning/auth/verify` - Validate password, set cookie
- `POST /api/tuning/auth/logout` - Clear cookies

### Summarizer
- `GET /api/tuning/summarizer/models` - List available models
- `GET /api/tuning/summarizer/config` - Get current config
- `POST /api/tuning/summarizer/config` - Update config

### Search
- `GET /api/tuning/search-config` - Get search parameters
- `PUT /api/tuning/search-config` - Update search parameters

### Custom Instructions
- `GET /api/tuning/instructions` - List all instruction sets
- `GET /api/tuning/instructions/active` - Get active set
- `POST /api/tuning/instructions` - Create new set
- `PUT /api/tuning/instructions/{id}` - Update set
- `POST /api/tuning/instructions/{id}/activate` - Activate set
- `DELETE /api/tuning/instructions/{id}` - Delete set
- `POST /api/tuning/instructions/preview` - Preview merged prompt
- `GET /api/tuning/instructions/{id}/history` - Version history
- `POST /api/tuning/instructions/{id}/rollback/{version}` - Rollback

### Stats
- `GET /api/tuning/stats` - Database statistics

## File Structure

```
frontend/src/
├── app/tuning/
│   ├── auth/page.tsx      # Login page
│   ├── layout.tsx         # Dashboard layout with sidebar
│   ├── page.tsx           # Overview/stats page
│   ├── models/page.tsx    # Summarizer model selection
│   ├── search/page.tsx    # Search config
│   ├── instructions/page.tsx  # Custom instructions
│   └── tuning-pages.css   # Page-specific styles
├── styles/
│   ├── tuning.css         # Layout styles
│   └── custom-instructions.css  # Editor styles
└── pages/api/tuning/
    ├── [...path].ts       # Proxy to backend
    └── auth/
        ├── verify.ts      # Login handler
        └── logout.ts      # Logout handler

backend/api/
└── tuning.py              # All tuning endpoints
```

## Security Notes

1. **Password**: Never expose `TUNING_PASSWORD` in frontend code
2. **Cookies**: `httpOnly` prevents XSS access, `secure` enforces HTTPS in production
3. **CSRF**: `samesite=lax` provides protection while allowing navigation
4. **Validation**: All inputs validated server-side before processing
5. **Custom Instructions**: Cannot override baseline safety rules (additive only)

## Troubleshooting

### Login not working
- Check `TUNING_PASSWORD` is set in backend `.env`
- In development, ensure `ENVIRONMENT=development` (allows HTTP cookies)
- Check browser console for cookie errors

### Settings not persisting
- Search config requires `search_config` table (run migrations)
- Summarizer model is runtime-only (resets on server restart)
- Custom instructions persist in database

### Theme issues
- Clear `localStorage` key `askdrchaffee.theme`
- Ensure `dark-mode` or `light-mode` class on `<html>` element
