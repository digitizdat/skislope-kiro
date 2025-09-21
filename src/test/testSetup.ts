/**
 * Core test setup infrastructure for frontend testing environment
 * Provides WebGL context mocking, environment initialization, and cleanup utilities
 */

import { vi } from 'vitest';
import { createCanvas } from 'canvas';
// Use the main fake-indexeddb module
import 'fake-indexeddb/auto';

// Global test state management
interface TestEnvironmentState {
  webglContext: WebGLRenderingContext | null;
  canvas: HTMLCanvasElement | null;
  indexedDB: IDBFactory | null;
  originalAPIs: Map<string, any>;
  isInitialized: boolean;
}

const testState: TestEnvironmentState = {
  webglContext: null,
  canvas: null,
  indexedDB: null,
  originalAPIs: new Map(),
  isInitialized: false
};

/**
 * WebGL Context Mock Creation
 * Creates a mock WebGL context using the canvas package for headless testing
 */
export function createWebGLContextMock(): WebGLRenderingContext {
  // Create a canvas using the node-canvas package
  const canvas = createCanvas(800, 600);
  
  // Mock WebGL context with essential methods for Three.js
  const mockContext = {
    canvas,
    drawingBufferWidth: 800,
    drawingBufferHeight: 600,
    
    // WebGL state management
    enable: vi.fn(),
    disable: vi.fn(),
    clear: vi.fn(),
    clearColor: vi.fn(),
    clearDepth: vi.fn(),
    viewport: vi.fn(),
    
    // Shader operations
    createShader: vi.fn(() => ({})),
    shaderSource: vi.fn(),
    compileShader: vi.fn(),
    getShaderParameter: vi.fn(() => true),
    createProgram: vi.fn(() => ({})),
    attachShader: vi.fn(),
    linkProgram: vi.fn(),
    getProgramParameter: vi.fn(() => true),
    useProgram: vi.fn(),
    
    // Buffer operations
    createBuffer: vi.fn(() => ({})),
    bindBuffer: vi.fn(),
    bufferData: vi.fn(),
    
    // Texture operations
    createTexture: vi.fn(() => ({})),
    bindTexture: vi.fn(),
    texImage2D: vi.fn(),
    texParameteri: vi.fn(),
    generateMipmap: vi.fn(),
    
    // Attribute and uniform operations
    getAttribLocation: vi.fn(() => 0),
    getUniformLocation: vi.fn(() => ({})),
    enableVertexAttribArray: vi.fn(),
    vertexAttribPointer: vi.fn(),
    uniform1f: vi.fn(),
    uniform1i: vi.fn(),
    uniform2f: vi.fn(),
    uniform3f: vi.fn(),
    uniform4f: vi.fn(),
    uniformMatrix4fv: vi.fn(),
    
    // Drawing operations
    drawArrays: vi.fn(),
    drawElements: vi.fn(),
    
    // WebGL constants
    VERTEX_SHADER: 35633,
    FRAGMENT_SHADER: 35632,
    ARRAY_BUFFER: 34962,
    ELEMENT_ARRAY_BUFFER: 34963,
    STATIC_DRAW: 35044,
    TEXTURE_2D: 3553,
    RGBA: 6408,
    UNSIGNED_BYTE: 5121,
    TEXTURE_MAG_FILTER: 10240,
    TEXTURE_MIN_FILTER: 10241,
    LINEAR: 9729,
    TRIANGLES: 4,
    DEPTH_TEST: 2929,
    COLOR_BUFFER_BIT: 16384,
    DEPTH_BUFFER_BIT: 256,
    
    // Extension support
    getExtension: vi.fn(() => null),
    getSupportedExtensions: vi.fn(() => []),
    
    // Error handling
    getError: vi.fn(() => 0), // GL_NO_ERROR
    
    // Additional WebGL methods that Three.js might use
    deleteBuffer: vi.fn(),
    deleteTexture: vi.fn(),
    deleteProgram: vi.fn(),
    deleteShader: vi.fn(),
    isBuffer: vi.fn(() => true),
    isTexture: vi.fn(() => true),
    isProgram: vi.fn(() => true),
    isShader: vi.fn(() => true),
    
    // WebGL 2.0 methods (for compatibility)
    createVertexArray: vi.fn(() => ({})),
    bindVertexArray: vi.fn(),
    deleteVertexArray: vi.fn(),
  } as unknown as WebGLRenderingContext;
  
  return mockContext;
}

/**
 * Setup WebGL environment for testing
 * Mocks HTMLCanvasElement and WebGL context creation
 */
