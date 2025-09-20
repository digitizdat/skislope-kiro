# CI/CD Integration Guide

This document provides comprehensive guidance for integrating the Alpine Ski Slope Environment Viewer with CI/CD pipelines, focusing on automated testing, deployment validation, and artifact management.

## Overview

The CI/CD integration provides:
- Automated integration testing on every push and pull request
- Pre-commit hooks for fast feedback during development
- Deployment validation smoke tests
- Comprehensive test artifact collection and storage
- Multi-environment testing (Python 3.11/3.12, Node 18/20)

## GitHub Actions Workflow

### Integration Tests Workflow

The main workflow (`.github/workflows/integration-tests.yml`) runs on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches  
- Daily scheduled runs at 2 AM UTC

#### Workflow Steps

1. **Environment Setup**
   - Sets up Python and Node.js in matrix combinations
   - Installs `uv` for Python dependency management
   - Caches dependencies for faster builds

2. **Dependency Installation**
   - Installs Python dependencies via `uv sync`
   - Installs Node dependencies via `npm ci`

3. **Import Verification**
   - Tests critical Python module imports
   - Catches missing dependencies early

4. **Unit Testing**
   - Runs Python unit tests with pytest
   - Runs frontend unit tests with npm
   - Generates JUnit XML reports

5. **Build Verification**
   - Builds frontend production assets
   - Ensures TypeScript compilation succeeds

6. **Integration Testing**
   - Starts agent servers in background
   - Runs comprehensive integration test suite
   - Collects detailed test results and diagnostics

7. **Artifact Collection**
   - Uploads test results for analysis
   - Stores logs and diagnostics for failed tests
   - Publishes test reports with visual indicators

### Deployment Validation

The deployment validation job runs only on `main` branch pushes and includes:
- Production build verification
- Deployment smoke tests
- Production readiness checks

## Pre-commit Hooks (Lefthook)

### Installation

```bash
# Install Lefthook as dev dependency
npm install lefthook --save-dev

# Install hooks in repository
npx lefthook install
```

### Hook Categories

#### Pre-commit Hooks
- **Code Quality**: Python formatting (ruff), linting, TypeScript checks
- **Import Validation**: Lightweight contract validation without starting agents
- **API Contract Check**: Static analysis of agent method signatures
- **Dependency Check**: Validates package manager consistency
- **Quick Smoke Test**: Fast validation of critical functionality

#### Pre-push Hooks
- **Comprehensive Testing**: Full unit test suite for backend and frontend
- **Integration Test Validation**: Environment validation without full agent startup

#### Commit Message Validation
- **Conventional Commits**: Enforces conventional commit message format
- **Format Examples**:
  ```
  feat(agents): add health check endpoint
  fix(frontend): resolve cache invalidation issue
  docs(api): update agent communication protocol
  ```

### Hook Configuration

The `lefthook.yml` file defines all hooks with parallel execution for performance:

```yaml
pre-commit:
  parallel: true
  commands:
    python-format:
      glob: "*.py"
      run: uv run ruff format --check {staged_files}
    
    api-contract-check:
      run: |
        # Lightweight contract validation
        uv run python -c "
        from agents.tests.integration.api_contract_validator import APIContractValidator
        validator = APIContractValidator()
        # Static validation without starting agents
        "
```

## Deployment Smoke Tests

### Purpose

Deployment smoke tests (`scripts/deployment_smoke_tests.py`) provide lightweight validation that a deployment is production-ready without requiring full integration test infrastructure.

### Test Categories

1. **Environment Setup**
   - Python environment validation
   - Package consistency checking
   - SSL configuration verification

2. **Import Validation**
   - Critical module import testing
   - Dependency availability verification

3. **Build Verification**
   - Frontend build success
   - Essential artifact presence

4. **Configuration Validation**
   - Required configuration files
   - Configuration format validation

5. **Production Readiness**
   - Production-specific requirements
   - Security considerations
   - Performance checks

### Usage

```bash
# Run smoke tests locally
uv run python scripts/deployment_smoke_tests.py

# Run with custom output directory
uv run python scripts/deployment_smoke_tests.py --output-dir custom-results

# Verbose output
uv run python scripts/deployment_smoke_tests.py --verbose
```

### Output Formats

- **JSON Report**: Machine-readable test results
- **HTML Report**: Human-readable visual report
- **JUnit XML**: CI/CD integration format
- **Logs**: Detailed execution logs

## Test Artifact Collection

### Automatic Collection

The artifact collector (`scripts/collect_test_artifacts.py`) automatically gathers:

- **Test Results**: JUnit XML, JSON reports, HTML reports
- **Log Files**: Agent logs, performance logs, error logs
- **Diagnostic Files**: Debug information, system state
- **Build Artifacts**: Build manifests, dependency locks
- **Coverage Reports**: Code coverage data
- **Performance Data**: Benchmarks, profiling results

### Usage

```bash
# Collect all artifacts
uv run python scripts/collect_test_artifacts.py

# Custom test run ID
uv run python scripts/collect_test_artifacts.py --test-run-id "pr-123"

# Custom output directory
uv run python scripts/collect_test_artifacts.py --output-dir artifacts

# Cleanup old artifacts (30+ days)
uv run python scripts/collect_test_artifacts.py --cleanup-only
```

### Artifact Organization

