# Frontend Test Environment Troubleshooting Guide

## Overview

This guide provides solutions for common issues encountered when working with the Alpine Ski Simulator frontend test environment. Issues are organized by category with step-by-step solutions and prevention strategies.

## Table of Contents

1. [Environment Setup Issues](#environment-setup-issues)
2. [WebGL Context Problems](#webgl-context-problems)
3. [IndexedDB and CacheManager Issues](#indexeddb-and-cachemanager-issues)
4. [Browser API Mock Problems](#browser-api-mock-problems)
5. [Async Operation Failures](#async-operation-failures)
6. [Test Timeout Issues](#test-timeout-issues)
7. [Coverage and Reporting Problems](#coverage-and-reporting-problems)
8. [CI/CD Integration Issues](#cicd-integration-issues)
9. [Performance Problems](#performance-problems)
10. [Mock Reset and Cleanup Issues](#mock-reset-and-cleanup-issues)

## Environment Setup Issues

### Issue: Tests fail with "Cannot find module" errors

**Symptoms:**
```
Error: Cannot find module 'canvas'
Error: Cannot find module 'fake-indexeddb'
```

**Solution:**
```bash
# Install missing dependencies
npm install --save-dev canvas fake-indexeddb jsdom

# For canvas on different platforms:
# macOS with Homebrew
brew install pkg-config cairo pango libpng jpeg giflib librsvg

# Ubuntu/Debian
sudo apt-get install build-essential libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev

# Windows (use Windows Subsystem for Linux or pre-built binaries)
npm install --save-dev canvas --canvas_binary_host_mirror=https://github.com/Automattic/node-canvas/releases/download/
```

**Prevention:**
- Always run `npm install` after pulling changes
- Check platform-specific requirements for canvas package
- Use Docker for consistent environments across platforms

### Issue: TypeScript compilation errors in test files

**Symptoms:**
```
TS2304: Cannot find name 'describe'
TS2304: Cannot find name 'it'
TS2304: Cannot find name 'expect'
```

**Solution:**
```typescript
// Add to test file
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

// Or ensure vitest.config.ts has globals: true
export default defineConfig({
  test: {
    globals: true, // This enables global test functions
  }
});
```

**Prevention:**
- Use explicit imports for test functions
- Ensure `vitest.config.ts` is properly configured
- Check TypeScript configuration includes test files

### Issue: Module resolution problems

**Symptoms:**
```
Error: Cannot resolve module '@/components/MyComponent'
```

**Solution:**
```typescript
// Check vitest.config.ts has proper alias configuration
export default defineConfig({
  resolve: {
    alias: {
      '@': '/src',
      '@/components': '/src/components',
      '@/services': '/src/services',
      // ... other aliases
    }
  }
});
```

**Prevention:**
- Keep alias configuration consistent between Vite and Vitest configs
- Use relative imports when aliases don't work
- Verify path resolution in IDE settings

## WebGL Context Problems

### Issue: WebGL context creation fails

**Symptoms:**
```
Error: Cannot read property 'createShader' of null
TypeError: gl.clearColor is not a function
```

**Solution:**
```typescript
// Ensure test setup is properly initialized
import { initializeTestEnvironment } from '../test/testSetup';

describe('WebGL Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment(); // This sets up WebGL mocks
  });

  it('should have WebGL context', () => {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl');
    
    expect(gl).toBeDefined();
    expect(gl.createShader).toBeDefined();
  });
});
```

**Debugging:**
```typescript
// Check WebGL availability
import { isWebGLAvailable, getTestEnvironmentState } from '../test/testSetup';

console.log('WebGL available:', isWebGLAvailable());
console.log('Environment state:', getTestEnvironmentState());
```

**Prevention:**
- Always call `initializeTestEnvironment()` in `beforeEach`
- Check that canvas package is properly installed
- Verify WebGL mock setup in test environment

### Issue: Three.js renderer creation fails

**Symptoms:**
```
Error: WebGL context lost
Error: Cannot create WebGLRenderer
```

**Solution:**
```typescript
import * as THREE from 'three';
import { initializeTestEnvironment } from '../test/testSetup';

describe('Three.js Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should create renderer', () => {
    const canvas = document.createElement('canvas');
    const renderer = new THREE.WebGLRenderer({ canvas });
    
    expect(renderer).toBeDefined();
    expect(renderer.domElement).toBe(canvas);
  });
});
```

**Prevention:**
- Ensure WebGL context is available before creating Three.js objects
- Use proper canvas element creation in tests
- Check Three.js version compatibility

### Issue: WebGL operations not mocked properly

**Symptoms:**
```
Error: gl.VERTEX_SHADER is undefined
Error: WebGL method not implemented
```

**Solution:**
```typescript
// Check if specific WebGL constants/methods are available
const gl = canvas.getContext('webgl');
console.log('VERTEX_SHADER constant:', gl.VERTEX_SHADER);
console.log('Available methods:', Object.keys(gl));

// If missing, extend the WebGL mock
import { createWebGLContextMock } from '../test/testSetup';

// The mock should include all necessary constants and methods
```

**Prevention:**
- Keep WebGL mock up to date with Three.js requirements
- Test WebGL operations that your code actually uses
- Report missing WebGL methods to extend the mock

## IndexedDB and CacheManager Issues

### Issue: IndexedDB operations fail

**Symptoms:**
```
Error: indexedDB is not defined
DOMException: The operation failed for reasons unrelated to the database itself
```

**Solution:**
```typescript
// Ensure fake-indexeddb is properly imported
import 'fake-indexeddb/auto';

// Or manually set up IndexedDB
import FDBFactory from 'fake-indexeddb/lib/FDBFactory';
import FDBKeyRange from 'fake-indexeddb/lib/FDBKeyRange';

global.indexedDB = new FDBFactory();
global.IDBKeyRange = FDBKeyRange;
```

**Debugging:**
```typescript
// Check IndexedDB availability
console.log('IndexedDB available:', typeof indexedDB !== 'undefined');
console.log('IndexedDB type:', indexedDB.constructor.name);

// Test basic IndexedDB operation
const request = indexedDB.open('test', 1);
request.onsuccess = () => console.log('IndexedDB working');
request.onerror = (e) => console.error('IndexedDB error:', e);
```

**Prevention:**
- Import `fake-indexeddb/auto` in test setup
- Verify IndexedDB mock is working before running CacheManager tests
- Use proper async/await patterns with IndexedDB operations

### Issue: CacheManager initialization hangs

**Symptoms:**
```
Test timeout: CacheManager.initialize() never resolves
```

**Solution:**
```typescript
// Use timeout wrapper for CacheManager operations
import { withTimeout } from '../test/asyncTestUtils';

describe('CacheManager Tests', () => {
  it('should initialize within timeout', async () => {
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

**Alternative - Use Mock:**
```typescript
// Use mock CacheManager for faster tests
import { createMockCacheManager } from '../test/cacheManagerMocks';

describe('Service Tests', () => {
  let mockCacheManager;

  beforeEach(async () => {
    mockCacheManager = createMockCacheManager();
    await mockCacheManager.initialize();
  });

  // Tests run much faster with mock
});
```

**Prevention:**
- Use mock CacheManager for unit tests
- Only use real CacheManager for integration tests
- Set appropriate timeouts for CacheManager operations

### Issue: Cache operations return unexpected results

**Symptoms:**
```
Expected cached data but got null
Cache hit rate is 0%
```

**Solution:**
```typescript
// Debug cache operations
import { createMockCacheManager } from '../test/cacheManagerMocks';

describe('Cache Debug', () => {
  it('should debug cache operations', async () => {
    const mockCache = createMockCacheManager();
    await mockCache.initialize();
    
    // Set up test data
    const testData = { elevation: [1, 2, 3] };
    const mockRun = { id: 'test-run', skiAreaId: 'test-area' };
    
    // Cache data
    await mockCache.cacheTerrainData(testData, mockRun, 'medium');
    
    // Verify cache state
    console.log('Cache size:', mockCache.getTerrainCacheSize());
    
    // Retrieve data
    const cached = await mockCache.getCachedTerrainData('test-run', 'medium');
    console.log('Retrieved data:', cached);
    
    expect(cached).toEqual(testData);
  });
});
```

**Prevention:**
- Use consistent keys for cache operations
- Verify cache initialization before operations
- Check cache expiration settings in tests

## Browser API Mock Problems

### Issue: localStorage/sessionStorage not working

**Symptoms:**
```
TypeError: Cannot read property 'getItem' of undefined
localStorage.setItem is not a function
```

**Solution:**
```typescript
// Ensure browser API mocks are installed
import { initializeTestEnvironment } from '../test/testSetup';

describe('Storage Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment(); // This installs storage mocks
  });

  it('should have working localStorage', () => {
    expect(typeof localStorage.setItem).toBe('function');
    
    localStorage.setItem('test', 'value');
    expect(localStorage.getItem('test')).toBe('value');
  });
});
```

**Manual Setup:**
```typescript
// If automatic setup fails, manually install mocks
import { createStorageMock } from '../test/browserAPIMocks';

const mockStorage = createStorageMock();
Object.defineProperty(global, 'localStorage', {
  value: mockStorage,
  writable: true
});
```

**Prevention:**
- Always initialize test environment before using browser APIs
- Check that mock installation succeeded
- Use explicit mock creation for specific test needs

### Issue: fetch API not mocked properly

**Symptoms:**
```
TypeError: fetch is not a function
Network request failed in test environment
```

**Solution:**
```typescript
// Verify fetch mock installation
describe('Fetch Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should have mocked fetch', async () => {
    expect(typeof fetch).toBe('function');
    
    const response = await fetch('/test');
    expect(response.ok).toBe(true);
  });
});
```

**Custom Fetch Mock:**
```typescript
// Create custom fetch behavior
import { createFetchMock } from '../test/browserAPIMocks';

const fetchMock = createFetchMock();
fetchMock.mockResolvedValue({
  ok: true,
  status: 200,
  json: () => Promise.resolve({ data: 'test' })
});

global.fetch = fetchMock;
```

**Prevention:**
- Verify fetch mock is installed in test setup
- Use custom fetch mocks for specific test scenarios
- Check network request patterns in your code

### Issue: Web Audio API not available

**Symptoms:**
```
ReferenceError: AudioContext is not defined
TypeError: Cannot read property 'createOscillator' of undefined
```

**Solution:**
```typescript
// Check Web Audio API mock
describe('Audio Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should have AudioContext', () => {
    expect(typeof AudioContext).toBe('function');
    
    const audioContext = new AudioContext();
    expect(audioContext.createOscillator).toBeDefined();
  });
});
```

**Prevention:**
- Ensure Web Audio API mocks are installed
- Check browser compatibility requirements
- Use feature detection in production code

## Async Operation Failures

### Issue: Promises never resolve in tests

**Symptoms:**
```
Test timeout: Promise never resolved
Async operation hanging indefinitely
```

**Solution:**
```typescript
// Use async test utilities
import { waitFor, withTimeout, flushPromises } from '../test/asyncTestUtils';

describe('Async Tests', () => {
  it('should handle async operations', async () => {
    // Flush any pending promises
    await flushPromises();
    
    // Use timeout wrapper
    const result = await withTimeout(
      someAsyncOperation(),
      5000,
      'Operation should complete within 5 seconds'
    );
    
    expect(result).toBeDefined();
  });
});
```

**Debugging:**
```typescript
// Debug async operations
it('should debug async flow', async () => {
  console.log('Starting async operation');
  
  const promise = someAsyncOperation();
  console.log('Promise created');
  
  const result = await promise;
  console.log('Promise resolved:', result);
  
  expect(result).toBeDefined();
});
```

**Prevention:**
- Always use appropriate timeouts for async operations
- Use async test utilities for complex timing scenarios
- Debug async flow with logging when needed

### Issue: Race conditions in tests

**Symptoms:**
```
Test results are inconsistent
Sometimes passes, sometimes fails
```

**Solution:**
```typescript
// Use proper synchronization
import { waitFor, delay } from '../test/asyncTestUtils';

describe('Race Condition Tests', () => {
  it('should handle race conditions', async () => {
    let condition = false;
    
    // Start async operation
    setTimeout(() => {
      condition = true;
    }, 100);
    
    // Wait for condition instead of fixed delay
    await waitFor(() => condition, {
      timeout: 1000,
      interval: 10
    });
    
    expect(condition).toBe(true);
  });
});
```

**Prevention:**
- Use `waitFor` instead of fixed delays
- Synchronize on actual conditions, not time
- Test race conditions explicitly

### Issue: Async cleanup not working

**Symptoms:**
```
Tests interfere with each other
State leaks between tests
```

**Solution:**
```typescript
describe('Cleanup Tests', () => {
  afterEach(async () => {
    // Ensure all async operations complete
    await flushPromises();
    
    // Reset test environment
    await resetTestEnvironment();
    
    // Clear any timers
    vi.clearAllTimers();
  });
});
```

**Prevention:**
- Always clean up async operations in `afterEach`
- Use proper test isolation
- Clear timers and intervals

## Test Timeout Issues

### Issue: Tests timeout in CI but not locally

**Symptoms:**
```
Test timeout in CI: 5000ms exceeded
Tests pass locally but fail in CI
```

**Solution:**
```typescript
// Use environment-aware timeouts
import { getTestTimeout } from '../test/asyncTestUtils';

describe('Timeout Tests', () => {
  it('should use appropriate timeout', async () => {
    const timeout = getTestTimeout(); // Automatically adjusts for CI
    
    const result = await withTimeout(
      slowOperation(),
      timeout,
      'Operation should complete within environment timeout'
    );
    
    expect(result).toBeDefined();
  });
});
```

**Configuration:**
```typescript
// vitest.config.ts - CI timeout multiplier
const isCI = process.env.CI === 'true';
const ciMultiplier = isCI ? 1.5 : 1;

export default defineConfig({
  test: {
    timeout: Math.floor(10000 * ciMultiplier),
    testTimeout: Math.floor(5000 * ciMultiplier),
  }
});
```

**Prevention:**
- Use environment-aware timeout configuration
- Test in CI-like conditions locally
- Monitor test performance over time

### Issue: Individual test timeouts

**Symptoms:**
```
Specific test always times out
Test hangs on specific operation
```

**Solution:**
```typescript
// Increase timeout for specific test
it('should handle slow operation', async () => {
  // This test needs more time
  const result = await withTimeout(
    verySlowOperation(),
    15000, // 15 seconds
    'Slow operation timeout'
  );
  
  expect(result).toBeDefined();
}, 20000); // Vitest timeout: 20 seconds
```

**Debugging:**
```typescript
// Debug what's causing the timeout
it('should debug timeout', async () => {
  console.time('operation');
  
  try {
    const result = await withTimeout(
      problematicOperation(),
      5000,
      'Debug timeout'
    );
    console.timeEnd('operation');
    expect(result).toBeDefined();
  } catch (error) {
    console.timeEnd('operation');
    console.error('Operation failed:', error);
    throw error;
  }
});
```

**Prevention:**
- Profile slow operations
- Use appropriate timeouts for different operation types
- Mock slow operations when possible

## Coverage and Reporting Problems

### Issue: Coverage reports missing files

**Symptoms:**
```
Coverage report doesn't include all source files
Some files show 0% coverage incorrectly
```

**Solution:**
```typescript
// Check vitest.config.ts coverage configuration
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{js,ts,tsx}'], // Include all source files
      exclude: [
        'node_modules/**',
        'src/test/**',
        '**/*.test.*',
        '**/*.spec.*',
        '**/*.d.ts'
      ],
      all: true, // Include all files, even untested ones
    }
  }
});
```

**Prevention:**
- Configure coverage to include all source files
- Exclude only test files and type definitions
- Use `all: true` to show untested files

### Issue: Coverage thresholds failing

**Symptoms:**
```
Coverage threshold for lines (80%) not met: 75%
Coverage check failed
```

**Solution:**
```bash
# Check current coverage
npm run test:coverage

