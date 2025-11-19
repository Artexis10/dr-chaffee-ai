# Git Branching & Workflow Strategy

## Overview

This project uses a **feature-branch workflow** with a protected `main` branch. All changes go through pull requests with automated checks before merging. This ensures production stability even in solo development.

## Branch Types

### Main Branches

- **`main`** (protected)
  - Production-ready code
  - Runs on production servers
  - Requires PR review + all checks passing
  - Tagged with semantic versions (v1.0.0, v1.1.0, etc.)
  - **Rule**: Never commit directly to main

- **`develop`** (optional, for staging)
  - Pre-production testing
  - Integration point for features
  - Deploys to staging environment

### Feature Branches

Format: `feature/<feature-name>` or `feat/<feature-name>`

```bash
git checkout -b feature/custom-instructions
git checkout -b feat/youtube-api-integration
```

**Rules:**
- Branch from: `main` (or `develop` if exists)
- Merge back to: `main` via PR
- Naming: lowercase, hyphens, descriptive
- Examples:
  - `feature/add-voice-profiles`
  - `feature/improve-embeddings`
  - `feature/fix-ingestion-pipeline`

### Bug Fix Branches

Format: `bugfix/<bug-name>` or `fix/<bug-name>`

```bash
git checkout -b bugfix/segment-insertion-error
git checkout -b fix/numpy-compatibility
```

**Rules:**
- Branch from: `main`
- Merge back to: `main` via PR
- Reference issue: `fix: resolve #123`

### Hotfix Branches

Format: `hotfix/<issue-name>`

```bash
git checkout -b hotfix/production-crash
```

**Rules:**
- Branch from: `main` (only for critical production issues)
- Merge back to: `main` + `develop` (if exists)
- Requires immediate review
- Bumps patch version (v1.0.0 → v1.0.1)

### Documentation Branches

Format: `docs/<doc-name>`

```bash
git checkout -b docs/deployment-guide
git checkout -b docs/api-reference
```

**Rules:**
- Branch from: `main`
- Merge back to: `main` via PR
- No code changes

## Workflow

### 1. Create Feature Branch

```bash
# Update main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/my-feature
```

### 2. Make Changes

```bash
# Make commits with conventional format
git add .
git commit -m "feat: add new feature description"
git commit -m "test: add unit tests for feature"
git commit -m "docs: update README with feature info"
```

