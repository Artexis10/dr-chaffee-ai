# Git Quick Reference Card

## One-Minute Setup

```bash
# Clone repo
git clone https://github.com/Artexis10/dr-chaffee-ai.git
cd dr-chaffee-ai

# Create feature branch
git checkout -b feature/my-feature

# Make changes, then:
git add .
git commit -m "feat: description of change"
git push origin feature/my-feature

# Create PR on GitHub
# Wait for checks ✅
# Get approval ✅
# Merge ✅
```

## Branch Names

| Type | Format | Example |
|------|--------|---------|
| Feature | `feature/name` | `feature/custom-instructions` |
| Bug Fix | `fix/name` | `fix/numpy-compatibility` |
| Hotfix | `hotfix/name` | `hotfix/production-crash` |
| Docs | `docs/name` | `docs/deployment-guide` |
| Refactor | `refactor/name` | `refactor/improve-performance` |
| Test | `test/name` | `test/add-embeddings-tests` |

## Commit Messages

```
feat: add new feature
fix: resolve bug
docs: update guide
test: add unit tests
refactor: improve code
chore: update dependencies
perf: optimize performance
style: format code
```

## Common Commands

```bash
# Create & switch to branch
git checkout -b feature/my-feature

# See current branch
git branch

# Switch branches
git checkout feature/my-feature

# Stage changes
git add .
git add file.py

# Commit
git commit -m "feat: description"

# Push to GitHub
git push origin feature/my-feature

# Update branch with main
git fetch origin main
git rebase origin/main
git push origin feature/my-feature --force-with-lease

# Delete branch locally
git branch -d feature/my-feature

# Delete branch on GitHub
git push origin --delete feature/my-feature

# See commit history
git log --oneline

# See changes
git diff
git diff feature/my-feature...main
```

## PR Workflow

1. **Create branch** → `git checkout -b feature/name`
2. **Make changes** → Edit files
3. **Commit** → `git commit -m "feat: description"`
4. **Push** → `git push origin feature/name`
5. **Create PR** → GitHub UI (or `gh pr create`)
6. **Wait for checks** → GitHub Actions runs automatically
7. **Get approval** → Request review
8. **Merge** → Click merge button
9. **Delete branch** → `git push origin --delete feature/name`

## Automated Checks

All PRs must pass:

- ✅ **Branch name** - Must follow convention
- ✅ **Commit messages** - Must use conventional format
- ✅ **Code quality** - Linting, formatting, type checking
- ✅ **Tests** - Unit + integration tests
- ✅ **Security** - Vulnerability scan, secret detection
- ✅ **Coverage** - Minimum 80%

## Rules

### ✅ DO

- Create branch for every change
- Use descriptive branch names
- Write clear commit messages
- Run tests before pushing
- Request reviews
- Reference issues in PRs

### ❌ DON'T

- Commit directly to main
- Use vague names (`update`, `fix`, `test`)
- Mix multiple features in one PR
- Ignore failing checks
- Force push to main
- Commit secrets/API keys

## Troubleshooting

**Branch name invalid?**
```bash
# Rename branch
git branch -m feature/old-name feature/new-name
git push origin feature/new-name
git push origin --delete feature/old-name
```

**Need to update branch?**
```bash
git fetch origin main
git rebase origin/main
git push origin feature/my-feature --force-with-lease
```

**Merge conflicts?**
```bash
git rebase origin/main
# Edit conflicting files
git add .
git rebase --continue
git push origin feature/my-feature --force-with-lease
```

**Accidentally committed to main?**
```bash
git branch feature/my-feature
git reset --hard HEAD~1
git push origin feature/my-feature
```

## Links

- [Full Branching Strategy](BRANCHING_STRATEGY.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

**Need help?** Check BRANCHING_STRATEGY.md or ask in PR comments
