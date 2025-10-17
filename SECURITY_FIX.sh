#!/bin/bash
# ============================================================================
# SECURITY FIX: Remove exposed database credentials from git history
# ============================================================================
# WARNING: This rewrites git history and requires force push!
# ============================================================================

set -e

echo "🚨 SECURITY FIX: Removing exposed credentials from git history"
echo ""
echo "⚠️  WARNING: This will rewrite git history!"
echo "⚠️  All collaborators will need to re-clone the repository!"
echo ""
read -p "Have you rotated the database password on Render? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Please rotate the database password first!"
    echo ""
    echo "Steps:"
    echo "1. Go to https://dashboard.render.com"
    echo "2. Select your PostgreSQL database"
    echo "3. Click 'Reset Password'"
    echo "4. Update the password in Render Dashboard → Backend Service → Environment"
    echo ""
    exit 1
fi

echo ""
echo "📝 Creating backup..."
git branch backup-before-security-fix

echo ""
echo "🔍 Finding exposed credentials..."
EXPOSED_PASSWORD="R3shsw9dirMQQcnO8hFqO9L0MU8OSV4t"

echo ""
echo "🧹 Removing credentials from git history..."
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch backend/.env.render backend/.env.example.local || true" \
  --prune-empty --tag-name-filter cat -- --all

echo ""
echo "🗑️  Cleaning up..."
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "✅ Git history cleaned!"
echo ""
echo "📤 NEXT STEPS:"
echo "1. Push the cleaned history:"
echo "   git push origin --force --all"
echo ""
echo "2. Verify on GitHub that credentials are gone"
echo ""
echo "3. All collaborators must re-clone:"
echo "   git clone https://github.com/Artexis10/dr-chaffee-ai.git"
echo ""
echo "⚠️  The backup branch 'backup-before-security-fix' contains the old history"
echo "   Delete it after confirming everything works:"
echo "   git branch -D backup-before-security-fix"
echo ""
