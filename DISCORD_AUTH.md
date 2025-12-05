# Discord OAuth Authentication

This document explains how to set up Discord OAuth authentication for the Ask Dr Chaffee main application.

## Overview

Discord OAuth allows users to log in using their Discord account. Access is gated by:
1. **Guild membership** - User must be a member of a specific Discord server
2. **Role requirement** - User must have at least one of the allowed roles

This feature is **optional** and works alongside the existing password authentication.

## Architecture

- **Discord Application**: "AskDrChaffee" (do not confuse with "Dr Chaffee AI")
- **Backend is the OAuth callback target** - Discord redirects directly to FastAPI
- **Scopes**: `identify guilds guilds.members.read`

### URL Structure

| Environment | Backend Login | Discord Callback (redirect_uri) |
|-------------|---------------|--------------------------------|
| Development | `http://localhost:8000/auth/discord/login` | `http://localhost:8000/auth/discord/callback` |
| Production  | `https://app.askdrchaffee.com/api/auth/discord/login` | `https://app.askdrchaffee.com/api/auth/discord/callback` |

> **Note**: In production, the backend is at `app.askdrchaffee.com` (via Traefik), and routes have the `/api` prefix externally.

## Prerequisites

- A Discord account
- Admin access to a Discord server (to get Guild ID and Role IDs)
- Access to the [Discord Developer Portal](https://discord.com/developers/applications)

## Setup Instructions

### 1. Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Enter name: **"AskDrChaffee"**
4. Click **"Create"**

### 2. Configure OAuth2

1. In your application, go to **OAuth2** → **General**
2. Copy the **Client ID** and **Client Secret**
3. Add redirect URIs (both if you need dev + prod):
   - Development: `http://localhost:8000/auth/discord/callback`
   - Production: `https://app.askdrchaffee.com/api/auth/discord/callback`
   
   > **CRITICAL**: The redirect URI must match EXACTLY - including scheme (https), subdomain (app.), and path. No trailing slash!

### 3. Get Guild ID

1. Enable Developer Mode in Discord:
   - User Settings → App Settings → Advanced → Developer Mode
2. Right-click your server name → **Copy Server ID**

### 4. Get Role IDs

1. Go to Server Settings → Roles
2. Right-click the role you want to allow → **Copy Role ID**
3. Repeat for each role that should have access

### 5. Configure Environment Variables

#### Backend (`backend/.env`)

```env
# Discord OAuth Configuration
DISCORD_CLIENT_ID=your_client_id_here
DISCORD_CLIENT_SECRET=your_client_secret_here
DISCORD_GUILD_ID=your_guild_id_here
DISCORD_ALLOWED_ROLE_IDS=role_id_1,role_id_2,role_id_3
DISCORD_OAUTH_SCOPES=identify guilds guilds.members.read
FRONTEND_APP_URL=http://localhost:3000

# IMPORTANT: redirect_uri must match EXACTLY what's in Discord Developer Portal
# Dev:
DISCORD_REDIRECT_URI=http://localhost:8000/auth/discord/callback
# Prod (note: app. subdomain + /api prefix):
# DISCORD_REDIRECT_URI=https://app.askdrchaffee.com/api/auth/discord/callback
```

#### Frontend (`frontend/.env.local`)

```env
# Enable Discord login button
DISCORD_LOGIN_ENABLED=true

# Backend URL (for API proxying)
# Dev:
BACKEND_API_URL=http://localhost:8000
# Prod: set via Coolify
```

### 6. Run Database Migration

```bash
cd backend
alembic upgrade head
```

This creates the `users` table for storing Discord user information.

## How It Works

### Authentication Flow

1. User clicks **"Log in with Discord"** on the login page
2. Frontend redirects to `/api/auth/discord/login`
3. Backend generates a secure state token and redirects to Discord
4. User authorizes the application on Discord
5. Discord redirects back to `/auth/discord/callback` with an authorization code
6. Backend:
   - Validates the state token (CSRF protection)
   - Exchanges the code for an access token
   - Fetches user info (`/users/@me`)
   - Checks guild membership (`/users/@me/guilds/{guild_id}/member`)
   - Validates role requirements
   - Creates/updates user record in database
   - Issues `auth_token` cookie (same as password login)
7. User is redirected to the main application

### Error Handling

- **Not in guild**: Redirects to `/auth/discord/not-in-server`
- **Missing required role**: Redirects to `/auth/discord/insufficient-role`
- **OAuth errors**: Redirects to `/auth/discord/error`

## Security Considerations

- **State token**: Stored in HttpOnly cookie, prevents CSRF attacks
- **Access tokens**: Never exposed to frontend, used only server-side
- **Session tokens**: Same HMAC-SHA256 signed tokens as password login
- **No global member sync**: Only checks individual user's membership (privacy-preserving)

## API Endpoints

### Backend

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/discord/login` | GET | Initiates OAuth flow |
| `/auth/discord/callback` | GET | Handles OAuth callback |
| `/auth/discord/status` | GET | Returns configuration status |

### Frontend

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/discord/login` | GET | Proxy to backend login |
| `/api/auth/discord/status` | GET | Checks if Discord is enabled |

## Troubleshooting

### Discord login button not showing

1. Check `DISCORD_LOGIN_ENABLED=true` in frontend `.env.local`
2. Check backend Discord configuration is complete
3. Check browser console for errors

### "Not in server" error

- Verify the user is a member of the correct Discord server
- Check `DISCORD_GUILD_ID` is correct

### "Insufficient role" error

- Verify the user has one of the allowed roles
- Check `DISCORD_ALLOWED_ROLE_IDS` contains the correct role IDs
- Role IDs should be comma-separated without spaces

### OAuth redirect errors

- Verify `DISCORD_REDIRECT_URI` matches exactly what's configured in Discord Developer Portal
- Check for trailing slashes - they must match exactly

### State mismatch errors

- Clear browser cookies and try again
- Check that cookies are being set correctly (not blocked by browser)

## Database Schema

The `users` table stores Discord user information:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    discord_id VARCHAR(255) UNIQUE,
    discord_username VARCHAR(255),
    discord_discriminator VARCHAR(10),
    discord_global_name VARCHAR(255),
    discord_avatar VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);
