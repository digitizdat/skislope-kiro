/**
 * Test setup file for vitest
 * Integrates with core test setup infrastructure for comprehensive testing environment
 */

import { expect, beforeAll, afterEach, afterAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'
import { 
  initializeTestEnvironment, 
  teardownTestEnvironment, 
  resetTestEnvironment 
} from './testSetup'
import { WebGLTestEnvironment } from './webglMocks'

// extends Vitest's expect
expect.extend(matchers)

// Initialize test environment before all tests
beforeAll(async () => {
  // Setup WebGL test environment first
  const webglEnv = WebGLTestEnvironment.getInstance()
  webglEnv.setup()
  
  // Then initialize the rest of the test environment
  await initializeTestEnvironment()
})

// Reset environment state between tests
afterEach(() => {
  // Clean up React components
  cleanup()
  
  // Reset WebGL test environment
  WebGLTestEnvironment.reset()
  
  // Reset test environment state
  resetTestEnvironment()
})

// Clean up test environment after all tests
afterAll(async () => {
  // Teardown WebGL test environment
  WebGLTestEnvironment.teardownAll()
  
  // Teardown the rest of the test environment
  await teardownTestEnvironment()
})