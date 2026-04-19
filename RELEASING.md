# Release Checklist

This document outlines the complete process for releasing a new version of AgentMind.

## Pre-Release Checklist

### Code Quality

- [ ] All tests pass locally (`pytest tests/ -v`)
- [ ] Linting passes (`ruff check src/`)
- [ ] Type checking passes (`mypy src/`)
- [ ] Code coverage is acceptable (`pytest --cov=agentmind tests/`)
- [ ] No critical security vulnerabilities (`bandit -r src/`)

### Documentation

- [ ] CHANGELOG.md is up to date
- [ ] README.md reflects current features
- [ ] API documentation is current
- [ ] Example code works with new version
- [ ] Migration guide written (for breaking changes)

### Version Control

- [ ] Working directory is clean (`git status`)
- [ ] On main/master branch
- [ ] All changes committed
- [ ] Pulled latest from remote (`git pull`)
- [ ] No merge conflicts

### Dependencies

- [ ] Dependencies in setup.py are current
- [ ] Requirements files are updated
- [ ] No deprecated dependencies
- [ ] Security audit passed (`pip-audit`)

## Release Process

### 1. Determine Version Number

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes, incompatible API changes
- **MINOR** (0.X.0): New features, backwards compatible
- **PATCH** (0.0.X): Bug fixes, backwards compatible

Current version: Check `setup.py` or run:
```bash
python -c "import agentmind; print(agentmind.__version__)"
```

### 2. Update Version

#### Option A: Automated (Recommended)

Use the release script:
```bash
./scripts/release.sh
```

This will:
- Prompt for version bump type
- Run tests and linting
- Update version numbers
- Generate changelog
- Create git tag
- Build package
- Optionally publish to PyPI

#### Option B: Manual

Update version manually:
```bash
# Bump version
python scripts/bump_version.py <major|minor|patch>

# Or set custom version
python scripts/bump_version.py custom 1.2.3
```

This updates:
- `setup.py`
- `src/agentmind/__init__.py`
- `pyproject.toml`

### 3. Update Changelog

Add entry to `CHANGELOG.md`:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security improvements
```

Generate from git commits:
```bash
git log $(git describe --tags --abbrev=0)..HEAD --pretty=format:"- %s (%h)" --no-merges
```

### 4. Run Final Tests

```bash
# Unit tests
pytest tests/ -v

# Integration tests
pytest tests/integration/ -v

# Coverage report
pytest --cov=agentmind --cov-report=html tests/

# Linting
ruff check src/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

### 5. Build Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build source and wheel distributions
python -m build

# Verify package
twine check dist/*
```

### 6. Commit and Tag

```bash
# Commit version changes
git add setup.py src/agentmind/__init__.py pyproject.toml CHANGELOG.md
git commit -m "Release version X.Y.Z"

# Create annotated tag
git tag -a vX.Y.Z -m "Release version X.Y.Z"

# Push commits and tags
git push origin main
git push origin vX.Y.Z
```

### 7. Create GitHub Release

1. Go to https://github.com/cym3118288-afk/AgentMind-Framework/releases/new
2. Select the tag you just created (vX.Y.Z)
3. Title: "Release X.Y.Z"
4. Description: Copy from CHANGELOG.md
5. Attach built distributions from `dist/`
6. Mark as pre-release if applicable
7. Click "Publish release"

### 8. Publish to PyPI

#### Test PyPI (Optional)

```bash
# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ agentmind
```

#### Production PyPI

```bash
# Upload to PyPI
twine upload dist/*

# Verify installation
pip install --upgrade agentmind
python -c "import agentmind; print(agentmind.__version__)"
```

### 9. Update Documentation

- [ ] Update documentation site (if applicable)
- [ ] Update examples with new version
- [ ] Update installation instructions
- [ ] Announce on documentation homepage

### 10. Announce Release

- [ ] Post on GitHub Discussions
- [ ] Update project README badges
- [ ] Tweet/social media announcement
- [ ] Update project website
- [ ] Notify major users/contributors

## Post-Release Checklist

### Verification

- [ ] Package available on PyPI
- [ ] Installation works: `pip install agentmind==X.Y.Z`
- [ ] GitHub release created
- [ ] Documentation updated
- [ ] CI/CD pipeline passed

### Monitoring

- [ ] Monitor GitHub issues for bug reports
- [ ] Check PyPI download statistics
- [ ] Monitor CI/CD for failures
- [ ] Review user feedback

### Cleanup

- [ ] Close milestone (if using GitHub milestones)
- [ ] Update project board
- [ ] Archive old releases (if needed)
- [ ] Update roadmap

## Rollback Procedure

If critical issues are discovered:

### 1. Yank Release from PyPI

```bash
# Mark version as yanked (doesn't delete, but prevents new installs)
pip install twine
twine upload --skip-existing dist/*  # If needed
# Contact PyPI support to yank: https://pypi.org/help/
```

### 2. Delete Git Tag

```bash
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag
git push origin :refs/tags/vX.Y.Z
```

### 3. Revert Commit

```bash
# Revert the release commit
git revert <commit-hash>
git push origin main
```

### 4. Communicate

- [ ] Post issue on GitHub explaining the problem
- [ ] Update release notes with warning
- [ ] Notify users through available channels
- [ ] Provide workaround or rollback instructions

## Hotfix Procedure

For critical bugs in production:

1. Create hotfix branch from release tag:
   ```bash
   git checkout -b hotfix/X.Y.Z+1 vX.Y.Z
   ```

2. Fix the bug and commit

3. Bump patch version:
   ```bash
   python scripts/bump_version.py patch
   ```

4. Follow release process (steps 3-10)

5. Merge hotfix back to main:
   ```bash
   git checkout main
   git merge hotfix/X.Y.Z+1
   git push origin main
   ```

## Release Schedule

- **Patch releases**: As needed for critical bugs
- **Minor releases**: Monthly or when significant features are ready
- **Major releases**: Quarterly or when breaking changes are necessary

## Version Support

- **Current major version**: Full support
- **Previous major version**: Security fixes for 6 months
- **Older versions**: No support (upgrade recommended)

## Automation

The `scripts/release.sh` script automates most of this process:

```bash
./scripts/release.sh
```

It will:
1. Check pre-conditions (clean repo, tests pass)
2. Prompt for version bump type
3. Update version numbers
4. Generate changelog
5. Run tests and linting
6. Build package
7. Create git tag
8. Push to remote
9. Optionally publish to PyPI

## Troubleshooting

### Build Fails

- Check Python version compatibility
- Verify all dependencies are installed
- Review build logs for specific errors

### Tests Fail

- Don't release with failing tests
- Fix issues or revert problematic changes
- Re-run full test suite

### PyPI Upload Fails

- Verify credentials in `~/.pypirc`
- Check if version already exists
- Ensure package name is available
- Review PyPI upload logs

### Tag Already Exists

```bash
# Delete and recreate tag
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
git tag -a vX.Y.Z -m "Release version X.Y.Z"
git push origin vX.Y.Z
```

## Resources

- [Semantic Versioning](https://semver.org/)
- [Python Packaging Guide](https://packaging.python.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [PyPI Publishing](https://packaging.python.org/tutorials/packaging-projects/)

## Contact

For release-related questions:
- Open an issue on GitHub
- Contact maintainers
- Check documentation

---

**Last Updated**: 2026-04-19
**Maintained By**: AgentMind Core Team