```

## Authentication Layer Separation

**IMPORTANT**: Discord OAuth and Tuning Dashboard authentication are completely separate systems.

### Main App (Public Users)
- ✅ Discord OAuth for authentication
- ✅ Password authentication (fallback)
- Sets `auth_token` cookie for main app access

### Tuning Dashboard (Admins Only)
- ✅ Password authentication ONLY
- ❌ NO Discord OAuth
- ❌ NO role-based access
- Sets `tuning_auth` cookie for dashboard access

### Why Separate?

The tuning dashboard is an internal admin-only interface for 2 people (you and Dr. Chaffee).
It should NOT be accessible via Discord login because:
1. Discord users should not have admin access
2. Keeps the admin panel isolated and secure
3. Simpler security model (single strong password)

### Tuning Dashboard Authentication Flow

1. User visits `/tuning` or any `/tuning/*` page
2. `useTuningAuth` hook checks for `tuning_auth` cookie
3. If missing, user is redirected to `/tuning/auth`
4. User enters admin password
5. Password verified via `/api/tuning/auth/verify`
6. On success, `tuning_auth=authenticated` cookie is set
7. User is redirected to `/tuning`

### What Discord Login Does NOT Do

Discord login:
- ✅ Sets `auth_token` cookie (main app)
- ✅ Sets `discord_user_id` cookie (user info)
- ❌ Does NOT set `tuning_auth` cookie
- ❌ Does NOT grant tuning dashboard access

## Production Checklist

- [ ] Discord application "AskDrChaffee" created and configured
- [ ] Redirect URI `https://app.askdrchaffee.com/api/auth/discord/callback` added in Discord Developer Portal
- [ ] `DISCORD_REDIRECT_URI=https://app.askdrchaffee.com/api/auth/discord/callback` set in backend env (Coolify)
- [ ] `FRONTEND_APP_URL=https://askdrchaffee.com` set in backend env (where users land after auth)
- [ ] `DISCORD_CLIENT_SECRET` stored securely (not in git)
- [ ] `APP_SESSION_SECRET` set for token signing
- [ ] Database migration applied (`alembic upgrade head`)
- [ ] `DISCORD_LOGIN_ENABLED=true` in frontend env
- [ ] All backend Discord env vars configured (CLIENT_ID, SECRET, GUILD_ID, ROLE_IDS)
- [ ] HTTPS enabled (required for secure cookies)

## Testing Discord Login End-to-End

### Quick Verification Steps

1. **Check backend config status:**
   ```bash
   curl https://app.askdrchaffee.com/api/auth/discord/status
   ```
   Verify `enabled: true` and `redirect_uri` matches what's in Discord Developer Portal.

2. **Check Discord Developer Portal:**
   - Go to https://discord.com/developers/applications
   - Select "AskDrChaffee" application
   - OAuth2 → Redirects
   - Verify `https://app.askdrchaffee.com/api/auth/discord/callback` is listed

3. **Test the login flow:**
   - Visit https://askdrchaffee.com
   - Click "Log in with Discord"
   - Should redirect to Discord authorization page
   - After authorizing, should redirect back to the app

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Invalid OAuth2 redirect_uri" | Mismatch between `DISCORD_REDIRECT_URI` and Discord Portal | Add exact URI to Discord Developer Portal |
| Redirect to wrong domain | `FRONTEND_APP_URL` incorrect | Set `FRONTEND_APP_URL=https://askdrchaffee.com` |
| "State mismatch" error | Cookies not being set/read | Check SameSite cookie settings, HTTPS requirement |
| "Not in server" after auth | User not in Discord guild | Verify `DISCORD_GUILD_ID` is correct |

### Local Development vs Production

#### Production Setup
- Frontend: `https://askdrchaffee.com` (Vercel)
- Backend: `https://app.askdrchaffee.com` (Coolify)
- Discord OAuth: Enabled for main app login
- `DISCORD_LOGIN_ENABLED=true` in frontend env
- Tuning dashboard: Password-only (separate from Discord)

#### Local Development

For local development:

```env
# frontend/.env.local
DISCORD_LOGIN_ENABLED=false  # Hide Discord button on main app
BACKEND_API_URL=https://app.askdrchaffee.com  # Can use remote backend
```

**Main app login**: Use password authentication (Discord button hidden)
**Tuning dashboard**: Always use password authentication at `/tuning/auth`

#### Testing Discord OAuth Locally (Main App Only)

If you need to test Discord OAuth for the main app:

1. **Add local redirect URI to Discord Developer Portal:**
   - Go to https://discord.com/developers/applications
   - Select "AskDrChaffee" application
   - OAuth2 → Redirects → Add `http://localhost:8000/auth/discord/callback`

2. **Configure backend:**
   ```env
   # backend/.env
   DISCORD_REDIRECT_URI=http://localhost:8000/auth/discord/callback
   FRONTEND_APP_URL=http://localhost:3000
   ```

3. **Configure frontend:**
   ```env
   # frontend/.env.local
   DISCORD_LOGIN_ENABLED=true
   BACKEND_API_URL=http://localhost:8000
   ```

4. **Run both services locally:**
   - Backend: `uvicorn api.main:app --reload --port 8000`
   - Frontend: `npm run dev`

**Note:** This only affects the main app login. The tuning dashboard (`/tuning/*`) always uses password authentication regardless of Discord settings.