**Commit Message Format** (Conventional Commits):
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Code style (formatting, missing semicolons, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding/updating tests
- `chore:` - Build, dependencies, tooling
- `perf:` - Performance improvements

Example:
```
feat: add custom instructions for AI tuning

- Create database migration for custom_instructions table
- Add API endpoints for CRUD operations
- Implement frontend UI component
- Add comprehensive tests

Closes #42
```

### 3. Push & Create PR

```bash
# Push branch
git push origin feature/my-feature

# Create PR on GitHub (or use gh CLI)
gh pr create --title "feat: add custom instructions" --body "Description of changes"
```

**PR Title Format**: Same as commit messages
- ✅ `feat: add custom instructions`
- ✅ `fix: resolve segment insertion error`
- ❌ `Update stuff`
- ❌ `WIP`

### 4. Automated Checks

GitHub Actions will automatically run:

1. **PR Validation** (`pr-checks.yml`)
   - ✅ Conventional commit format check
   - ✅ Test coverage verification
   - ✅ File size checks
   - ✅ PR summary generation

2. **Code Quality** (`code-quality.yml`)
   - ✅ Linting (ruff, black)
   - ✅ Type checking (mypy)
   - ✅ Security scanning (bandit)

3. **Tests** (`unit-tests.yml`)
   - ✅ Unit tests (pytest)
   - ✅ Integration tests (if `--run-integration`)
   - ✅ Coverage reporting

4. **Security Scan** (`security-scan.yml`)
   - ✅ Dependency vulnerabilities (pip-audit)
   - ✅ Secret detection (Gitleaks)
   - ✅ SAST analysis (CodeQL)

**All checks must pass** before merging.

### 5. Self-Review

Before merging, verify:
- ✅ All automated checks pass
- ✅ Tests pass locally
- ✅ Code quality is good
- ✅ Security scan passes
- ✅ Documentation updated

### 6. Merge to Main

```bash
# Option 1: Squash commits (recommended for features)
# Keeps main history clean
# GitHub UI: Select "Squash and merge"

# Option 2: Create merge commit
# Preserves branch history
# GitHub UI: Select "Create a merge commit"

# Option 3: Rebase and merge
# Linear history
# GitHub UI: Select "Rebase and merge"
```

**After merge:**
```bash
# Delete branch
git branch -d feature/my-feature
git push origin --delete feature/my-feature

# Update local main
git checkout main
git pull origin main
```

## Protection Rules for `main`

Configured in GitHub repository settings:

- ✅ Require pull request (no direct pushes)
- ✅ Require status checks to pass:
  - Branch name validation
  - Commit message validation
  - Code Quality
  - Unit Tests
  - Security Scan
- ✅ Require branches to be up to date before merge
- ✅ Prevent accidental main-to-main PRs

## Release Process

### Semantic Versioning

Format: `v{MAJOR}.{MINOR}.{PATCH}`

- **MAJOR**: Breaking changes (v1.0.0 → v2.0.0)
- **MINOR**: New features (v1.0.0 → v1.1.0)
- **PATCH**: Bug fixes (v1.0.0 → v1.0.1)

### Creating a Release

```bash
# 1. Update version in code/docs
# 2. Create PR with version bump
# 3. Merge to main
# 4. Tag release
git tag -a v1.1.0 -m "Release v1.1.0: Add custom instructions"
git push origin v1.1.0

# 5. Create GitHub Release
# GitHub UI: Releases → Create Release from tag
```

## Common Scenarios

### Scenario 1: Feature Development

```bash
# Start feature
git checkout -b feature/new-feature
# ... make changes ...
git push origin feature/new-feature

# Create PR on GitHub
# Wait for checks to pass
# Get review approval
# Merge to main (squash)
```

### Scenario 2: Bug Fix

```bash
# Start bugfix
git checkout -b fix/bug-name
# ... fix bug ...
# ... add test ...
git push origin fix/bug-name

# Create PR
# Reference issue: "Closes #123"
# Merge to main
```

### Scenario 3: Production Hotfix

```bash
# Start hotfix (from main)
git checkout -b hotfix/critical-issue
# ... fix critical issue ...
git push origin hotfix/critical-issue

# Create PR with urgent label
# Fast-track review
# Merge to main
# Bump patch version
# Tag release
```

### Scenario 4: Rebase Before Merge

If main has moved ahead:

```bash
# Update main
git fetch origin main

# Rebase feature branch
git rebase origin/main feature/my-feature

# Force push (only on your branch!)
git push origin feature/my-feature --force-with-lease
```

## Best Practices

### Do's ✅

- ✅ Create branches for all changes
- ✅ Use descriptive branch names
- ✅ Write clear commit messages
- ✅ Keep branches focused (one feature per branch)
- ✅ Rebase before merge if needed
- ✅ Delete branches after merge
- ✅ Reference issues in commits/PRs
- ✅ Request reviews from team members
- ✅ Run tests locally before pushing

### Don'ts ❌

- ❌ Commit directly to main
- ❌ Use vague branch names (`update`, `fix`, `test`)
- ❌ Mix multiple features in one PR
- ❌ Ignore failing checks
- ❌ Force push to main
- ❌ Merge without approval
- ❌ Leave stale branches
- ❌ Commit secrets or API keys
- ❌ Skip tests

## Troubleshooting

### Accidentally committed to main

```bash
# Create new branch from current state
git branch feature/my-feature

# Reset main to previous commit
git reset --hard HEAD~1

# Push changes
git push origin feature/my-feature
git push origin main --force-with-lease  # Only if absolutely necessary
```

### Need to update branch with main changes

```bash
# Fetch latest main
git fetch origin main

# Rebase your branch
git rebase origin/main

# Force push (safe on your branch)
git push origin feature/my-feature --force-with-lease
```

### PR has merge conflicts

```bash
# Update main
git fetch origin main

# Rebase and resolve conflicts
git rebase origin/main

# Resolve conflicts in editor
# Then continue
git rebase --continue

# Force push
git push origin feature/my-feature --force-with-lease
```

## CI/CD Integration

### Automated Deployments

- **main** → Production (automatic after merge)
- **develop** → Staging (automatic after merge)
- **feature branches** → Preview environments (optional)

### Deployment Status

Check deployment status in PR:
- Green checkmark = deployment successful
- Red X = deployment failed
- Click "Details" to see logs

## Why This Matters (Solo Dev)

Even working alone, this workflow provides:

1. **Production Safety** - Main branch is always stable
2. **Easy Rollback** - If something breaks, revert the commit
3. **Clean History** - Conventional commits make it easy to find changes
4. **Automated Checks** - Catch bugs before they reach production
5. **Documentation** - Clear record of what changed and why

## Resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Semantic Versioning](https://semver.org/)
