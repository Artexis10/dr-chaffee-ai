# Discord OAuth Authentication

This document explains how to set up Discord OAuth authentication for the Ask Dr Chaffee main application.

## Overview

Discord OAuth allows users to log in using their Discord account. Access is gated by:
1. **Guild membership** - User must be a member of a specific Discord server
2. **Role requirement** - User must have at least one of the allowed roles

This feature is **optional** and works alongside the existing password authentication.

## Prerequisites

- A Discord account
- Admin access to a Discord server (to get Guild ID and Role IDs)
- Access to the [Discord Developer Portal](https://discord.com/developers/applications)

## Setup Instructions

### 1. Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Enter a name (e.g., "Ask Dr Chaffee")
4. Click **"Create"**

### 2. Configure OAuth2

1. In your application, go to **OAuth2** → **General**
2. Copy the **Client ID** and **Client Secret**
3. Add a redirect URI:
   - Development: `http://localhost:8000/auth/discord/callback`
   - Production: `https://your-backend-domain.com/auth/discord/callback`

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
DISCORD_REDIRECT_URI=http://localhost:8000/auth/discord/callback
DISCORD_GUILD_ID=your_guild_id_here
DISCORD_ALLOWED_ROLE_IDS=role_id_1,role_id_2,role_id_3
DISCORD_OAUTH_SCOPES=identify guilds.members.read
FRONTEND_APP_URL=http://localhost:3000
```

#### Frontend (`frontend/.env.local`)

```env
# Enable Discord login button
DISCORD_LOGIN_ENABLED=true
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
- Tuning dashboard continues to use its separate `tuning_auth` system

## Production Checklist

- [ ] Discord application created and configured
- [ ] Redirect URI set for production domain
- [ ] `DISCORD_CLIENT_SECRET` stored securely (not in git)
- [ ] `APP_SESSION_SECRET` set for token signing
- [ ] Database migration applied
- [ ] `DISCORD_LOGIN_ENABLED=true` in frontend
- [ ] All backend Discord env vars configured
- [ ] HTTPS enabled (required for secure cookies)