# Identify uncovered lines
open coverage/index.html

# Write tests for uncovered code
# Or adjust thresholds if appropriate
```

**Temporary Threshold Adjustment:**
```typescript
// vitest.config.ts - adjust thresholds temporarily
export default defineConfig({
  test: {
    coverage: {
      threshold: {
        lines: 75,    // Temporarily lower
        functions: 75,
        branches: 70,
        statements: 75
      }
    }
  }
});
```

**Prevention:**
- Write tests as you develop features
- Monitor coverage regularly
- Set realistic but challenging thresholds

### Issue: Coverage reports not generated

**Symptoms:**
```
No coverage directory created
Coverage command fails silently
```

**Solution:**
```bash
# Install coverage provider
npm install --save-dev @vitest/coverage-v8

# Run coverage explicitly
npx vitest run --coverage

# Check configuration
npx vitest --help | grep coverage
```

**Prevention:**
- Ensure coverage provider is installed
- Verify coverage configuration in vitest.config.ts
- Test coverage generation in CI/CD pipeline

## CI/CD Integration Issues

### Issue: Tests pass locally but fail in CI

**Symptoms:**
```
Tests fail in GitHub Actions
Different behavior between local and CI
```

**Solution:**
```yaml
# .github/workflows/test.yml
- name: Run tests with proper environment
  run: npm test
  env:
    CI: true
    NODE_ENV: test
    # Add any required environment variables
