/// <reference types="vitest" />
import { defineConfig } from 'vite'

// Load test configuration from environment
const isCI = process.env.CI === 'true' || process.env.GITHUB_ACTIONS === 'true'
const ciMultiplier = isCI ? 1.5 : 1

export default defineConfig({
  test: {
    // Use Node environment for integration tests to support real network calls
    environment: 'node',
    
    // Timeout settings for reliable test execution (adjusted for CI)
    timeout: Math.floor((parseInt(process.env.VITEST_TIMEOUT) || 30000) * ciMultiplier),
    testTimeout: Math.floor((parseInt(process.env.VITEST_TEST_TIMEOUT) || 15000) * ciMultiplier),
    hookTimeout: Math.floor((parseInt(process.env.VITEST_HOOK_TIMEOUT) || 10000) * ciMultiplier),
    
    // Test isolation and parallel execution
    isolate: true,         // Isolate test environments
    pool: 'threads',       // Use worker threads for parallel execution
    poolOptions: {
      threads: {
        singleThread: false,  // Enable parallel execution
        isolate: true,        // Ensure test isolation
        useAtomics: true,     // Use atomic operations for thread safety
      }
    },
    
    // Reporter configuration for clear feedback
    reporter: ['verbose'],
    
    // Test file patterns - only integration tests
    include: [
      'src/**/*.integration.test.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
    ],
    exclude: [
      'node_modules/**',
      'dist/**',
      '.git/**',
      '.vscode/**',
      'coverage/**'
    ],
    
    // Performance and debugging options
    logHeapUsage: true,     // Monitor memory usage
    allowOnly: true,        // Allow test.only in development
    passWithNoTests: false, // Fail if no tests found
    
    // Environment variables for consistent configuration
    env: {
      NODE_ENV: 'test',
      VITEST: 'true',
      INTEGRATION_TEST: 'true',
      CI: process.env.CI || 'false',
    },
    
    // Retry configuration for flaky tests in CI
    retry: isCI ? (parseInt(process.env.CI_RETRY_COUNT) || 2) : 0
  }
})