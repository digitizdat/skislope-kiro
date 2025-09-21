# Frontend Test Environment Documentation

## Overview

The Alpine Ski Simulator frontend test environment provides testing infrastructure specifically for React components, services, and browser APIs. This guide covers frontend-specific testing setup, configuration, and usage patterns.

**📖 For Complete Testing Coverage**: This document focuses on frontend testing. For the full testing ecosystem including agent testing, integration testing, and deployment validation, see the [Comprehensive Testing Guide](./COMPREHENSIVE_TESTING_GUIDE.md).

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Mock Systems](#mock-systems)
5. [Usage Patterns](#usage-patterns)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [Performance Optimization](#performance-optimization)
9. [CI/CD Integration](#cicd-integration)

## Quick Start

### Prerequisites

Ensure you have the required dependencies installed:

```bash
# Install frontend dependencies
npm install

# Required packages for test environment
npm install --save-dev canvas fake-indexeddb jsdom vitest @vitest/coverage-v8
```

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test -- src/services/TerrainService.test.ts

# Run tests matching pattern
npm test -- --grep "CacheManager"
```

### Basic Test Setup

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { initializeTestEnvironment, resetTestEnvironment } from '../test/testSetup';

describe('My Component Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  afterEach(async () => {
    await resetTestEnvironment();
  });

  it('should work with browser APIs', () => {
    // All browser APIs are available and mocked
    localStorage.setItem('test', 'value');
    expect(localStorage.getItem('test')).toBe('value');
  });
});
```

## Architecture

### Test Environment Layers

The test environment is structured in multiple layers:

```
┌─────────────────────────────────────┐
│           Test Runner (Vitest)      │
├─────────────────────────────────────┤
│         Test Setup Layer            │
│  - Environment initialization       │
│  - Mock coordination                │
│  - Cleanup management               │
├─────────────────────────────────────┤
│       Mock Infrastructure           │
│  - WebGL Context Mock               │
│  - IndexedDB Mock                   │
│  - Browser API Mocks                │
│  - Network Mocks                    │
├─────────────────────────────────────┤
│     Environment Configuration       │
│  - TypeScript Config                │
│  - Module Resolution                │
│  - Environment Variables            │
└─────────────────────────────────────┘
```

### Key Components

- **`src/test/setup.ts`**: Main Vitest setup file that initializes the test environment
- **`src/test/testSetup.ts`**: Core test environment initialization and teardown
- **`src/test/browserAPIMocks.ts`**: Comprehensive browser API mocking
- **`src/test/webglMocks.ts`**: WebGL context mocking for Three.js
- **`src/test/cacheManagerMocks.ts`**: CacheManager mocking utilities
- **`src/test/asyncTestUtils.ts`**: Async operation testing utilities

## Configuration

### Vitest Configuration

The test environment is configured in `vitest.config.ts`:

```typescript
export default defineConfig({
  test: {
    // Environment setup
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    
    // Timeout configuration (adjusted for CI)
    timeout: 10000,
    testTimeout: 5000,
    hookTimeout: 10000,
    
    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      threshold: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80
      }
    },
    
    // Performance settings
    isolate: true,
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false,
        isolate: true,
        useAtomics: true
      }
    }
  }
});
```

### Environment Variables

The test environment supports several environment variables for configuration:

```bash
# Timeout configuration
VITEST_TIMEOUT=10000              # Global timeout (ms)
VITEST_TEST_TIMEOUT=5000          # Individual test timeout (ms)
VITEST_HOOK_TIMEOUT=10000         # Hook timeout (ms)

# CI configuration
CI=true                           # Enable CI mode
CI_RETRY_COUNT=2                  # Number of retries in CI

# Debug configuration
DEBUG_TEST_SETUP=true             # Enable test setup debugging
DEBUG_MOCK_OPERATIONS=true        # Enable mock operation debugging
DEBUG_CACHE_OPERATIONS=true       # Enable cache operation debugging
```

## Mock Systems

### WebGL Context Mock

The WebGL mock provides a complete WebGL context for Three.js testing:

```typescript
import { createWebGLContextMock } from '../test/testSetup';

describe('Three.js Tests', () => {
  it('should create WebGL context', () => {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl');
    
    expect(gl).toBeDefined();
    expect(typeof gl.createShader).toBe('function');
    
    // All WebGL operations are mocked
    const shader = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(shader, 'vertex shader source');
    gl.compileShader(shader);
  });
});
```

### IndexedDB Mock

IndexedDB is fully mocked using `fake-indexeddb`:

```typescript
describe('IndexedDB Tests', () => {
  it('should work with IndexedDB operations', async () => {
    const request = indexedDB.open('testDB', 1);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      const store = db.createObjectStore('data', { keyPath: 'id' });
    };
    
    const db = await new Promise((resolve) => {
      request.onsuccess = () => resolve(request.result);
    });
    
    expect(db).toBeDefined();
  });
});
```

### Browser API Mocks

All major browser APIs are mocked:

```typescript
describe('Browser API Tests', () => {
  it('should mock localStorage', () => {
    localStorage.setItem('key', 'value');
    expect(localStorage.getItem('key')).toBe('value');
  });

  it('should mock fetch API', async () => {
    // Fetch is automatically mocked
    const response = await fetch('/api/data');
    expect(response.ok).toBe(true);
  });

  it('should mock Web Audio API', () => {
    const audioContext = new AudioContext();
    const oscillator = audioContext.createOscillator();
    expect(oscillator.frequency.value).toBe(440);
  });
});
```

### CacheManager Mock

The CacheManager has specialized mocking utilities:

```typescript
import { createMockCacheManager } from '../test/cacheManagerMocks';

describe('CacheManager Tests', () => {
  let mockCacheManager;

  beforeEach(async () => {
    mockCacheManager = createMockCacheManager();
    await mockCacheManager.initialize();
  });

  it('should cache and retrieve data', async () => {
    const testData = { message: 'test' };
    
    await mockCacheManager.cacheTerrainData(testData, mockRun, 'medium');
    const cached = await mockCacheManager.getCachedTerrainData(mockRun.id, 'medium');
    
    expect(cached).toEqual(testData);
  });
});
```

## Usage Patterns

### Component Testing

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { initializeTestEnvironment } from '../test/testSetup';
import MyComponent from './MyComponent';

describe('MyComponent', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should render correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });
});
```

### Service Testing

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { initializeTestEnvironment } from '../test/testSetup';
import { TerrainService } from './TerrainService';

describe('TerrainService', () => {
  let terrainService;

  beforeEach(async () => {
    await initializeTestEnvironment();
    terrainService = new TerrainService();
  });

  it('should load terrain data', async () => {
    // Mock fetch response
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ elevation: [100, 200, 300] })
    });

    const data = await terrainService.loadTerrainData('test-run');
    expect(data.elevation).toHaveLength(3);
  });
});
```

