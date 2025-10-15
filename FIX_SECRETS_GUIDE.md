# 🔐 Fix Exposed Secrets in Git

## Problem

GitHub blocked your push because API keys were committed in:
- `backend/.env.production.cpu` (commit `59109aa`)

**Exposed**:
- Hugging Face Token: `hf_****` (redacted)
- OpenAI API Key: `sk-proj-****` (redacted)

---

## ✅ Solution (Choose One)

### Option 1: Simple Fix (Recommended)

**Just remove the secrets and force push**:

```powershell
cd C:\Users\hugoa\Desktop\ask-dr-chaffee

# Secrets are already removed from the file
# Now amend the problematic commit

# Reset to before the bad commit
git reset --soft 902980e

# Re-stage everything
git add .

# Recommit without secrets
git commit -m "feat: add production environment configuration templates

- .env.production: GPU-optimized config (for reference)  
- .env.production.cpu: CPU-optimized config for production server
- Uses same embedding model (GTE-Qwen2-1.5B) to avoid dimension mismatch
- API keys are placeholders (set real values in production)"

# Re-apply other commits
git cherry-pick 3570343  # systemd timer
git cherry-pick c24cb10  # documentation
git cherry-pick a9f583f  # deployment summary

# Force push (rewrites history)
git push --force-with-lease
```

### Option 2: Use GitHub's Allow Secret Feature

**Temporarily allow the secrets** (if you plan to rotate them anyway):

1. Click the GitHub link from the error:
   ```
   https://github.com/Artexis10/dr-chaffee-ai/security/secret-scanning/unblock-secret/347H9ea0GM7nwnyTpVRWuyWU8lB
   https://github.com/Artexis10/dr-chaffee-ai/security/secret-scanning/unblock-secret/347H9gUZZ2iirAVpBnWm27CfSQb
   ```

2. Click "Allow secret" for each

3. Push again:
   ```powershell
   git push
   ```

4. **IMMEDIATELY rotate the keys**:
   - Hugging Face: https://huggingface.co/settings/tokens
   - OpenAI: https://platform.openai.com/api-keys

---

## 🔒 After Fixing

### 1. Rotate Your API Keys (IMPORTANT!)

Even though we removed them from the file, they're still in git history until you force push.

**Rotate immediately**:

#### Hugging Face Token
1. Go to https://huggingface.co/settings/tokens
2. Delete the exposed token (starts with `hf_`)
3. Create new token
4. Update in your local `.env` file (NOT in git!)

#### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Revoke the exposed key (starts with `sk-proj-`)
3. Create new key
4. Update in your local `.env` file (NOT in git!)

### 2. Add .env to .gitignore

Make sure `.env` files are never committed:

```powershell
# Check .gitignore
cat .gitignore | Select-String ".env"

# Should see:
# .env
# .env.local
# .env.*.local
```

### 3. Use Environment Variables in Production

On production server, set secrets as environment variables:

```bash
# Don't put in .env file!
export OPENAI_API_KEY="your-new-key"
export HUGGINGFACE_HUB_TOKEN="your-new-token"
```

Or use a secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)

---

## 📋 Prevention Checklist

- [ ] Never commit `.env` files with real secrets
- [ ] Use placeholders in template files (`.env.example`, `.env.production.cpu`)
- [ ] Add `.env` to `.gitignore`
- [ ] Use environment variables in production
- [ ] Enable GitHub secret scanning (already enabled!)
- [ ] Rotate keys immediately if exposed
- [ ] Use secrets managers for production

---

## 🎯 Recommended: Option 1 (Rewrite History)

This is cleaner because:
- ✅ Secrets never exist in git history
- ✅ No need to rotate keys
- ✅ Clean commit history

**Steps**:
1. Run the commands from Option 1 above
2. Force push: `git push --force-with-lease`
3. Done! No key rotation needed.

---

## ⚠️ About Force Push

`git push --force-with-lease` is safe because:
- Only rewrites YOUR commits (not others')
- Fails if someone else pushed in the meantime
- Better than `--force` which is dangerous

**Only do this if**:
- You're the only one working on this branch
- OR you've coordinated with your team
