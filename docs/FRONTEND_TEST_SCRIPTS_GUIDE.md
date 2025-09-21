# Frontend Test Scripts Guide

This guide explains how to use the comprehensive test scripts provided in the Alpine Ski Simulator frontend test environment.

## Quick Start

```bash
# Validate test environment
npm run test:env:validate

# Run unit tests (jsdom environment)
npm test

# Run integration tests (Node environment)
npm run test:integration

# Run tests with coverage
npm run test:coverage

# Run in CI mode
npm run test:ci
```

## Environment Overview

The Alpine Ski Simulator uses **two different test environments**:

- **Unit Tests**: jsdom environment with mocked browser APIs (`npm test`)
- **Integration Tests**: Node environment for real network calls (`npm run test:integration`)

See [Testing Architecture Changes](./TESTING_ARCHITECTURE_CHANGES.md) for details on this architectural decision.

## Test Script Categories

### Basic Test Execution

| Script | Environment | Description | Use Case |
|--------|-------------|-------------|----------|
| `npm test` | jsdom | Run unit tests with verbose output | Daily development |
| `npm run test:integration` | Node | Run integration tests with real network calls | Cross-system validation |
| `npm run test:watch` | jsdom | Run unit tests in watch mode | Active development |
| `npm run test:ui` | jsdom | Open Vitest UI for interactive testing | Debugging tests |

### Coverage Testing

| Script | Description | Use Case |
|--------|-------------|----------|
| `npm run test:coverage` | Run unit tests with coverage reporting | Code quality checks |
| `npm run test:coverage:watch` | Coverage in watch mode | Development with coverage |
| `npm run test:coverage:threshold` | Enforce coverage thresholds | CI/CD validation |

### Test Categories

| Script | Environment | Description | Use Case |
|--------|-------------|-------------|----------|
| `npm run test:unit` | jsdom | Unit tests only (excludes integration) | Fast feedback loop |
| `npm run test:integration` | Node | Integration tests only | Agent communication testing |
| `npm run test:all` | Both | Run both unit and integration tests | Complete validation |
| `npm run test:performance` | jsdom | Performance tests with heap monitoring | Performance validation |

### Test Filtering

| Script | Description | Example |
|--------|-------------|---------|
| `npm run test:filter` | Filter tests by file pattern | `npm run test:filter -- src/services/` |
| `npm run test:filter:pattern` | Filter by test name pattern | `npm run test:filter:pattern -- "CacheManager"` |
| `npm run test:filter:file` | Run specific test file | `npm run test:filter:file -- AgentClient.test.ts` |

### CI/CD Integration

| Script | Description | Use Case |
|--------|-------------|----------|
| `npm run test:ci` | Full CI test suite with artifacts | Continuous integration |
| `npm run test:ci:unit` | CI unit tests only | Fast CI feedback |
| `npm run test:ci:integration` | CI integration tests | Full CI validation |
| `npm run test:ci:artifacts` | Tests + artifact collection | Deployment preparation |

### Debug and Validation

| Script | Description | Use Case |
|--------|-------------|----------|
| `npm run test:debug` | Tests with debug logging | Troubleshooting |
| `npm run test:debug:watch` | Debug mode in watch | Active debugging |
| `npm run test:setup:validate` | Validate test setup | Environment verification |
| `npm run test:mocks:validate` | Validate mock infrastructure | Mock system verification |

### Test Runner Scripts

| Script | Description | Use Case |
|--------|-------------|----------|
| `npm run test:runner` | Advanced test runner (all tests) | Comprehensive testing |
| `npm run test:runner:unit` | Test runner for unit tests | Focused unit testing |
| `npm run test:runner:integration` | Test runner for integration tests | Integration validation |
| `npm run test:runner:coverage` | Test runner with coverage | Quality assurance |
| `npm run test:runner:performance` | Test runner for performance | Performance validation |
| `npm run test:runner:validate` | Test runner validation mode | Environment check |
| `npm run test:runner:ci` | Test runner in CI mode | CI/CD integration |
| `npm run test:runner:full` | Complete test suite | Full validation |

### Environment Management

| Script | Description | Use Case |
|--------|-------------|----------|
| `npm run test:env:validate` | Validate test environment setup | Pre-test verification |
| `npm run test:env:setup` | Install deps + validate environment | Initial setup |

## Environment Variables

