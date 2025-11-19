# Development Workflow Guide

This guide explains the development workflow for the Dr. Chaffee AI project.

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/Artexis10/dr-chaffee-ai.git
cd dr-chaffee-ai

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

```bash
# Make your changes
# Test locally
# Commit with conventional format
git add .
git commit -m "feat: add new feature"
```

### 3. Push & Create PR

```bash
# Push branch
git push origin feature/your-feature-name

# Create PR on GitHub
# Title: "feat: add new feature"
# Description: Explain what and why
```

### 4. Automated Checks Run

GitHub Actions automatically validates:
- ✅ Branch name format
- ✅ Commit message format
- ✅ Code quality
- ✅ Unit tests
- ✅ Integration tests
- ✅ Security scan

All checks must pass before merging to main.

## Branch Naming

Format: `<type>/<description>`

**Valid types:**
- `feature/` - New feature
- `feat/` - New feature (short)
- `fix/` - Bug fix
- `bugfix/` - Bug fix (long)
- `hotfix/` - Critical production fix
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Tests
- `chore/` - Build/tooling
- `perf/` - Performance

**Examples:**
```bash
git checkout -b feature/custom-instructions
git checkout -b fix/numpy-compatibility
git checkout -b docs/deployment-guide
git checkout -b test/add-embeddings-tests
```

## Commit Messages

Use **Conventional Commits** format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Code style (formatting)
- `refactor` - Code refactoring
- `test` - Tests
- `chore` - Build/dependencies
- `perf` - Performance

**Examples:**

```bash
# Simple feature
git commit -m "feat: add custom instructions for AI tuning"

# Bug fix with scope
git commit -m "fix(ingestion): resolve segment insertion error"

# With body and footer
git commit -m "feat: add voice profile support

- Create voice enrollment endpoint
- Add speaker identification
- Store voice embeddings

Closes #42"

# Documentation
git commit -m "docs: update README with setup instructions"
```

## Pull Requests

### PR Title Format

Same as commit messages:
- ✅ `feat: add custom instructions`
- ✅ `fix: resolve segment insertion error`
- ✅ `docs: update deployment guide`
- ❌ `Update stuff`
- ❌ `WIP`
- ❌ `Fix bug`

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Performance improvement
- [ ] Breaking change

## Related Issues
Closes #123

## Testing
- [ ] Added unit tests
- [ ] Added integration tests
- [ ] Tested locally

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed changes
- [ ] Added comments for complex logic
- [ ] Updated documentation
- [ ] No new warnings generated
- [ ] Tests pass locally
```

## Code Style

### Python

```bash
# Format code
black backend/ frontend/

# Lint code
ruff check backend/ frontend/

# Type checking
mypy backend/
```

### JavaScript/TypeScript

```bash
# Format code
prettier --write frontend/

# Lint code
eslint frontend/
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Testing

### Run Tests Locally

```bash
cd backend

# Unit tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=backend --cov-report=html

# Integration tests
python -m pytest tests/ --run-integration -v
```

### Test Requirements

- ✅ New features need tests
- ✅ Bug fixes need regression tests
- ✅ Minimum 80% coverage
- ✅ All tests must pass

## Security

### Secrets

**Never commit:**
- API keys
- Passwords
- Tokens
- Private keys

**Use environment variables:**
```bash
# .env (gitignored)
YOUTUBE_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

### Dependency Updates

- Use `pip-audit` to check for vulnerabilities
- Update dependencies regularly
- Run security scan before merge

```bash
pip-audit
```

## Documentation

### Update These Files

- `README.md` - Overview & setup
- `BRANCHING_STRATEGY.md` - Git workflow
- `CONTRIBUTING.md` - This file
- Code comments - Complex logic
- Docstrings - Functions/classes

### Documentation Format

```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of what function does.
    
    Longer description if needed, explaining:
    - What it does
    - Why it's useful
    - Any important notes
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When something is invalid
    
    Example:
        >>> result = my_function("test", 42)
        >>> print(result)
        True
    """
    pass
```

## Common Workflows

### Adding a Feature

```bash
# 1. Create branch
git checkout -b feature/my-feature

# 2. Make changes
# ... edit files ...

# 3. Add tests
# ... create test_my_feature.py ...

# 4. Commit
git add .
git commit -m "feat: add my feature"
git commit -m "test: add tests for my feature"

# 5. Push
git push origin feature/my-feature

# 6. Create PR on GitHub
# Wait for checks
# Get approval
# Merge
```

### Fixing a Bug

```bash
# 1. Create branch
git checkout -b fix/bug-name

# 2. Fix bug
# ... edit files ...

# 3. Add regression test
# ... create test that catches bug ...

# 4. Commit
git add .
git commit -m "fix: resolve bug description"
git commit -m "test: add regression test for bug"

# 5. Push & PR
git push origin fix/bug-name
# Create PR referencing issue: "Closes #123"
```

### Updating Documentation

```bash
# 1. Create branch
git checkout -b docs/update-guide

# 2. Update docs
# ... edit .md files ...

# 3. Commit
git add .
git commit -m "docs: update deployment guide"

# 4. Push & PR
git push origin docs/update-guide
```

## Troubleshooting

### PR checks failing?

1. **Branch name invalid**
   - Use format: `feature/name`, `fix/name`, etc.

2. **Commit messages invalid**
   - Use format: `feat: description`, `fix: description`, etc.

3. **Tests failing**
   - Run locally: `pytest tests/ -v`
   - Check error messages
   - Fix code or tests

4. **Code quality issues**
   - Run: `black .` and `ruff check .`
   - Fix issues
   - Commit: `git add . && git commit -m "style: format code"`

5. **Security scan failing**
   - Run: `pip-audit`
   - Update vulnerable packages
   - Commit: `git add . && git commit -m "chore: update dependencies"`

### Need to update branch?

```bash
# Fetch latest main
git fetch origin main

# Rebase your branch
git rebase origin/main

# Force push (safe on your branch)
git push origin feature/my-feature --force-with-lease
```

### Merge conflicts?

```bash
# Rebase and resolve
git rebase origin/main

# Edit conflicting files
# Mark as resolved
git add .
git rebase --continue

# Force push
git push origin feature/my-feature --force-with-lease
```

## Notes

- **Solo development** - No PR approvals needed, just ensure checks pass
- **Production safety** - Main branch is protected, all changes via branches
- **Automated validation** - GitHub Actions catches issues before merge
- **Easy rollback** - If something breaks, revert the commit

## Resources

- [Branching Strategy](BRANCHING_STRATEGY.md)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Semantic Versioning](https://semver.org/)

---

**Happy coding!** 🚀
