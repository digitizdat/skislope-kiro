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
  AsyncTestUtils,
  NetworkTestUtils,
  ErrorTestUtils,
  PerformanceTestUtils,
} from './testUtils';

// WebGL and Three.js mocking infrastructure
export {
  WebGLContextMock,
  ThreeJSTerrainMocks,
  WebGLTestEnvironment,
} from './webglMocks';

// Re-export common testing library utilities
export { cleanup } from '@testing-library/react';
export { vi } from 'vitest';