export function setupWebGLEnvironment(): void {
  // Store original APIs
  if (typeof window !== 'undefined') {
    testState.originalAPIs.set('HTMLCanvasElement', window.HTMLCanvasElement);
  }
  
  // Create mock canvas element factory
  const createMockCanvas = () => {
    const canvas = {
      width: 800,
      height: 600,
      getContext: vi.fn((contextType: string) => {
        if (contextType === 'webgl' || contextType === 'experimental-webgl') {
          if (!testState.webglContext) {
            testState.webglContext = createWebGLContextMock();
          }
          // Always set the canvas property to point back to this specific canvas
          (testState.webglContext as any).canvas = canvas;
          return testState.webglContext;
        }
        return null;
      }),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      getBoundingClientRect: vi.fn(() => ({
        left: 0,
        top: 0,
        width: 800,
        height: 600,
        right: 800,
        bottom: 600,
        x: 0,
        y: 0,
        toJSON: () => ({})
      })),
      style: {},
      clientWidth: 800,
      clientHeight: 600,
      offsetWidth: 800,
      offsetHeight: 600,
    } as unknown as HTMLCanvasElement;
    return canvas;
  };

  const mockCanvas = createMockCanvas();

  
  testState.canvas = mockCanvas;
  
  // Mock document.createElement for canvas
  if (typeof document !== 'undefined') {
    const originalCreateElement = document.createElement;
    testState.originalAPIs.set('createElement', originalCreateElement);
    
    document.createElement = vi.fn((tagName: string) => {
      if (tagName.toLowerCase() === 'canvas') {
        return createMockCanvas();
      }
      return originalCreateElement.call(document, tagName);
    }) as any;
  }
}

/**
 * Setup IndexedDB mock for CacheManager testing
 */
export function setupIndexedDBMock(): void {
  // fake-indexeddb/auto should have already set up the globals
  if (typeof window !== 'undefined') {
    // Store original IndexedDB if it exists
    if (window.indexedDB) {
      testState.originalAPIs.set('indexedDB', window.indexedDB);
    }
    if (window.IDBKeyRange) {
      testState.originalAPIs.set('IDBKeyRange', window.IDBKeyRange);
    }
    testState.indexedDB = window.indexedDB;
  }
  
  if (typeof globalThis !== 'undefined' && (globalThis as any).indexedDB) {
    testState.indexedDB = (globalThis as any).indexedDB;
  }
}

/**
 * Setup comprehensive browser API mocks
 */
export async function setupBrowserAPIMocks(): Promise<void> {
  // Store original APIs for restoration
  if (typeof globalThis !== 'undefined') {
    testState.originalAPIs.set('localStorage', globalThis.localStorage);
    testState.originalAPIs.set('sessionStorage', globalThis.sessionStorage);
    testState.originalAPIs.set('fetch', globalThis.fetch);
    testState.originalAPIs.set('XMLHttpRequest', globalThis.XMLHttpRequest);
    testState.originalAPIs.set('AudioContext', globalThis.AudioContext);
    testState.originalAPIs.set('webkitAudioContext', (globalThis as any).webkitAudioContext);
    testState.originalAPIs.set('OfflineAudioContext', globalThis.OfflineAudioContext);
    testState.originalAPIs.set('Blob', globalThis.Blob);
    testState.originalAPIs.set('File', globalThis.File);
    testState.originalAPIs.set('URL', globalThis.URL);
    
    // Store the original fetch in a special location for integration tests
    if (globalThis.fetch) {
      (globalThis as any).__originalFetch = globalThis.fetch;
    }
  }
  
  // Try to use comprehensive browser API mocks first, fallback to simple mocks
  try {
    const { installBrowserAPIMocks } = await import('./browserAPIMocks');
    const mocks = installBrowserAPIMocks();
    testState.originalAPIs.set('browserAPIMocks', mocks);
    testState.originalAPIs.set('mockType', 'comprehensive');
    console.log('Comprehensive browser API mocks installed');
  } catch (error) {
    console.warn('Failed to install comprehensive mocks, falling back to simple mocks:', error);
    
    // Fallback to simple browser API mocks
    const { installSimpleBrowserMocks } = await import('./simpleBrowserMocks');
    const mocks = installSimpleBrowserMocks();
    testState.originalAPIs.set('browserAPIMocks', mocks);
    testState.originalAPIs.set('mockType', 'simple');
    console.log('Simple browser API mocks installed');
  }
}

/**
 * Initialize complete test environment
 */
export async function initializeTestEnvironment(): Promise<void> {
  if (testState.isInitialized) {
    return;
  }
  
  try {
    // Setup all mock environments
    setupWebGLEnvironment();
    setupIndexedDBMock();
    await setupBrowserAPIMocks();
    
    // Ensure WebGL context is created
    if (!testState.webglContext) {
      testState.webglContext = createWebGLContextMock();
    }
    
    // Initialize CacheManager for tests that need it with timeout
    try {
      const { cacheManager } = await import('../utils/CacheManager');
      
      // Use a timeout for CacheManager initialization to prevent hanging
      const initPromise = cacheManager.initialize();
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('CacheManager initialization timeout')), 5000);
      });
      
      await Promise.race([initPromise, timeoutPromise]);
      console.log('CacheManager initialized for tests');
    } catch (error) {
      console.warn('Could not initialize CacheManager in test environment:', error);
      // Don't fail the test setup if CacheManager fails to initialize
    }
    
    // Mark as initialized
    testState.isInitialized = true;
    
    console.log('Test environment initialized successfully');
  } catch (error) {
    console.error('Failed to initialize test environment:', error);
    throw error;
  }
}

