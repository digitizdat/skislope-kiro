/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    // Environment configuration
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    
    // Timeout settings for reliable test execution
    timeout: 10000,        // Global timeout for test suites
    testTimeout: 5000,     // Individual test timeout
    hookTimeout: 10000,    // Setup/teardown timeout
    
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
    
    // Coverage configuration with appropriate thresholds
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
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
        'vitest.config.ts'
      ],
      threshold: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80
      },
      // Fail tests if coverage is below threshold
      thresholdAutoUpdate: false,
      skipFull: false
    },
    
    // Reporter configuration for clear feedback
    reporter: ['verbose', 'json', 'html'],
    outputFile: {
      json: './test-results/results.json',
      html: './test-results/report.html'
    },
    
    // Test file patterns and filtering support
    include: [
      'src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
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
      VITEST: 'true'
    }
  },
  
  // Resolve configuration to match production build
  resolve: {
    alias: {
      '@': '/src',
      '@/components': '/src/components',
      '@/managers': '/src/managers',
      '@/services': '/src/services',
      '@/stores': '/src/stores',
      '@/models': '/src/models',
      '@/utils': '/src/utils'
    }
  }
})