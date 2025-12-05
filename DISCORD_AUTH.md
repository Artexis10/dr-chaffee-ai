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

## Coexistence with Password Auth

Discord OAuth works alongside the existing password authentication:
- Both methods issue the same `auth_token` cookie
- Users can choose either method on the login page
- **Discord login now also grants tuning dashboard access** via `tuning_auth` cookie

## Tuning Dashboard Access

### How Discord Login Flows into Tuning Dashboard

1. User clicks "Log in with Discord" on the main app or tuning auth page
2. Frontend redirects to `/api/auth/discord/login` (Next.js proxy)
3. Backend redirects to Discord OAuth consent screen
4. User authorizes the application
5. Discord redirects to backend callback: `/auth/discord/callback`
6. Backend validates guild membership and roles
7. Backend sets three cookies:
   - `auth_token` - Main app authentication (7 days)
   - `discord_user_id` - User identification (7 days)
   - `tuning_auth=authenticated` - Tuning dashboard access (24 hours)
8. User is redirected to `FRONTEND_APP_URL`
9. Tuning dashboard checks `tuning_auth` cookie via `/api/tuning/auth/status`
10. If valid, dashboard loads; if not, redirects to `/tuning/auth`

### What Happens When Tuning Auth is Missing

When the `tuning_auth` cookie is missing or expired:

1. **Layout redirect**: `useTuningAuth` hook returns `isAuthenticated: false`
2. **Automatic redirect**: User is sent to `/tuning/auth` page
3. **Data hooks stop**: All `useTuningData` hooks detect 401 and stop retrying
4. **Clear UI message**: Pages show "Authentication required. Please log in again."

### Re-authentication

To re-authenticate:
1. Go to `/tuning/auth` and enter the admin password, OR
2. Click "Log in with Discord" (if Discord OAuth is configured)

Both methods set the `tuning_auth` cookie and grant dashboard access

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

### Development Testing

For local development:
```env
# backend/.env
DISCORD_REDIRECT_URI=http://localhost:8000/auth/discord/callback
FRONTEND_APP_URL=http://localhost:3000

# Discord Developer Portal: Add http://localhost:8000/auth/discord/callback
```
