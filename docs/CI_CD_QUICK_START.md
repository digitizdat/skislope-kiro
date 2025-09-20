# CI/CD Integration Quick Start

This guide helps you quickly set up and use the CI/CD integration for the Alpine Ski Simulator project.

## Quick Setup

### 1. Run the Setup Script

```bash
# Make the setup script executable and run it
chmod +x scripts/setup_ci_cd.sh
./scripts/setup_ci_cd.sh
```

This script will:
- Create necessary directories
- Install Lefthook for git hooks
- Set up pre-commit and pre-push hooks
- Verify your environment
- Run initial smoke tests

### 2. Install Git Hooks

```bash
# Install hooks (done automatically by setup script)
npm run hooks:install

# Or manually with Lefthook
lefthook install
```

### 3. Verify Setup

```bash
# Test the hooks
git add .
git commit -m "test: verify CI/CD setup"

# This should trigger pre-commit hooks automatically
```

## What's Included

### GitHub Actions Workflow
- **File**: `.github/workflows/integration-tests.yml`
- **Triggers**: Push to main/develop, PRs, daily at 2 AM UTC
- **Features**: 
  - Matrix testing (Python 3.11/3.12, Node 18/20)
  - Full integration test suite
  - Artifact collection
  - Test result reporting

### Pre-commit Hooks
- **File**: `lefthook.yml`
- **Features**:
  - Python code formatting and linting
  - TypeScript type checking
  - Import validation
  - API contract checking
  - Dependency consistency checks

### Deployment Smoke Tests
- **File**: `scripts/deployment_smoke_tests.py`
- **Purpose**: Lightweight production readiness validation
- **Output**: JSON, HTML, and JUnit XML reports

### Test Artifact Collection
- **File**: `scripts/collect_test_artifacts.py`
- **Purpose**: Collect and organize test results, logs, and diagnostics
- **Output**: Organized archives with metadata

## Daily Workflow

### Development
1. **Make changes** to your code
2. **Stage files**: `git add .`
3. **Commit**: `git commit -m "feat: your changes"`
   - Pre-commit hooks run automatically
   - Fast feedback on code quality and imports
4. **Push**: `git push`
   - Pre-push hooks run comprehensive tests
   - GitHub Actions workflow triggers

### Before Deployment
1. **Run smoke tests**: `npm run ci:smoke`
2. **Review results** in `deployment-test-results/`
3. **Fix any issues** before deploying

### Debugging Test Failures
1. **Check logs**: Look in `logs/` directory
2. **Collect artifacts**: `npm run ci:artifacts`
3. **Review detailed reports** in generated archives

## Available Commands

### NPM Scripts
```bash
npm run hooks:install      # Install git hooks
npm run hooks:uninstall    # Remove git hooks
npm run ci:integration     # Run integration tests
npm run ci:smoke          # Run deployment smoke tests
npm run ci:artifacts      # Collect test artifacts
```

### Direct Script Usage
```bash
# Deployment smoke tests
uv run python scripts/deployment_smoke_tests.py --verbose

# Artifact collection
uv run python scripts/collect_test_artifacts.py --test-run-id "local-test"

# Integration tests
uv run python scripts/test_integration.py --ci-mode
```

### Lefthook Commands
```bash
npx lefthook run pre-commit    # Run pre-commit hooks manually
npx lefthook run pre-push      # Run pre-push hooks manually
npx lefthook install           # Install hooks
npx lefthook uninstall         # Remove hooks
```

## Understanding Test Results

### Pre-commit Hook Results
- ✅ **Green checkmarks**: All checks passed
- ❌ **Red X marks**: Issues found, commit blocked
- 🔧 **Auto-fixes**: Some issues fixed automatically

### GitHub Actions Results
- **Status badges**: Show overall workflow status
- **Detailed logs**: Available in Actions tab
- **Artifacts**: Downloadable test results and logs
- **Test reports**: Visual test result summaries

### Smoke Test Results
- **JSON Report**: Machine-readable results
- **HTML Report**: Visual dashboard
- **JUnit XML**: CI integration format

## Troubleshooting

### Common Issues

#### "uv not found"
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart terminal
```

#### "lefthook not found"
```bash
# Install Lefthook as dev dependency
npm install lefthook --save-dev
```

#### "Import errors in hooks"
```bash
# Sync Python dependencies
uv sync

# Verify imports
uv run python -c "import agents.hill_metrics.server"
```

#### "Frontend build fails"
```bash
# Install Node dependencies
npm install

# Clear cache
npm run cache:clear
```

#### "Hooks not running"
```bash
# Reinstall hooks
npx lefthook uninstall
npx lefthook install

# Check hook status
npx lefthook version
```

### Getting Help

1. **Check the logs**: Most issues are logged with helpful error messages
2. **Run setup script again**: `./scripts/setup_ci_cd.sh`
3. **Verify environment**: Ensure uv and npm are working
4. **Review documentation**: See `docs/CI_CD_INTEGRATION.md` for detailed info

## Customization

### Modifying Hooks
Edit `lefthook.yml` to customize:
- Which files trigger hooks
- What commands run
- Parallel vs sequential execution
- Skip conditions

### Adjusting Workflows
Edit `.github/workflows/integration-tests.yml` to:
- Change trigger conditions
- Modify test matrix
- Add new test steps
- Adjust timeouts

### Custom Smoke Tests
Extend `scripts/deployment_smoke_tests.py` to add:
- New validation checks
- Custom test scenarios
- Additional output formats
- Integration with monitoring systems

## Best Practices

### Commit Messages
Use [Conventional Commits](https://www.conventionalcommits.org/):
```bash
feat(agents): add new health check endpoint
fix(frontend): resolve cache invalidation issue
docs(api): update integration guide
test(ci): add deployment smoke tests
```

### Development Flow
1. **Small, frequent commits** with descriptive messages
2. **Run tests locally** before pushing
3. **Review hook output** and fix issues promptly
4. **Monitor CI results** and address failures quickly

### Performance Tips
1. **Use selective testing** during development
2. **Cache dependencies** in CI
3. **Run hooks in parallel** where possible
4. **Clean up old artifacts** regularly

## Next Steps

After setup:
1. **Commit your changes** to trigger the first workflow run
2. **Review the GitHub Actions results** 
3. **Customize hooks and workflows** for your team's needs
4. **Set up monitoring and alerting** for production deployments
5. **Train your team** on the new development workflow

For detailed information, see the full [CI/CD Integration Guide](CI_CD_INTEGRATION.md).