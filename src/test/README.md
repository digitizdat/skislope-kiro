# Frontend Test Environment

This directory contains the comprehensive test environment setup for the Alpine Ski Simulator frontend, providing reliable testing infrastructure for all browser APIs and services.

## Overview

The test environment provides mocks and utilities for:

- **WebGL Context**: Headless WebGL rendering for Three.js tests
- **IndexedDB**: Complete IndexedDB mocking for CacheManager tests
- **Browser APIs**: localStorage, sessionStorage, fetch, XMLHttpRequest, Web Audio API
- **File APIs**: Blob, File, and URL object creation
- **Test Setup**: Automated environment initialization and cleanup

## Key Files

### Core Test Setup
- `testSetup.ts` - Main test environment initialization and teardown
- `setup.ts` - Vitest setup file that initializes the test environment

### Browser API Mocks
- `browserAPIMocks.ts` - Comprehensive browser API mocks with vitest integration
- `simpleBrowserMocks.ts` - Simple browser API mocks without vitest dependencies
- `webglMocks.ts` - WebGL context mocking utilities

### Test Files
- `browserAPIMocks.simple.test.ts` - Tests for comprehensive browser API mocks
- `simpleBrowserMocks.test.ts` - Tests for simple browser API mocks
- `browserAPIIntegration.test.ts` - Integration tests for the complete test environment
- `testSetup.test.ts` - Tests for the test setup infrastructure

## Usage

### Basic Test Setup

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { initializeTestEnvironment, teardownTestEnvironment } from './testSetup';

describe('My Component Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  afterEach(async () => {
    await teardownTestEnvironment();
  });

  it('should work with browser APIs', () => {
    // localStorage, fetch, AudioContext, etc. are all available
    localStorage.setItem('test', 'value');
    expect(localStorage.getItem('test')).toBe('value');
  });
});
```

### Using Specific Mocks

```typescript
import { createFetchMock, createStorageMock } from './browserAPIMocks';

describe('Service Tests', () => {
  it('should handle fetch operations', async () => {
    const fetchMock = createFetchMock();
    
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: { message: 'success' }
    });
    
    const response = await fetchMock('/api/data');
    const data = await response.json();
    
    expect(data.message).toBe('success');
  });
});
```

### WebGL Testing

```typescript
import { createWebGLContextMock } from './testSetup';

describe('Three.js Tests', () => {
  it('should create WebGL context', () => {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl');
    
    expect(gl).toBeDefined();
    expect(typeof gl.createShader).toBe('function');
    
    // Test WebGL operations
    gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
  });
});
```

### CacheManager Testing

```typescript
import { cacheManager } from '../utils/CacheManager';

describe('CacheManager Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should cache and retrieve data', async () => {
    const testData = { message: 'test' };
    
    await cacheManager.cacheTerrainData(testData, mockRun, 'medium');
    const cached = await cacheManager.getCachedTerrainData(mockRun.id, 'medium');
    
    expect(cached).toEqual(testData);
  });
});
```

## Features

### Automatic Environment Setup

The test environment automatically:

1. **Initializes WebGL Context**: Creates headless WebGL context using canvas package
2. **Sets up IndexedDB**: Configures fake-indexeddb for database operations
3. **Installs Browser API Mocks**: Provides localStorage, fetch, AudioContext, etc.
4. **Initializes CacheManager**: Sets up the cache system for testing
5. **Handles Cleanup**: Properly tears down all mocks and connections

### Mock Capabilities

#### Storage APIs
- Full localStorage and sessionStorage implementation
- Persistent storage between test operations
- Automatic cleanup between tests

#### Network APIs
- Fetch API with customizable responses
- XMLHttpRequest with event handling
- Support for JSON, text, blob, and arrayBuffer responses

#### Web Audio API
- Complete AudioContext implementation
- All audio node types (oscillator, gain, panner, etc.)
- Audio buffer creation and management
- State management (suspended, running, closed)

#### File APIs
- Blob and File creation with size calculation
- URL.createObjectURL and revokeObjectURL
- ArrayBuffer and text conversion

### Error Handling

The test environment provides:

- **Graceful Fallbacks**: Falls back to simple mocks if comprehensive mocks fail
- **Clear Error Messages**: Detailed error information for debugging
- **Environment Validation**: Checks for required dependencies and setup
- **Cleanup on Failure**: Ensures clean state even when tests fail

## Configuration

### Vitest Configuration

The test environment integrates with Vitest configuration in `vitest.config.ts`:

```typescript
export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    timeout: 10000,
  }
});
```

### Dependencies

Required packages for the test environment:

- `canvas` - WebGL context for headless testing
- `fake-indexeddb` - IndexedDB mocking
- `jsdom` - DOM environment
- `vitest` - Test runner
- `@vitest/coverage-v8` - Coverage reporting

## Troubleshooting

### Common Issues

1. **WebGL Context Errors**
   - Ensure `canvas` package is installed
   - Check that WebGL context is being created in tests

2. **IndexedDB Errors**
   - Verify `fake-indexeddb/auto` is imported
   - Check database initialization in CacheManager

3. **Mock Reset Issues**
   - Ensure proper cleanup in `afterEach` hooks
   - Use `resetTestEnvironment()` for partial resets

4. **Performance Issues**
   - Use `resetTestEnvironment()` instead of full teardown when possible
   - Consider test isolation for heavy operations

### Debug Information

Use the test environment state utilities:

```typescript
import { getTestEnvironmentState, isWebGLAvailable, isIndexedDBAvailable } from './testSetup';

// Check environment status
console.log('WebGL available:', isWebGLAvailable());
console.log('IndexedDB available:', isIndexedDBAvailable());
console.log('Environment state:', getTestEnvironmentState());
```

## Requirements Satisfied

This test environment implementation satisfies the following requirements:

- **4.1**: Comprehensive browser API mocks for localStorage, sessionStorage, and other storage APIs
- **4.2**: Fetch API and XMLHttpRequest mocking for network operations  
- **4.4**: Web Audio API mocks for audio service testing

The implementation provides a robust foundation for testing all frontend services and components without external dependencies.