/**
 * Test Configuration for Frontend Test Environment
 * 
 * This configuration provides consistent test execution settings
 * across local development and CI/CD environments.
 */

import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'

// Load environment variables from test.env
const env = loadEnv('test', process.cwd(), '')

// Determine if running in CI environment
const isCI = process.env.CI === 'true' || process.env.GITHUB_ACTIONS === 'true'

// Calculate timeouts based on environment
const baseTimeout = parseInt(env.VITEST_TIMEOUT || '10000')
const testTimeout = parseInt(env.VITEST_TEST_TIMEOUT || '5000')
const hookTimeout = parseInt(env.VITEST_HOOK_TIMEOUT || '10000')

// Apply CI timeout multiplier if in CI environment
const ciMultiplier = parseFloat(env.CI_TIMEOUT_MULTIPLIER || '1.5')
const finalTimeout = isCI ? Math.floor(baseTimeout * ciMultiplier) : baseTimeout
const finalTestTimeout = isCI ? Math.floor(testTimeout * ciMultiplier) : testTimeout
const finalHookTimeout = isCI ? Math.floor(hookTimeout * ciMultiplier) : hookTimeout

export const testConfig = {
  // Environment detection
  isCI,
  isDevelopment: !isCI,
  
  // Timeout configuration
  timeout: finalTimeout,
  testTimeout: finalTestTimeout,
  hookTimeout: finalHookTimeout,
  
  // Coverage configuration
  coverage: {
    provider: env.VITEST_COVERAGE_PROVIDER || 'v8',
    threshold: {
      lines: parseInt(env.VITEST_COVERAGE_THRESHOLD_LINES || '80'),
      functions: parseInt(env.VITEST_COVERAGE_THRESHOLD_FUNCTIONS || '80'),
      branches: parseInt(env.VITEST_COVERAGE_THRESHOLD_BRANCHES || '80'),
      statements: parseInt(env.VITEST_COVERAGE_THRESHOLD_STATEMENTS || '80')
    },
    reportsDirectory: env.TEST_COVERAGE_DIR || './coverage',
    reporter: isCI 
      ? ['text', 'json', 'lcov', 'html']
      : ['text', 'html'],
    exclude: [
      'node_modules/**',
      'dist/**',
      '**/*.d.ts',
      '**/*.config.*',
      '**/test/**',
      '**/tests/**',
      '**/*.test.*',
      '**/*.spec.*',
      'src/test/**',
      'coverage/**',
      '.eslintrc.cjs',
      'vite.config.ts',
      'vitest.config.ts',
      'test.config.js'
    ]
  },
  
  // Performance configuration
  performance: {
    logHeapUsage: env.VITEST_LOG_HEAP_USAGE === 'true',
    pool: env.VITEST_POOL || 'threads',
    isolate: env.VITEST_ISOLATE === 'true',
    parallel: isCI ? parseInt(env.CI_PARALLEL_WORKERS || '2') : true
  },
  
  // Reporter configuration
  reporter: isCI 
    ? ['verbose', 'json', 'html', 'junit']
    : ['verbose', 'html'],
  
  // Output configuration
  outputFile: {
    json: `${env.TEST_RESULTS_DIR || './test-results'}/results.json`,
    html: `${env.TEST_RESULTS_DIR || './test-results'}/report.html`,
    junit: `${env.TEST_RESULTS_DIR || './test-results'}/junit.xml`
  },
  
  // Mock configuration
  mocks: {
    webgl: env.MOCK_WEBGL_CONTEXT === 'true',
    indexeddb: env.MOCK_INDEXEDDB === 'true',
    browserAPIs: env.MOCK_BROWSER_APIS === 'true',
    network: env.MOCK_NETWORK_REQUESTS === 'true'
  },
  
  // Debug configuration
  debug: {
    testSetup: env.DEBUG_TEST_SETUP === 'true',
    mockOperations: env.DEBUG_MOCK_OPERATIONS === 'true',
    cacheOperations: env.DEBUG_CACHE_OPERATIONS === 'true'
  },
  
  // Retry configuration for CI
  retry: isCI ? parseInt(env.CI_RETRY_COUNT || '2') : 0,
  
  // Test patterns
  patterns: {
    unit: ['src/**/*.test.{ts,tsx}', '!src/**/*.integration.test.{ts,tsx}'],
    integration: ['src/**/*.integration.test.{ts,tsx}'],
    all: ['src/**/*.{test,spec}.{ts,tsx}']
  }
}

export default testConfig