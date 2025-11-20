# Tuning Dashboard Authentication Troubleshooting

## Error: "Connection error" on verify endpoint

### Root Causes

1. **`BACKEND_API_URL` not set on Vercel**
   - The frontend can't reach the backend
   - Check Vercel environment variables

2. **Backend not running or unreachable**
   - Render backend is down
   - Network connectivity issue

3. **`TUNING_PASSWORD` not set on Render**
   - Backend returns 503 (not configured)

4. **CORS issues**
   - Backend might not allow requests from Vercel domain

### Debug Steps

#### Step 1: Check Browser Console
Open DevTools (F12) → Console tab and look for:
```
[Tuning Auth Page] Submitting password...
[Tuning Auth Page] Response status: XXX
[Tuning Auth Page] Response data: {...}
```

#### Step 2: Check Vercel Function Logs
1. Go to Vercel dashboard
2. Select your project
3. Go to "Functions" tab
4. Click on `/api/tuning/auth/verify`
5. Look for logs showing:
   ```
   [Tuning Auth] Attempting to reach backend: https://...
   [Tuning Auth] Backend response status: XXX
   ```

#### Step 3: Verify Environment Variables

**On Vercel:**
```
BACKEND_API_URL=https://drchaffee-backend.onrender.com
```

**On Render (Backend):**
```
TUNING_PASSWORD=your_password_here
```

#### Step 4: Test Backend Directly

From your local machine:
```bash
curl -X POST https://drchaffee-backend.onrender.com/api/tuning/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"password":"your_password"}'
```

Expected response:
```json
{"success": true, "message": "Authentication successful"}
```

### Common Responses

| Status | Meaning | Fix |
|--------|---------|-----|
| 200 OK | Success | Working! |
| 400 | Password missing | Check form submission |
| 401 | Wrong password | Verify `TUNING_PASSWORD` |
| 503 | Not configured | Set `TUNING_PASSWORD` on Render |
| 500 | Connection error | Check `BACKEND_API_URL` |

### Solution Checklist

- [ ] `BACKEND_API_URL` is set on Vercel
- [ ] `TUNING_PASSWORD` is set on Render
- [ ] Backend is running on Render
- [ ] Password is correct
- [ ] Network connectivity is working
- [ ] Check browser console for detailed error
- [ ] Check Vercel function logs

### Quick Fix

If you see "Connection error" with backend URL in response:

1. **Verify the URL is correct:**
   ```
   https://drchaffee-backend.onrender.com
   ```

2. **Test it manually:**
   ```bash
   curl https://drchaffee-backend.onrender.com/api/tuning/auth/verify
   ```

3. **Check Render logs:**
   - Go to Render dashboard
   - Select your backend service
   - Check "Logs" tab for errors

### Authentication Flow

```
Frontend (Tuning Auth Page)
    ↓
    POST /api/tuning/auth/verify (Vercel)
    ↓
Frontend API Route
    ↓
    POST /api/tuning/auth/verify (Render Backend)
    ↓
Backend validates password
    ↓
Sets httpOnly cookie
    ↓
Returns success
    ↓
Frontend redirects to /tuning
```

Each step has logging - check console and Vercel logs to see where it fails!
