# Git Hooks Setup

## Pre-commit Hook (Secret Detection)

A pre-commit hook is installed at `.git/hooks/pre-commit` that automatically checks for:

### Blocked (Commit will fail):
- ❌ `.env` files (except `.env.example`)
- ❌ Database URLs with credentials (`postgresql://user:pass@host`)
- ❌ AWS access keys (`AKIA...`)
- ❌ Private keys (`BEGIN RSA PRIVATE KEY`)
- ❌ Known leaked passwords

### Warnings (Commit proceeds):
- ⚠️  Possible API keys or secrets (pattern matching)

## Installation

The hook is already installed if you cloned this repo. If it's missing:

```bash
# Copy the hook
cp .git/hooks/pre-commit.sample .git/hooks/pre-commit

# Or create it manually (see .git/hooks/pre-commit)

# Make it executable
chmod +x .git/hooks/pre-commit
```

## Testing

Try committing a file with a secret:

```bash
echo "DATABASE_URL=postgresql://user:password@host/db" > test.txt
git add test.txt
git commit -m "test"
# Should be blocked!
```

## Bypassing (Emergency Only)

If you absolutely must bypass the hook (NOT recommended):

```bash
git commit --no-verify -m "message"
```

## Platform Compatibility

- ✅ **Linux**: Fully supported
- ✅ **macOS**: Fully supported  
- ⚠️  **Windows**: Works in Git Bash, WSL, or with Git for Windows

### Windows Notes:

If using Windows, ensure:
1. Git Bash or WSL is installed
2. Hook has Unix line endings (LF, not CRLF)
3. Hook is executable: `chmod +x .git/hooks/pre-commit`

## Adding More Patterns

Edit `.git/hooks/pre-commit` and add patterns to the checks.

## CI/CD Integration

For additional security, consider adding:
- [GitGuardian](https://www.gitguardian.com/)
- [TruffleHog](https://github.com/trufflesecurity/trufflehog)
- [detect-secrets](https://github.com/Yelp/detect-secrets)

These can scan your entire git history for secrets.