### Async Testing

```typescript
import { waitFor, delay, withTimeout } from '../test/asyncTestUtils';

describe('Async Operations', () => {
  it('should handle async operations with timeout', async () => {
    const result = await withTimeout(
      someAsyncOperation(),
      5000,
      'Operation should complete within 5 seconds'
    );
    
    expect(result).toBeDefined();
  });

  it('should wait for condition', async () => {
    let condition = false;
    
    setTimeout(() => { condition = true; }, 100);
    
    await waitFor(() => condition, {
      timeout: 1000,
      interval: 50
    });
    
    expect(condition).toBe(true);
  });
});
```

### Mock Customization

```typescript
import { createFetchMock } from '../test/browserAPIMocks';

describe('Custom Mock Tests', () => {
  it('should customize fetch responses', async () => {
    const fetchMock = createFetchMock();
    
    fetchMock.mockImplementation(async (url) => {
      if (url.includes('/api/terrain')) {
        return {
          ok: true,
          status: 200,
          json: () => Promise.resolve({ elevation: [1, 2, 3] })
        };
      }
      return {
        ok: false,
        status: 404,
        json: () => Promise.resolve({ error: 'Not found' })
      };
    });

    global.fetch = fetchMock;
    
    const response = await fetch('/api/terrain');
    const data = await response.json();
    
    expect(data.elevation).toEqual([1, 2, 3]);
  });
});
```

## Best Practices

### Test Organization

1. **Group related tests**: Use `describe` blocks to group related functionality
2. **Use descriptive names**: Test names should clearly describe what is being tested
3. **Setup and teardown**: Always use `beforeEach` and `afterEach` for clean test state
4. **Isolate tests**: Each test should be independent and not rely on other tests