### Core Settings
- `NODE_ENV=test` - Test environment mode
- `VITEST=true` - Vitest execution flag
- `INTEGRATION_TEST=true` - Integration test mode (Node environment)
- `CI=true` - CI environment detection

### Timeout Configuration
- `VITEST_TIMEOUT=10000` - Global timeout (ms)
- `VITEST_TEST_TIMEOUT=5000` - Individual test timeout (ms)
- `VITEST_HOOK_TIMEOUT=10000` - Setup/teardown timeout (ms)

### Coverage Settings
- `VITEST_COVERAGE_THRESHOLD_LINES=80` - Line coverage threshold
- `VITEST_COVERAGE_THRESHOLD_FUNCTIONS=80` - Function coverage threshold
- `VITEST_COVERAGE_THRESHOLD_BRANCHES=80` - Branch coverage threshold
- `VITEST_COVERAGE_THRESHOLD_STATEMENTS=80` - Statement coverage threshold

### CI/CD Settings
- `CI_TIMEOUT_MULTIPLIER=1.5` - Timeout multiplier for CI
- `CI_RETRY_COUNT=2` - Number of retries for flaky tests
- `CI_PARALLEL_WORKERS=2` - Parallel worker count

### Debug Settings
- `DEBUG_TEST_SETUP=true` - Enable test setup debugging
- `DEBUG_MOCK_OPERATIONS=true` - Enable mock operation debugging
- `DEBUG_CACHE_OPERATIONS=true` - Enable cache operation debugging

### Mock Configuration
- `MOCK_WEBGL_CONTEXT=true` - Enable WebGL context mocking
- `MOCK_INDEXEDDB=true` - Enable IndexedDB mocking
- `MOCK_BROWSER_APIS=true` - Enable browser API mocking
- `MOCK_NETWORK_REQUESTS=true` - Enable network request mocking (unit tests only)

## Usage Examples

### Development Workflow

```bash
# Start development with unit test watching
npm run test:watch

# Run specific component tests
npm run test:filter -- src/components/CacheStatus/

# Test integration with agents (requires running agents)
npm run test:integration

# Debug failing tests
DEBUG_TEST_SETUP=true npm run test:debug

# Check coverage for new code
npm run test:coverage
```

### Pre-Commit Validation

```bash
# Validate environment
npm run test:env:validate

# Run unit tests (fast)
npm test

# Run integration tests (requires agents)
npm run test:integration

# Ensure coverage thresholds
npm run test:coverage:threshold
```

### CI/CD Pipeline

```bash
# Environment setup
npm run test:env:setup

# Run CI test suite (unit tests)
npm run test:ci

# Run integration tests in CI
npm run test:ci:integration

# Collect artifacts
npm run test:ci:artifacts

# Full integration
npm run ci:test:full
```

### Performance Testing

```bash
# Run performance tests
npm run test:performance

# Monitor heap usage
npm run test:runner:performance

# Debug performance issues
npm run test:debug -- --logHeapUsage
```

### Integration Testing Workflow

```bash
# Start agent servers (required for integration tests)
uv run python scripts/start_agents.py

# Run integration tests
npm run test:integration

# Debug integration test issues
DEBUG_TEST_SETUP=true npm run test:integration

# Stop agents
pkill -f "python.*agents"
```

### Troubleshooting

```bash
# Validate test setup
npm run test:setup:validate

# Validate mocks
npm run test:mocks:validate

# Full environment validation
npm run test:env:validate

# Debug with verbose output
VERBOSE=true npm run test:runner:validate
```

## Test Environments in Detail

### Unit Test Environment (jsdom)

**Configuration**: `vitest.config.ts`
**Environment**: `jsdom`
**File Pattern**: `*.test.ts`

**Features**:
- Mocked browser APIs (fetch, localStorage, WebGL, etc.)
- React component testing with Testing Library
- Fast execution with isolated test environment
- No external dependencies required

**Example**:
```bash
# Run unit tests
npm test

# Watch mode for development
npm run test:watch
```

### Integration Test Environment (Node)

**Configuration**: `vitest.integration.config.ts`
**Environment**: `node`
**File Pattern**: `*.integration.test.ts`

**Features**:
- Real network calls to localhost agent servers
- Fetch polyfill for Node environment
- API contract validation
- CORS configuration testing

**Requirements**:
- Agent servers must be running on localhost:8001-8003
- Fetch polyfill (undici or node-fetch)

