# Async Operation Test Utilities

This document describes the async operation test utilities provided for handling Promise-based operations, timeout management, and controlling timing and execution order in async tests.

## Overview

The async test utilities address common challenges in testing asynchronous operations:

- **Promise-based operations**: Utilities for waiting on conditions and promises with proper timeout handling
- **Timeout management**: Environment-aware timeout values optimized for both local development and CI environments
- **Timing control**: Tools for controlling execution order and managing race conditions in tests
- **Fake timer integration**: Support for Vitest fake timers to control time in tests

## Core Classes

### AsyncTestUtils

The main utility class providing comprehensive async testing capabilities.

#### Configuration

```typescript
import { AsyncTestUtils, configureAsyncTests } from './asyncTestUtils';

// Configure global settings
configureAsyncTests({
  defaultTimeout: 3000,    // Local environment timeout
  ciTimeout: 10000,        // CI environment timeout
  maxRetries: 5,           // Default retry attempts
  baseDelay: 50,           // Base delay for exponential backoff
  useFakeTimers: false     // Whether to use fake timers by default
});
```

#### Basic Usage

```typescript
import { waitFor, waitForPromise, flushPromises, delay } from './asyncTestUtils';

// Wait for a condition to become true
await waitFor(() => someCondition === true, { timeout: 5000 });

// Wait for a promise with timeout
const result = await waitForPromise(somePromise, 3000);

// Flush all pending promises
await flushPromises();

// Create a delay
await delay(100);
```

#### Advanced Promise Handling

```typescript
import { AsyncTestUtils } from './asyncTestUtils';

// Wait for multiple promises with individual timeouts
const results = await AsyncTestUtils.waitForAll([
  { promise: fetchData(), timeout: 5000, name: 'data-fetch' },
  { promise: loadConfig(), timeout: 2000, name: 'config-load' }
], {
  failFast: true,           // Fail immediately on first error
  globalTimeout: 10000      // Overall timeout for all operations
});

// Retry operations with exponential backoff
const result = await AsyncTestUtils.retry(
  () => unstableOperation(),
  {
    maxAttempts: 3,
    baseDelay: 100,
    backoffFactor: 2,
    shouldRetry: (error, attempt) => error.message.includes('temporary')
  }
);
```

#### Fake Timer Support

```typescript
import { AsyncTestUtils } from './asyncTestUtils';

// Install fake timers
AsyncTestUtils.installFakeTimers();

// Advance time
await AsyncTestUtils.advanceTimers(1000);

// Run all pending timers
await AsyncTestUtils.runAllTimers();

// Restore real timers
AsyncTestUtils.restoreTimers();
```

### TimingController

Controls execution order of async operations with dependency management.

```typescript
import { createTimingController } from './asyncTestUtils';

const controller = createTimingController();

// Add operations with dependencies
controller.addOperation('setup', async () => {
  return await setupDatabase();
});

controller.addOperation('seed-data', async () => {
  return await seedTestData();
}, ['setup']); // Depends on 'setup'

controller.addOperation('run-test', async () => {
  return await runActualTest();
}, ['setup', 'seed-data']); // Depends on both previous operations

// Execute all operations in dependency order
const results = await controller.executeAll();
```

### AsyncTestPatterns

Common testing patterns for async operations.

```typescript
import { 
  expectToCompleteWithin, 
  expectToEventuallySucceed, 
  testConcurrency 
} from './asyncTestUtils';

// Test that operation completes within time limit
const result = await expectToCompleteWithin(
  () => fastOperation(),
  500 // Should complete within 500ms
);

// Test that operation eventually succeeds after retries
const result = await expectToEventuallySucceed(
  () => eventuallyWorkingOperation(),
  {
    timeout: 5000,
    interval: 100,
    expectedErrors: (error) => error.message.includes('not ready')
  }
);

// Test concurrent operations
const results = await testConcurrency([
  () => operation1(),
  () => operation2(),
  () => operation3()
], {
  expectSameResult: false,  // Allow different results
  allowFailures: false,     // All must succeed
  timeout: 3000            // Individual operation timeout
});
```

## Environment Configuration

The utilities automatically detect the environment and adjust timeouts accordingly:

- **Local Development**: Uses `defaultTimeout` (5 seconds by default)
- **CI Environment**: Uses `ciTimeout` (15 seconds by default) when `process.env.CI === 'true'`

```typescript
import { getTestTimeout } from './asyncTestUtils';

// Get environment-appropriate timeout
const timeout = getTestTimeout(); // 5000ms locally, 15000ms in CI

// Override with custom config
const customTimeout = getTestTimeout({ defaultTimeout: 3000, ciTimeout: 12000 });
```

