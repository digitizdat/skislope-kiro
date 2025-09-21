# Comprehensive Testing Troubleshooting Guide

## Overview

This guide provides solutions for issues across all testing layers of the Alpine Ski Simulator: frontend tests, agent tests, integration tests, and deployment validation. Issues are organized by testing layer and include step-by-step solutions.

## Table of Contents

1. [Frontend Testing Issues](#frontend-testing-issues)
2. [Agent Testing Issues](#agent-testing-issues)
3. [Integration Testing Issues](#integration-testing-issues)
4. [Deployment Validation Issues](#deployment-validation-issues)
5. [CI/CD Pipeline Issues](#cicd-pipeline-issues)
6. [Cross-System Issues](#cross-system-issues)
7. [Performance Issues](#performance-issues)
8. [Environment Setup Issues](#environment-setup-issues)

## Frontend Testing Issues

### WebGL Context Problems

**Issue**: Tests fail with WebGL context errors
```
Error: Cannot read property 'createShader' of null
TypeError: gl.clearColor is not a function
```

**Solution**:
```bash
# Install canvas package dependencies
# macOS
brew install pkg-config cairo pango libpng jpeg giflib librsvg

# Ubuntu/Debian
sudo apt-get install build-essential libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev

# Windows (use WSL or pre-built binaries)
npm install --save-dev canvas --canvas_binary_host_mirror=https://github.com/Automattic/node-canvas/releases/download/
```

**Verification**:
```typescript
// Test WebGL context creation
import { initializeTestEnvironment, isWebGLAvailable } from '../test/testSetup';

describe('WebGL Debug', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should have WebGL context', () => {
    console.log('WebGL available:', isWebGLAvailable());
    
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl');
    
    expect(gl).toBeDefined();
    expect(gl.createShader).toBeDefined();
  });
});
```

### IndexedDB and CacheManager Issues

**Issue**: CacheManager tests hang or fail
```
Test timeout: CacheManager.initialize() never resolves
DOMException: The operation failed for reasons unrelated to the database itself
```

**Solution**:
```typescript
// Use mock CacheManager for unit tests
import { createMockCacheManager } from '../test/cacheManagerMocks';

describe('Fast Cache Tests', () => {
  let mockCacheManager;

  beforeEach(async () => {
    mockCacheManager = createMockCacheManager();
    await mockCacheManager.initialize(); // Much faster than real CacheManager
  });

  it('should cache data quickly', async () => {
    const testData = { elevation: [1, 2, 3] };
    await mockCacheManager.cacheTerrainData(testData, mockRun, 'medium');
    
    const cached = await mockCacheManager.getCachedTerrainData('test-run', 'medium');
    expect(cached).toEqual(testData);
  });
});
```

**For Integration Tests**:
```typescript
// Use real CacheManager with timeout
import { withTimeout } from '../test/asyncTestUtils';

describe('CacheManager Integration', () => {
  it('should initialize with timeout', async () => {
    const { cacheManager } = await import('../utils/CacheManager');
    
    await withTimeout(
      cacheManager.initialize(),
      5000,
      'CacheManager initialization timeout'
    );
    
    expect(cacheManager.isInitialized).toBe(true);
  });
});
```

### Browser API Mock Issues

**Issue**: fetch, localStorage, or other browser APIs not available
```
TypeError: fetch is not a function
ReferenceError: localStorage is not defined
```

**Solution - Unit Tests (jsdom environment)**:
```typescript
// Ensure test environment is initialized
import { initializeTestEnvironment } from '../test/testSetup';

describe('Browser API Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment(); // This installs all browser API mocks
  });

  it('should have browser APIs available', () => {
    expect(typeof fetch).toBe('function');
    expect(typeof localStorage.setItem).toBe('function');
    expect(typeof AudioContext).toBe('function');
  });
});
```

**Solution - Integration Tests (Node environment)**:
```typescript
// For Node environment, provide fetch polyfill
if (typeof globalThis.fetch === 'undefined') {
  try {
    const { fetch } = await import('undici');
    globalThis.fetch = fetch as any;
  } catch {
    const fetch = (await import('node-fetch')).default;
    globalThis.fetch = fetch as any;
  }
}

describe('Integration Tests', () => {
  it('should make real network calls', async () => {
    // This will make actual HTTP requests to localhost
    const response = await fetch('http://localhost:8001/health');
    expect(response.ok).toBe(true);
  });
});
```

**Manual Mock Setup** (if automatic setup fails):
```typescript
import { createBrowserAPIMocks } from '../test/browserAPIMocks';

// Install mocks manually
const mocks = createBrowserAPIMocks();
global.fetch = mocks.fetch;
global.localStorage = mocks.localStorage;
```

## Agent Testing Issues

### Agent Import Failures

**Issue**: Cannot import agent modules
```
ImportError: No module named 'agents.hill_metrics.server'
ModuleNotFoundError: No module named 'shapely'
```

**Solution**:
```bash
# Check Python environment
uv run python -c "import sys; print(sys.path)"

# Ensure all dependencies are installed
uv sync

# Test individual imports
uv run python -c "import agents.hill_metrics.server"
uv run python -c "import agents.weather.server"
uv run python -c "import agents.equipment.server"

# Check for missing system dependencies
uv run python -c "import rasterio, shapely, geopandas"
```

**Fix Missing Dependencies**:
```bash
# Add missing dependencies
uv add shapely rasterio geopandas

# For system-level dependencies (Ubuntu/Debian)
sudo apt-get install gdal-bin libgdal-dev

# For macOS
brew install gdal
```

### JSON-RPC Method Errors

**Issue**: Method not found errors in agent tests
```
JSON-RPC error: Method 'getHillMetrics' not found
```

**Solution**:
```python
# Check available methods
from agents.hill_metrics.server import HillMetricsAgent

agent = HillMetricsAgent()
print("Available methods:", [method for method in dir(agent) if not method.startswith('_')])

# Verify method registration
from agents.shared.jsonrpc import JSONRPCServer
server = JSONRPCServer()
# Check if methods are properly registered
```

**API Contract Validation**:
```bash
# Run API contract validator
uv run python agents/tests/integration/api_contract_validator.py

# Check for method name mismatches
uv run python scripts/test_integration.py --api-contracts-only
```

### Agent Server Startup Issues

**Issue**: Agents fail to start during tests
```
ConnectionError: Cannot connect to agent at http://localhost:8001
Agent startup timeout after 30 seconds
```

**Solution**:
```bash
# Check port availability
lsof -i :8001-8003

# Kill any existing processes
pkill -f "python.*agents"

# Start agents manually for debugging
uv run python scripts/start_agents.py

# Check agent health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

**Debug Agent Startup**:
```python
# Test individual agent startup
import asyncio
from agents.hill_metrics.server import HillMetricsAgent

async def test_agent():
    agent = HillMetricsAgent()
    await agent.start()
    print("Agent started successfully")

asyncio.run(test_agent())
```

## Integration Testing Issues

### Environment Configuration Issues

**Issue**: Integration tests fail with mocked fetch preventing real network calls
```
Integration tests cannot connect to agent servers
Fetch calls are being mocked instead of making real requests
Network requests return mock data instead of agent responses
```

**Root Cause**: Integration tests were originally configured to use jsdom environment with mocked browser APIs, but this prevented real network calls needed for agent communication.

**Solution**: Use separate Vitest configuration for integration tests with Node environment:

**File: `vitest.integration.config.ts`**:
```typescript
export default defineConfig({
  test: {
    // Use Node environment for integration tests to support real network calls
    environment: 'node',
    
    // Only run integration test files
    include: [
      'src/**/*.integration.test.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
    ],
    
    // Environment variables
    env: {
      NODE_ENV: 'test',
      INTEGRATION_TEST: 'true',
    }
  }
});
```

**File: `package.json`**:
```json
{
  "scripts": {
    "test": "vitest --run --reporter=verbose",
    "test:integration": "vitest run --config=vitest.integration.config.ts --reporter=verbose"
  }
}
```

**Fetch Polyfill for Node Environment**:
```typescript
// Add to integration test files
if (typeof globalThis.fetch === 'undefined') {
  try {
    const { fetch } = await import('undici');
    globalThis.fetch = fetch as any;
  } catch {
    const fetch = (await import('node-fetch')).default;
    globalThis.fetch = fetch as any;
  }
}
```

**Prevention**: 
- Use `*.integration.test.ts` naming for integration tests
- Use `*.test.ts` naming for unit tests
- Keep environments separate: jsdom for units, Node for integration

### API Contract Validation Failures

**Issue**: Frontend-backend method mismatches
```
Contract validation failed: Method 'getHillMetrics' expected but 'get_hill_metrics' found
Parameter mismatch in weather agent methods
```

**Solution**:
```bash
# Run comprehensive contract validation
uv run python agents/tests/integration/api_contract_validator.py --verbose

# Check specific agent contracts
uv run python -c "
from agents.tests.integration.api_contract_validator import APIContractValidator
validator = APIContractValidator()
methods = validator.discover_agent_methods_static('agents/hill_metrics/server.py')
print('Hill Metrics Methods:', methods)
"
```

**Fix Method Name Mismatches**:
1. Update frontend AgentClient method names to match backend
2. Or update backend method names to match frontend expectations
3. Ensure consistent naming convention across all agents

### Cross-System Communication Issues

**Issue**: CORS errors or network communication failures
```
CORS policy error: Access blocked by CORS policy
Network timeout during integration tests
```

**Solution**:
```bash
# Test CORS configuration
uv run python agents/tests/integration/communication_validator.py --cors-only

# Check network connectivity
curl -H "Origin: http://localhost:3000" http://localhost:8001/health

# Test JSON-RPC communication
curl -X POST http://localhost:8001/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"getHillMetrics","params":{},"id":"test"}'
```

**Debug Network Issues**:
```python
# Test network communication manually
import httpx
import asyncio

async def test_communication():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8001/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

asyncio.run(test_communication())
```

### Environment Validation Issues

**Issue**: Environment inconsistencies detected
```
Package manager conflict: Both pip and uv packages detected
SSL certificate validation failed
Import dependency verification failed
```

**Solution**:
```bash
# Check package manager consistency
uv run python agents/tests/integration/environment_validator.py --packages-only

# Fix mixed package managers
pip list | grep -E "(fastapi|uvicorn|httpx)" # Should be empty in uv project
pip uninstall -y fastapi uvicorn httpx # Remove pip-installed packages
uv sync # Reinstall with uv

# Check SSL configuration
uv run python -c "
import ssl
import httpx
print('SSL context:', ssl.create_default_context())
"
```

## Deployment Validation Issues

### Smoke Test Failures

**Issue**: Deployment smoke tests fail
```
Environment setup validation failed
Frontend build verification failed
Production readiness check failed
```

**Solution**:
```bash
# Run smoke tests with verbose output
uv run python scripts/deployment_smoke_tests.py --verbose

# Check specific smoke test categories
uv run python scripts/deployment_smoke_tests.py --test-category environment
uv run python scripts/deployment_smoke_tests.py --test-category build
```

**Debug Build Issues**:
```bash
# Test frontend build manually
npm run build

# Check build artifacts
ls -la dist/
du -sh dist/

# Test production imports
uv run python -c "
from agents.hill_metrics.server import HillMetricsAgent
from agents.shared.jsonrpc import JSONRPCServer
print('Production imports successful')
"
```

### Configuration Validation Issues

**Issue**: Invalid configuration files detected
```
Invalid package.json structure
Missing required pyproject.toml sections
YAML syntax error in logging.yaml
```

**Solution**:
```bash
# Validate configuration files manually
node -e "console.log(JSON.parse(require('fs').readFileSync('package.json')))"

# Check pyproject.toml
uv run python -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
    print('Project name:', data['project']['name'])
"

# Validate YAML files
uv run python -c "
import yaml
with open('logging.yaml') as f:
    data = yaml.safe_load(f)
    print('Logging config valid')
"
```

## CI/CD Pipeline Issues

### GitHub Actions Failures

**Issue**: Tests pass locally but fail in CI
```
Tests timeout in GitHub Actions
Different behavior between local and CI environments
Dependency installation failures in CI
```

**Solution**:
```yaml
# Add debug information to GitHub Actions
- name: Debug Environment
  run: |
    echo "Node version: $(node --version)"
    echo "Python version: $(python --version)"
    echo "uv version: $(uv --version)"
    echo "Platform: $(uname -a)"
    echo "Available memory: $(free -h)"
```

**Fix CI-Specific Issues**:
```yaml
# Increase timeouts for CI
- name: Run tests with CI timeouts
  run: npm test
  env:
    CI: true
    VITEST_TIMEOUT: 15000
    VITEST_TEST_TIMEOUT: 10000

# Use CI-specific test configuration
- name: Run integration tests
  run: uv run python scripts/test_integration.py --ci-mode
```

### Pre-commit Hook Failures

**Issue**: Lefthook pre-commit hooks fail
```
Pre-commit hook failed: dependency-check
API contract validation failed in pre-commit
```

**Solution**:
```bash
# Run pre-commit hooks manually
uv run npx lefthook run pre-commit

# Debug specific hooks
uv run npx lefthook run pre-commit dependency-check
uv run npx lefthook run pre-commit api-contract-check

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

**Fix Hook Issues**:
```bash
# Update Lefthook configuration
npx lefthook install

# Check hook scripts
cat .lefthook.yml

# Verify hook dependencies
which uv
which npm
```

## Cross-System Issues

### API Contract Mismatches

**Issue**: Frontend and backend API contracts don't match
```
Method signature mismatch between frontend AgentClient and backend agents
Parameter structure differences
Response format inconsistencies
```

**Solution**:
```bash
# Run comprehensive contract validation
uv run python agents/tests/integration/api_contract_validator.py --detailed

# Generate contract comparison report
uv run python scripts/generate_api_contracts.py --compare
```

**Fix Contract Issues**:
1. **Update Frontend**: Modify AgentClient methods to match backend
2. **Update Backend**: Modify agent methods to match frontend expectations
3. **Add Compatibility Layer**: Create adapters for incompatible changes

### Data Format Inconsistencies

**Issue**: Data format mismatches between systems
```
Terrain data format mismatch
Weather data structure inconsistency
Equipment status format differences
```

**Solution**:
```python
# Test data format compatibility
from agents.tests.integration.mock_data_generator import MockDataGenerator

generator = MockDataGenerator()

# Generate test data and validate formats
terrain_data = generator.generate_terrain_data()
weather_data = generator.generate_weather_data()
equipment_data = generator.generate_equipment_data()

# Validate against expected schemas
```

## Performance Issues

### Slow Test Execution

**Issue**: Tests take too long to complete
```
Frontend tests timeout
Integration tests exceed time limits
CI/CD pipeline takes too long
```

**Solution**:
```bash
# Profile test execution
npm test -- --reporter=verbose --run

# Use parallel execution
npm test -- --pool=threads --poolOptions.threads.singleThread=false

# Run selective tests
npm test -- src/components/TerrainViewer.test.ts
uv run pytest agents/tests/test_hill_metrics.py -v
```

**Optimize Test Performance**:
```typescript
// Use mocks for expensive operations
import { createMockCacheManager } from '../test/cacheManagerMocks';

describe('Fast Tests', () => {
  beforeEach(async () => {
    // Use mock instead of real CacheManager
    const mockCache = createMockCacheManager();
    await mockCache.initialize(); // Much faster
  });
});
```

### Memory Usage Issues

**Issue**: Tests consume too much memory
```
Out of memory errors during test execution
Memory leaks in test environment
```

**Solution**:
```typescript
// Proper cleanup in tests
describe('Memory-Conscious Tests', () => {
  afterEach(async () => {
    // Clean up resources
    await resetTestEnvironment();
    
    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }
  });
});
```

**Monitor Memory Usage**:
```bash
# Monitor memory during tests
npm test -- --logHeapUsage

# Check for memory leaks
node --expose-gc --inspect npm test
```

## Environment Setup Issues

### Package Manager Conflicts

**Issue**: Mixed package manager usage
```
Both pip and uv packages detected
Dependency conflicts between package managers
```

**Solution**:
```bash
# Clean up mixed package managers
pip list | grep -E "(fastapi|uvicorn|httpx|structlog)"
pip uninstall -y $(pip list | grep -E "(fastapi|uvicorn|httpx|structlog)" | cut -d' ' -f1)

# Reinstall with uv
uv sync

# Verify clean environment
pip list # Should be minimal
uv pip list # Should show project dependencies
```

### SSL/TLS Issues

**Issue**: SSL certificate validation failures
```
SSL certificate verification failed
HTTPS requests fail in test environment
```

**Solution**:
```bash
# Check SSL configuration
uv run python -c "
import ssl
import certifi
print('SSL context:', ssl.create_default_context())
print('CA bundle:', certifi.where())
"

# Test HTTPS connectivity
uv run python -c "
import httpx
response = httpx.get('https://httpbin.org/get')
print('HTTPS test:', response.status_code)
"
```

### System Dependencies

**Issue**: Missing system-level dependencies
```
Cannot import rasterio, shapely, or other geospatial libraries
Canvas package compilation failures
```

**Solution**:
```bash
# Install system dependencies
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install gdal-bin libgdal-dev libproj-dev libgeos-dev
sudo apt-get install build-essential libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev

# macOS
brew install gdal proj geos
brew install pkg-config cairo pango libpng jpeg giflib librsvg

# Verify installations
gdal-config --version
pkg-config --version
```

## Debug Information Collection

When reporting issues, collect this comprehensive debug information:

```bash
# System information
echo "=== System Information ==="
uname -a
node --version
npm --version
uv --version
python --version

# Environment status
echo "=== Environment Status ==="
uv run python scripts/validate-test-env.js

# Test environment diagnostics
echo "=== Test Environment ==="
npm test -- --reporter=verbose --run src/test/testSetup.test.ts

# Agent status
echo "=== Agent Status ==="
uv run python scripts/test_agents.py

# Integration test diagnostics
echo "=== Integration Tests ==="
uv run python agents/tests/integration/dashboard.py --diagnostics

# Package information
echo "=== Package Information ==="
npm list --depth=0
uv pip list

# Build status
echo "=== Build Status ==="
npm run build
```

## Getting Help

### Escalation Path

1. **Check Documentation**: Review relevant testing guides
2. **Run Diagnostics**: Collect debug information using scripts above
3. **Search Issues**: Check existing GitHub issues for similar problems
4. **Create Issue**: Report with complete debug information
5. **Contact Team**: Reach out to development team with details

### Useful Commands for Debugging

```bash
# Quick health check
npm test -- --run src/test/testSetup.test.ts
uv run python scripts/test_agents.py
uv run python scripts/deployment_smoke_tests.py

# Detailed diagnostics
DEBUG=true npm test
uv run pytest agents/tests/ -v -s
uv run python scripts/test_integration.py --verbose

# Environment validation
uv run python agents/tests/integration/environment_validator.py
npm run build
```

This comprehensive troubleshooting guide should help resolve issues across all testing layers of the Alpine Ski Simulator. For specific testing scenarios, refer to the individual testing guides for more detailed information.