**Example**:
```bash
# Start agents first
uv run python scripts/start_agents.py

# Run integration tests
npm run test:integration
```

## Test Artifacts

### Generated Files
- `test-results/results.json` - Test execution results
- `test-results/report.html` - HTML test report
- `test-results/junit.xml` - JUnit format results (CI)
- `coverage/` - Coverage reports (HTML, LCOV, JSON)
- `test-results/artifact-info.json` - Test execution metadata

### Artifact Collection
Test artifacts are automatically collected after test execution and include:
- Test results and timing information
- Coverage reports with threshold validation
- Environment information and configuration
- Error logs and debugging information
- Performance metrics and heap usage data

## Integration with Pre-Push Hooks

The test scripts integrate with the pre-push hook system:

```yaml
# lefthook.yml
pre-push:
  commands:
    frontend-tests:
      run: npm run test:ci
```

This ensures all frontend unit tests pass before code can be pushed to the repository.

## Best Practices

### Local Development
1. Use `npm run test:watch` for active unit test development
2. Run `npm run test:integration` when testing agent communication
3. Run `npm run test:coverage` before committing
4. Use `npm run test:filter` to focus on specific areas
5. Enable debug mode when troubleshooting

### Environment Selection
1. **Unit Tests** (`npm test`): For component and service testing with mocks
2. **Integration Tests** (`npm run test:integration`): For testing real agent communication
3. **File Naming**: Use `*.test.ts` for units, `*.integration.test.ts` for integration

### CI/CD Integration
1. Always use `npm run test:ci` for unit tests in CI pipelines
2. Use `npm run test:ci:integration` for integration tests (requires agent setup)
3. Collect artifacts with `npm run test:ci:artifacts`
4. Set appropriate timeout multipliers for CI environments
5. Use retry configuration for flaky tests

### Performance Monitoring
1. Run `npm run test:performance` regularly
2. Monitor heap usage with debug scripts
3. Set performance budgets in CI
4. Profile slow tests with detailed logging

### Troubleshooting
1. Start with `npm run test:env:validate`
2. Check mock setup with validation scripts
3. Use debug mode for detailed error information
4. Verify environment variables are set correctly
5. For integration tests, ensure agents are running

## Common Issues and Solutions

### Integration Test Issues

**Issue**: Integration tests fail with "fetch is not a function"
**Solution**: Ensure fetch polyfill is installed in integration test files:
```typescript
if (typeof globalThis.fetch === 'undefined') {
  const { fetch } = await import('undici');
  globalThis.fetch = fetch as any;
}
```

**Issue**: Integration tests can't connect to agents
**Solution**: Start agent servers before running integration tests:
```bash
uv run python scripts/start_agents.py
npm run test:integration
```

**Issue**: Tests use wrong environment
**Solution**: Check file naming convention:
- `*.test.ts` → jsdom environment (unit tests)
- `*.integration.test.ts` → Node environment (integration tests)

### Unit Test Issues

**Issue**: Browser APIs not available in unit tests
**Solution**: Ensure test environment is initialized:
```typescript
import { initializeTestEnvironment } from '../test/testSetup';

beforeEach(async () => {
  await initializeTestEnvironment();
});
```

## Support and Debugging

If tests fail:
1. Check environment validation: `npm run test:env:validate`
2. Verify mock setup: `npm run test:mocks:validate`
3. Run with debug logging: `DEBUG_TEST_SETUP=true npm test`
4. Check test artifacts in `test-results/` directory
5. Review coverage reports for missing test coverage
6. For integration tests, verify agents are running and accessible

For performance issues:
1. Run performance tests: `npm run test:performance`
2. Enable heap monitoring: `npm run test:debug -- --logHeapUsage`
3. Check timeout settings for CI environments
4. Review parallel execution configuration

## Related Documentation

- [Comprehensive Testing Guide](./COMPREHENSIVE_TESTING_GUIDE.md) - Complete testing ecosystem overview
- [Testing Architecture Changes](./TESTING_ARCHITECTURE_CHANGES.md) - Key architectural decisions
- [Frontend Test Environment Guide](./FRONTEND_TEST_ENVIRONMENT.md) - Frontend-specific testing setup
- [Comprehensive Testing Troubleshooting](./COMPREHENSIVE_TESTING_TROUBLESHOOTING.md) - Troubleshooting all test layers