## Common Usage Patterns

### Testing Cache Operations

```typescript
import { waitFor, flushPromises } from './asyncTestUtils';

test('cache operations', async () => {
  // Start async cache operation
  const cachePromise = cacheManager.set('key', 'value');
  
  // Wait for cache to be ready
  await waitFor(() => cacheManager.isInitialized);
  
  // Ensure all promises are resolved
  await flushPromises();
  
  // Verify cache state
  const value = await cacheManager.get('key');
  expect(value).toBe('value');
});
```

### Testing Network Operations

```typescript
import { retry, withTimeout } from './asyncTestUtils';

test('network operations with retry', async () => {
  // Retry network operation with exponential backoff
  const data = await retry(
    () => fetchDataFromAPI(),
    {
      maxAttempts: 3,
      baseDelay: 100,
      shouldRetry: (error) => error.status >= 500 // Only retry server errors
    }
  );
  
  expect(data).toBeDefined();
});

test('network timeout handling', async () => {
  // Test that operation respects timeout
  await expect(
    withTimeout(slowNetworkOperation(), 1000)
  ).rejects.toThrow('Operation timed out');
});
```

### Testing Component Lifecycle

```typescript
import { waitFor, expectToCompleteWithin } from './asyncTestUtils';

test('component initialization', async () => {
  const component = new MyComponent();
  
  // Wait for component to initialize
  await waitFor(() => component.isInitialized);
  
  // Test that initialization completes quickly
  await expectToCompleteWithin(
    () => component.initialize(),
    1000 // Should initialize within 1 second
  );
});
```

### Testing Race Conditions

```typescript
import { testConcurrency, TimingController } from './asyncTestUtils';

test('concurrent cache access', async () => {
  // Test that concurrent operations don't interfere
  const operations = [
    () => cacheManager.set('key1', 'value1'),
    () => cacheManager.set('key2', 'value2'),
    () => cacheManager.get('key1')
  ];
  
  const results = await testConcurrency(operations, {
    allowFailures: false,
    timeout: 2000
  });
  
  expect(results).toHaveLength(3);
});

test('ordered async operations', async () => {
  const controller = createTimingController();
  
  controller.addOperation('init', () => initializeSystem());
  controller.addOperation('load', () => loadData(), ['init']);
  controller.addOperation('process', () => processData(), ['load']);
  
  const results = await controller.executeAll();
  expect(results.size).toBe(3);
});
```

## Error Handling

The utilities provide comprehensive error handling with detailed context:

```typescript
// Timeout errors include timing information
await expect(
  waitFor(() => false, { timeout: 100 })
).rejects.toThrow('Condition was not met within timeout (timeout: 100ms)');

// Retry errors include attempt information
await expect(
  retry(() => Promise.reject(new Error('fail')), { maxAttempts: 2 })
).rejects.toThrow('fail');

// Dependency errors include operation context
const controller = createTimingController();
controller.addOperation('a', () => Promise.resolve(), ['nonexistent']);
await expect(controller.executeAll()).rejects.toThrow('unresolvable dependencies');
```

## Best Practices

1. **Use environment-aware timeouts**: Always use `getTestTimeout()` for consistent behavior across environments
2. **Flush promises in tests**: Use `flushPromises()` to ensure all async operations complete before assertions
3. **Handle race conditions**: Use `TimingController` for operations that must execute in specific order
4. **Retry transient failures**: Use `retry()` for operations that may fail temporarily
5. **Test timeout scenarios**: Use `withTimeout()` to verify operations respect time limits
6. **Use fake timers sparingly**: Only use fake timers when you need precise control over timing

## Integration with Existing Test Infrastructure

The async utilities integrate seamlessly with the existing test setup:

```typescript
// In test files
import { 
  waitFor, 
  flushPromises, 
  expectToCompleteWithin 
} from '../test/asyncTestUtils';

// The utilities work with existing mocks and setup
test('terrain loading with async utilities', async () => {
  const terrainService = new TerrainService();
  
  // Wait for service to initialize
  await waitFor(() => terrainService.isReady);
  
  // Test loading completes within reasonable time
  const terrain = await expectToCompleteWithin(
    () => terrainService.loadTerrain('test-area'),
    5000
  );
  
  expect(terrain).toBeDefined();
});
```

The utilities are automatically available through the main test index and work with all existing test infrastructure including WebGL mocks, cache mocks, and browser API mocks.