/**
 * Cleanup and teardown test environment
 */
export async function teardownTestEnvironment(): Promise<void> {
  try {
    // Close CacheManager if it was initialized with timeout
    try {
      const { cacheManager } = await import('../utils/CacheManager');
      
      // Use a timeout for CacheManager close to prevent hanging
      const closePromise = cacheManager.close();
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('CacheManager close timeout')), 3000);
      });
      
      await Promise.race([closePromise, timeoutPromise]);
      console.log('CacheManager closed');
    } catch (error) {
      console.warn('Could not close CacheManager:', error);
    }
    
    // Reset WebGL context
    if (testState.webglContext) {
      // Clear any WebGL state if needed
      testState.webglContext = null;
    }
    
    // Reset canvas
    testState.canvas = null;
    
    // Reset IndexedDB
    if (testState.indexedDB && typeof testState.indexedDB.deleteDatabase === 'function') {
      // Clear any test databases
      testState.indexedDB = null;
    }
    
    // Restore original APIs
    if (typeof globalThis !== 'undefined') {
      for (const [key, originalValue] of testState.originalAPIs) {
        switch (key) {
          case 'HTMLCanvasElement':
            if (typeof window !== 'undefined') {
              window.HTMLCanvasElement = originalValue;
            }
            break;
          case 'createElement':
            if (typeof document !== 'undefined') {
              document.createElement = originalValue;
            }
            break;
          case 'indexedDB':
            if (originalValue) {
              Object.defineProperty(globalThis, 'indexedDB', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'IDBKeyRange':
            if (originalValue) {
              Object.defineProperty(globalThis, 'IDBKeyRange', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'localStorage':
            if (originalValue) {
              Object.defineProperty(globalThis, 'localStorage', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'sessionStorage':
            if (originalValue) {
              Object.defineProperty(globalThis, 'sessionStorage', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'fetch':
            if (originalValue) {
              Object.defineProperty(globalThis, 'fetch', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'XMLHttpRequest':
            if (originalValue) {
              Object.defineProperty(globalThis, 'XMLHttpRequest', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'AudioContext':
            if (originalValue) {
              Object.defineProperty(globalThis, 'AudioContext', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'webkitAudioContext':
            if (originalValue) {
              Object.defineProperty(globalThis, 'webkitAudioContext', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'OfflineAudioContext':
            if (originalValue) {
              Object.defineProperty(globalThis, 'OfflineAudioContext', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'Blob':
            if (originalValue) {
              Object.defineProperty(globalThis, 'Blob', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'File':
            if (originalValue) {
              Object.defineProperty(globalThis, 'File', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'URL':
            if (originalValue) {
              Object.defineProperty(globalThis, 'URL', {
                value: originalValue,
                writable: true,
                configurable: true,
              });
            }
            break;
          case 'browserAPIMocks':
            // Skip - this is our internal reference
            break;
        }
      }
    }
    
    // Clear stored APIs
    testState.originalAPIs.clear();
    
    // Mark as not initialized
    testState.isInitialized = false;
    
    console.log('Test environment cleaned up successfully');
  } catch (error) {
    console.error('Failed to cleanup test environment:', error);
    throw error;
  }
}

/**
 * Reset test environment between tests
 */
export async function resetTestEnvironment(): Promise<void> {
  // Reset WebGL context state
  if (testState.webglContext) {
    // Reset any stateful mocks
    Object.values(testState.webglContext).forEach(method => {
      if (typeof method === 'function' && 'mockClear' in method) {
        (method as any).mockClear();
      }
    });
  }
  
  // Reset browser API mocks based on type
  const browserAPIMocks = testState.originalAPIs.get('browserAPIMocks');
  const mockType = testState.originalAPIs.get('mockType');
  
  if (browserAPIMocks) {
    if (mockType === 'comprehensive') {
      try {
        const { resetBrowserAPIMocks } = await import('./browserAPIMocks');
        resetBrowserAPIMocks(browserAPIMocks);
      } catch (error) {
        console.warn('Failed to reset comprehensive mocks:', error);
      }
    } else {
      try {
        const { resetSimpleBrowserMocks } = await import('./simpleBrowserMocks');
        resetSimpleBrowserMocks(browserAPIMocks);
      } catch (error) {
        console.warn('Failed to reset simple mocks:', error);
      }
    }
  }
  
  // Reset IndexedDB mock state
  if (testState.indexedDB) {
    // Create fresh IndexedDB instance
    setupIndexedDBMock();
  }
}

/**
 * Get current test environment state (for debugging)
 */
export function getTestEnvironmentState(): TestEnvironmentState {
  return { ...testState };
}

/**
 * Utility to check if WebGL context is available in test
 */
export function isWebGLAvailable(): boolean {
  return testState.webglContext !== null;
}

/**
 * Utility to check if IndexedDB is available in test
 */
export function isIndexedDBAvailable(): boolean {
  return testState.indexedDB !== null;
}