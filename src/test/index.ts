/**
 * Test utilities and setup exports
 * Provides a centralized export for all testing infrastructure
 */

// Core test setup
export {
  initializeTestEnvironment,
  teardownTestEnvironment,
  resetTestEnvironment,
  createWebGLContextMock,
  setupWebGLEnvironment,
  setupIndexedDBMock,
  setupBrowserAPIMocks,
  getTestEnvironmentState,
  isWebGLAvailable,
  isIndexedDBAvailable,
} from './testSetup';

// Test utilities
export {
  ThreeJSTestUtils,
  CacheTestUtils,
  DeferredPromiseUtils,
  NetworkTestUtils,
  ErrorTestUtils,
  PerformanceTestUtils,
} from './testUtils';

// Async operation test utilities
export {
  AsyncTestUtils,
  TimingController,
  AsyncTestPatterns,
  waitFor,
  waitForPromise,
  waitForAll,
  flushPromises,
  flushAllPromises,
  delay,
  retry,
  withTimeout,
  installFakeTimers,
  restoreTimers,
  advanceTimers,
  advanceToNextTimer,
  runAllTimers,
  getTimerCount,
  clearAllTimers,
  expectToCompleteWithin,
  expectToTakeAtLeast,
  expectToEventuallySucceed,
  testConcurrency,
  createTimingController,
  getTestTimeout,
  configureAsyncTests,
  DEFAULT_ASYNC_CONFIG,
} from './asyncTestUtils';

// WebGL and Three.js mocking infrastructure
export {
  WebGLContextMock,
  ThreeJSTerrainMocks,
  WebGLTestEnvironment,
} from './webglMocks';

// Re-export common testing library utilities
export { cleanup } from '@testing-library/react';
export { vi } from 'vitest';