```

**Debug CI Environment:**
```typescript
// Add debug information to tests
console.log('Environment:', {
  CI: process.env.CI,
  NODE_ENV: process.env.NODE_ENV,
  platform: process.platform,
  nodeVersion: process.version
});
```

**Prevention:**
- Use consistent environment variables
- Test in Docker containers locally
- Monitor CI/CD pipeline regularly

### Issue: Pre-commit hooks failing

**Symptoms:**
```
Pre-commit hook failed: tests
Husky hook execution failed
```

**Solution:**
```bash
# Check pre-commit hook configuration
cat .husky/pre-commit

# Run pre-commit checks manually
npm test
npm run build
npm run lint

# Fix any failing checks
```

**Prevention:**
- Run pre-commit checks before committing
- Keep pre-commit hooks fast and reliable
- Use appropriate test selection for pre-commit

### Issue: Artifacts not collected

**Symptoms:**
```
Test reports not available in CI
Coverage reports missing
```

**Solution:**
```yaml
# GitHub Actions - collect artifacts
- name: Upload test results
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: test-results
    path: |
      test-results/
      coverage/
```

**Prevention:**
- Configure artifact collection in CI/CD
- Ensure test reports are generated
- Use consistent paths for artifacts

## Performance Problems

### Issue: Tests run slowly

**Symptoms:**
```
Test suite takes too long to complete
Individual tests are slow
```

**Solution:**
```typescript
// Use lightweight mocks
import { createMockCacheManager } from '../test/cacheManagerMocks';

