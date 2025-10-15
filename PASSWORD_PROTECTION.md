# Password Protection Feature

## Overview

The application now includes optional password protection to control access. When enabled, users must enter a password before accessing the main application.

## Features

- **Optional Protection**: Only active when `APP_PASSWORD` is set
- **Beautiful UI**: Professional password gate with Dr. Chaffee's photo
- **Session Persistence**: Authentication persists in browser localStorage
- **Secure**: Password checked server-side via API
- **Graceful Fallback**: If no password set, users access app directly

## Setup

### Enable Password Protection

Add to your `.env` file:

```env
APP_PASSWORD=your_secure_password_here
```

### Disable Password Protection

Leave empty or remove from `.env`:

```env
APP_PASSWORD=
```

Or simply don't set the variable at all.

## How It Works

1. **Check**: Frontend calls `/api/auth/check` to see if password is required
2. **Login**: If required, shows password gate
3. **Authenticate**: User enters password, calls `/api/auth/login`
4. **Token**: Server returns token, stored in localStorage
5. **Verify**: On subsequent visits, token is verified via `/api/auth/verify`
6. **Access**: If valid, user bypasses password gate

## API Endpoints

### GET /api/auth/check
Returns whether password protection is enabled.

**Response:**
```json
{
  "requiresPassword": true
}
```

### POST /api/auth/login
Authenticates user with password.

**Request:**
```json
{
  "password": "your_password"
}
```

**Response (Success):**
```json
{
  "success": true,
  "token": "abc123...",
  "message": "Authentication successful"
}
```

**Response (Failure):**
```json
{
  "error": "Invalid password"
}
```

### GET /api/auth/verify
Verifies authentication token.

**Headers:**
```
Authorization: Bearer abc123...
```

**Response:**
```json
{
  "valid": true
}
```

## Security Considerations

### Current Implementation (Development)
- Simple password comparison
- Basic token generation
- Client-side token storage

### Production Recommendations
1. **Use JWT tokens** with expiration
2. **Hash passwords** with bcrypt
3. **Store tokens** in Redis/database
4. **Add rate limiting** to prevent brute force
5. **Use HTTPS** in production
6. **Add CSRF protection**
7. **Implement token refresh** mechanism

## UI Design

The password gate features:
- Dr. Chaffee's photo in circular frame
- Gradient purple background
- Clean white card design
- Error feedback for wrong passwords
- Smooth animations and transitions
- Mobile-responsive layout

## Files Added

- `frontend/src/components/PasswordGate.tsx` - Main password gate component
- `frontend/src/pages/api/auth/check.ts` - Check if password required
- `frontend/src/pages/api/auth/login.ts` - Authenticate user
- `frontend/src/pages/api/auth/verify.ts` - Verify token
- `frontend/public/dr-chaffee.jpg` - Dr. Chaffee's photo

## Files Modified

- `frontend/src/pages/_app.tsx` - Wrapped app with PasswordGate
- `frontend/src/pages/index.tsx` - Added Dr. Chaffee's photo to header
- `.env.example` - Added APP_PASSWORD documentation

## Testing

1. **Without Password:**
   ```bash
   # Don't set APP_PASSWORD
   npm run dev
   ```
   → Should access app directly

2. **With Password:**
   ```bash
   # Set in .env
   APP_PASSWORD=test123
   npm run dev
   ```
   → Should show password gate
   → Enter "test123" to access

## Future Enhancements

- [ ] JWT-based authentication
- [ ] Password hashing
- [ ] Token expiration
- [ ] Rate limiting
- [ ] Multi-user support with database
- [ ] Password reset functionality
- [ ] Session management
- [ ] Audit logging