### Mock Usage

1. **Use appropriate mocks**: Choose the right level of mocking for your test
2. **Reset mocks**: Always reset mocks between tests to avoid interference
3. **Verify mock calls**: Use `expect().toHaveBeenCalledWith()` to verify interactions
4. **Mock at the right level**: Mock at the boundary of your unit under test

### Async Testing

1. **Use proper timeouts**: Set appropriate timeouts for async operations
2. **Handle promises correctly**: Always await async operations in tests
3. **Test error conditions**: Test both success and failure scenarios
4. **Use async utilities**: Leverage the provided async testing utilities

### Performance

1. **Minimize setup**: Only initialize what you need for each test
2. **Use reset over teardown**: Use `resetTestEnvironment()` when possible
3. **Parallel execution**: Structure tests to run in parallel safely
4. **Cache test data**: Reuse test data when appropriate

## Troubleshooting

See the [Frontend Test Troubleshooting Guide](./FRONTEND_TEST_TROUBLESHOOTING.md) for detailed troubleshooting information.

## Performance Optimization

### Test Execution Speed

1. **Parallel execution**: Tests run in parallel by default
2. **Selective testing**: Use patterns to run specific tests
3. **Mock optimization**: Use lightweight mocks when possible
4. **Timeout tuning**: Adjust timeouts based on environment

### Memory Management

1. **Cleanup**: Always clean up resources in `afterEach`
2. **Mock reset**: Reset mocks to prevent memory leaks
3. **Large data**: Be careful with large test data sets
4. **Garbage collection**: Allow garbage collection between tests

## CI/CD Integration

### GitHub Actions

The test environment is optimized for CI/CD:

```yaml
- name: Run Frontend Tests
  run: |
    npm test
  env:
    CI: true
    NODE_ENV: test
```

### Pre-commit Hooks

Tests are integrated with pre-commit hooks:

```bash
# Run before commit
npm test
npm run build
```

### Coverage Requirements

- Minimum 80% coverage for lines, functions, branches, and statements
- Coverage reports are generated in HTML and JSON formats
- Coverage thresholds are enforced in CI/CD

## Requirements Satisfied

This test environment implementation satisfies the following requirements:

- **8.4**: Complete documentation for test environment setup and configuration
- **8.5**: Comprehensive troubleshooting guide for common test environment issues
- **1.1-1.3**: WebGL context mocking for Three.js testing
- **2.1-2.4**: CacheManager mocking and IndexedDB support
- **3.1-3.4**: Async operation handling and timeout management
- **4.1-4.4**: Browser API mocking for all required APIs
- **5.1-5.2**: Environment configuration and consistency
- **6.1-6.2**: Performance optimization and test execution
- **7.1-7.2**: Coverage reporting and thresholds
- **8.1-8.3**: CI/CD integration and pre-commit hooks

## Integration with Broader Testing Infrastructure

This frontend test environment is part of a comprehensive testing ecosystem:

### Agent Testing Integration
- **API Contract Validation**: Frontend AgentClient methods are validated against backend agent implementations
- **Cross-System Communication**: Frontend requests are tested against real agent servers
- **Integration Workflows**: Complete user scenarios tested from frontend through agents

### CI/CD Integration
- **Pre-commit Hooks**: Lightweight frontend validation before commits
- **GitHub Actions**: Automated frontend testing in CI/CD pipeline
- **Deployment Validation**: Frontend build verification in smoke tests

### Related Testing Infrastructure
- **Agent Tests**: Python-based testing for hill metrics, weather, and equipment agents
- **Integration Tests**: Cross-system validation and API contract testing
- **Deployment Tests**: Production readiness and smoke testing

## Additional Resources

- **[Comprehensive Testing Guide](./COMPREHENSIVE_TESTING_GUIDE.md)** - Complete testing ecosystem overview
- **[Frontend Test Scripts Guide](./FRONTEND_TEST_SCRIPTS_GUIDE.md)** - Complete reference for all npm test scripts
- [Frontend Test Troubleshooting Guide](./FRONTEND_TEST_TROUBLESHOOTING.md)
- [Mock Usage Patterns](./FRONTEND_TEST_MOCK_PATTERNS.md)
- [Async Testing Best Practices](./FRONTEND_TEST_ASYNC_PATTERNS.md)