```
test-artifacts/
├── test_run_1234567890/
│   ├── collection_metadata.json
│   ├── report/
│   │   ├── test_results.xml
│   │   ├── coverage.json
│   │   └── smoke_test_report.html
│   ├── log/
│   │   ├── agents.log
│   │   ├── integration_tests.log
│   │   └── performance.log
│   ├── diagnostic/
│   │   ├── diagnostics_20241219.json
│   │   └── error_context.json
│   └── data/
│       ├── package-lock.json
│       └── uv.lock
└── test_run_1234567890.zip
```

## Environment Configuration

### Required Environment Variables

#### CI/CD Pipeline
```bash
CI=true                           # Enables CI mode
INTEGRATION_TEST_TIMEOUT=300      # Test timeout in seconds
NODE_ENV=test                     # Node environment
```

#### Optional Configuration
```bash
GITHUB_ACTIONS=true               # GitHub Actions specific
GITHUB_RUN_ID=123456             # Run identifier
GITHUB_SHA=abc123                # Commit SHA
```

### Local Development

```bash
# Setup development environment
uv sync
npm install
lefthook install

# Run pre-commit checks manually
npx lefthook run pre-commit

# Run integration tests locally
uv run python scripts/test_integration.py
```

## Troubleshooting

### Common Issues

#### 1. Import Errors in CI
```bash
# Symptom: Module import failures in CI but not locally
# Solution: Verify uv sync completed successfully
uv sync --verbose
```

#### 2. Agent Startup Failures
```bash
# Symptom: Agents fail to start in CI environment
# Solution: Check port availability and increase startup timeout
curl -f http://localhost:8001/health || echo "Agent not ready"
```

#### 3. Test Timeouts
```bash
# Symptom: Tests timeout in CI but pass locally
# Solution: Increase timeout values for CI environment
export INTEGRATION_TEST_TIMEOUT=600
```

#### 4. Artifact Collection Failures
```bash
# Symptom: Missing test artifacts in CI
# Solution: Ensure artifact paths exist before collection
mkdir -p test-results logs temp
```

### Debug Commands

```bash
# Check environment consistency
uv run python -c "import sys; print(sys.path)"
npm list --depth=0

# Verify agent imports
uv run python -c "import agents.hill_metrics.server"
uv run python -c "import agents.weather.server"
uv run python -c "import agents.equipment.server"

# Test artifact collection
uv run python scripts/collect_test_artifacts.py --test-run-id debug

# Run smoke tests with verbose output
uv run python scripts/deployment_smoke_tests.py --verbose
```

## Performance Optimization

### CI/CD Pipeline Optimization

1. **Dependency Caching**
   - Cache Node modules and Python packages
   - Use lock files for consistent installs

2. **Parallel Execution**
   - Run tests in parallel where possible
   - Use matrix builds for multiple environments

3. **Selective Testing**
   - Run only affected tests for pull requests
   - Use pre-commit hooks for fast feedback

4. **Artifact Management**
   - Compress artifacts for storage efficiency
   - Clean up old artifacts automatically

### Local Development Optimization

1. **Pre-commit Hooks**
   - Fast feedback without full test suite
   - Parallel execution of checks

2. **Selective Test Execution**
   - Run specific test categories
   - Skip integration tests during development

3. **Cache Management**
   - Reuse test fixtures and mock data
   - Cache agent startup for repeated runs

## Security Considerations

### Secrets Management
- Never commit API keys or credentials
- Use environment variables for sensitive data
- Rotate test credentials regularly

### Test Data Security
- Use synthetic data for testing
- Avoid real user data in test scenarios
- Sanitize logs and artifacts

### Access Control
- Restrict access to test artifacts
- Use secure artifact storage
- Implement audit logging

## Monitoring and Alerting

### Test Result Monitoring
- Track test success rates over time
- Monitor test execution duration
- Alert on test failure patterns

### Performance Monitoring
- Track build and test times
- Monitor resource usage in CI
- Alert on performance regressions

### Integration Health
- Monitor agent health in CI
- Track integration test reliability
- Alert on infrastructure issues

## Best Practices

### Development Workflow
1. Use pre-commit hooks for fast feedback
2. Run integration tests before pushing
3. Follow conventional commit messages
4. Keep test artifacts for debugging

### CI/CD Pipeline
1. Use matrix builds for compatibility testing
2. Implement proper timeout handling
3. Collect comprehensive artifacts
4. Provide clear failure diagnostics

### Maintenance
1. Regularly update dependencies
2. Clean up old test artifacts
3. Monitor and optimize test performance
4. Review and update test coverage

## Migration Guide

### From Manual Testing
1. Install Lefthook and configure hooks
2. Update development workflow documentation
3. Train team on new processes
4. Gradually increase automation coverage

### From Other CI Systems
1. Adapt workflow files to target platform
2. Update environment variable names
3. Modify artifact collection paths
4. Test thoroughly in new environment

## Support and Resources

### Documentation
- [Integration Testing Infrastructure Spec](.kiro/specs/integration-testing-infrastructure/)
- [Development Workflow Guidelines](.kiro/steering/development-workflow.md)
- [Technology Stack Guide](.kiro/steering/tech.md)

### Tools and Dependencies
- [Lefthook](https://github.com/evilmartians/lefthook) - Git hooks manager (v1.13.1+)
- [uv](https://github.com/astral-sh/uv) - Python package manager
- [GitHub Actions](https://docs.github.com/en/actions) - CI/CD platform

**Note**: We use the current supported version of Lefthook (`lefthook` npm package, not the deprecated `@arkweid/lefthook`).

### Getting Help
1. Check troubleshooting section above
2. Review test logs and artifacts
3. Run debug commands locally
4. Consult team documentation and practices