describe('Fast Tests', () => {
  beforeEach(async () => {
    // Use mock instead of real CacheManager
    const mockCache = createMockCacheManager();
    await mockCache.initialize(); // Much faster
  });
});
```

**Parallel Execution:**
```typescript
// vitest.config.ts - optimize for performance
export default defineConfig({
  test: {
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false, // Enable parallel execution
        isolate: true,
        useAtomics: true
      }
    }
  }
});
```

**Prevention:**
- Use mocks for external dependencies
- Enable parallel test execution
- Profile slow tests and optimize

### Issue: Memory usage too high

**Symptoms:**
```
Out of memory errors
Tests become slower over time
```

**Solution:**
```typescript
// Proper cleanup in tests
describe('Memory Tests', () => {
  afterEach(async () => {
    // Clean up large objects
    await resetTestEnvironment();
    
    // Force garbage collection in Node.js
    if (global.gc) {
      global.gc();
    }
  });
});
```

**Prevention:**
- Clean up resources in `afterEach`
- Avoid creating large objects in tests
- Monitor memory usage during test runs

### Issue: Test isolation problems

**Symptoms:**
```
Tests fail when run together but pass individually
State leaks between tests
```

**Solution:**
```typescript
// Ensure proper test isolation
describe('Isolated Tests', () => {
  beforeEach(async () => {
    // Fresh environment for each test
    await initializeTestEnvironment();
  });

  afterEach(async () => {
    // Complete cleanup
    await teardownTestEnvironment();
  });
});
```

**Prevention:**
- Use proper setup and teardown
- Avoid global state in tests
- Test both individually and together

## Mock Reset and Cleanup Issues

### Issue: Mocks not reset between tests

**Symptoms:**
```
Mock call counts accumulate
Previous test affects current test
```

**Solution:**
```typescript
import { vi } from 'vitest';

describe('Mock Reset Tests', () => {
  afterEach(() => {
    // Reset all mocks
    vi.clearAllMocks();
    
    // Reset specific mocks
    fetchMock.mockClear();
    
    // Reset test environment
    resetTestEnvironment();
  });
});
```

**Prevention:**
- Always reset mocks in `afterEach`
- Use `vi.clearAllMocks()` for comprehensive reset
- Verify mock state before tests

### Issue: Global state not cleaned up

**Symptoms:**
```
Global variables persist between tests
DOM state leaks between tests
```

**Solution:**
```typescript
describe('Cleanup Tests', () => {
  afterEach(async () => {
    // Clean up DOM
    document.body.innerHTML = '';
    
    // Reset global variables
    delete (global as any).testVariable;
    
    // Reset test environment
    await resetTestEnvironment();
  });
});
```

**Prevention:**
- Avoid global state in tests
- Clean up DOM modifications
- Use proper test isolation

## Getting Help

### Debug Information Collection

When reporting issues, collect this debug information:

```typescript
// Add to failing test
import { getTestEnvironmentState } from '../test/testSetup';

console.log('Debug Information:', {
  environment: getTestEnvironmentState(),
  nodeVersion: process.version,
  platform: process.platform,
  ci: process.env.CI,
  vitest: process.env.VITEST
});
```

### Common Debug Commands

```bash
# Run single test with debug output
npm test -- --reporter=verbose src/path/to/test.ts

# Run tests with coverage
npm run test:coverage

# Check test environment
node -e "console.log(process.env)"

# Verify dependencies
npm list canvas fake-indexeddb jsdom vitest
```

### Reporting Issues

When reporting test environment issues, include:

1. **Error message and stack trace**
2. **Test code that reproduces the issue**
3. **Environment information** (OS, Node version, npm version)
4. **Package versions** (`npm list` output)
5. **Configuration files** (vitest.config.ts, package.json)
6. **Steps to reproduce**

This troubleshooting guide should help resolve most common issues with the frontend test environment. For additional help, consult the main documentation or create an issue with detailed debug information.