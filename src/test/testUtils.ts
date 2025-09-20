/**
 * Test utilities for common testing patterns and scenarios
 */

import { vi } from 'vitest';
import * as THREE from 'three';
import { createWebGLContextMock } from './testSetup';
import { WebGLTestEnvironment } from './webglMocks';

/**
 * Three.js test utilities
 */
export class ThreeJSTestUtils {
  /**
   * Create a mock Three.js renderer for testing
   * Uses the enhanced WebGL mocking infrastructure
   */
  static createMockRenderer(): THREE.WebGLRenderer {
    const webglEnv = WebGLTestEnvironment.getInstance();
    const terrainMocks = webglEnv.getTerrainMocks();
    return terrainMocks.createTerrainRenderer();
  }

  /**
   * Create a mock Three.js renderer with basic functionality (legacy)
   */
  static createBasicMockRenderer(): THREE.WebGLRenderer {
    const mockContext = createWebGLContextMock();
    const mockCanvas = mockContext.canvas as HTMLCanvasElement;
    
    // Mock the WebGLRenderer constructor
    const mockRenderer = {
      domElement: mockCanvas,
      context: mockContext,
      capabilities: {
        isWebGL2: false,
        precision: 'highp',
        logarithmicDepthBuffer: false,
        maxTextures: 16,
        maxVertexTextures: 4,
        maxTextureSize: 2048,
        maxCubemapSize: 1024,
        maxAttributes: 16,
        maxVertexUniforms: 1024,
        maxVaryings: 8,
        maxFragmentUniforms: 1024,
        vertexTextures: true,
        floatFragmentTextures: true,
        floatVertexTextures: true,
      },
      
      // Rendering methods
      render: vi.fn(),
      setSize: vi.fn(),
      setPixelRatio: vi.fn(),
      setClearColor: vi.fn(),
      clear: vi.fn(),
      
      // State management
      setViewport: vi.fn(),
      setScissor: vi.fn(),
      setScissorTest: vi.fn(),
      
      // Disposal
      dispose: vi.fn(),
      
      // Properties
      shadowMap: {
        enabled: false,
        type: THREE.PCFShadowMap,
      },
      
      // Info
      info: {
        memory: {
          geometries: 0,
          textures: 0,
        },
        render: {
          frame: 0,
          calls: 0,
          triangles: 0,
          points: 0,
          lines: 0,
        },
        programs: [],
      },
    } as unknown as THREE.WebGLRenderer;
    
    return mockRenderer;
  }
  
  /**
   * Create a mock Three.js scene for testing
   */
  static createMockScene(): THREE.Scene {
    const scene = new THREE.Scene();
    
    // Add some basic properties that tests might expect
    scene.background = null;
    scene.fog = null;
    
    return scene;
  }
  
  /**
   * Create a mock Three.js camera for testing
   */
  static createMockCamera(): THREE.PerspectiveCamera {
    const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    camera.position.set(0, 0, 5);
    return camera;
  }
  
  /**
   * Create a complete Three.js test setup
   */
  static createTestSetup() {
    return {
      renderer: this.createMockRenderer(),
      scene: this.createMockScene(),
      camera: this.createMockCamera(),
    };
  }

  /**
   * Create mock terrain geometry for testing
   */
  static createMockTerrainGeometry(width: number = 32, height: number = 32): THREE.BufferGeometry {
    const webglEnv = WebGLTestEnvironment.getInstance();
    const terrainMocks = webglEnv.getTerrainMocks();
    return terrainMocks.createMockTerrainGeometry(width, height);
  }

  /**
   * Create mock terrain materials for testing
   */
  static createMockTerrainMaterials(): THREE.Material[] {
    const webglEnv = WebGLTestEnvironment.getInstance();
    const terrainMocks = webglEnv.getTerrainMocks();
    return terrainMocks.createMockTerrainMaterials();
  }

  /**
   * Create a complete terrain test setup with geometry and materials
   */
  static createTerrainTestSetup(gridWidth: number = 32, gridHeight: number = 32) {
    const setup = this.createTestSetup();
    const geometry = this.createMockTerrainGeometry(gridWidth, gridHeight);
    const materials = this.createMockTerrainMaterials();
    
    return {
      ...setup,
      terrainGeometry: geometry,
      terrainMaterials: materials,
      terrainMesh: new THREE.Mesh(geometry, materials[0]),
    };
  }

  /**
   * Validate Three.js geometry for terrain rendering
   */
  static validateTerrainGeometry(geometry: THREE.BufferGeometry): boolean {
    // Check required attributes
    const hasPosition = geometry.attributes.position !== undefined;
    const hasNormal = geometry.attributes.normal !== undefined;
    const hasUV = geometry.attributes.uv !== undefined;
    const hasIndex = geometry.index !== null;

    // Check attribute sizes
    const positionValid = hasPosition && geometry.attributes.position.itemSize === 3;
    const normalValid = hasNormal && geometry.attributes.normal.itemSize === 3;
    const uvValid = hasUV && geometry.attributes.uv.itemSize === 2;

    return hasPosition && hasNormal && hasUV && hasIndex && 
           positionValid && normalValid && uvValid;
  }

  /**
   * Mock WebGL rendering operations for terrain
   */
  static mockTerrainRender(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera): void {
    // Simulate the rendering process
    if (renderer.render && typeof renderer.render === 'function') {
      renderer.render(scene, camera);
    }

    // Update renderer info to simulate rendering
    if (renderer.info) {
      renderer.info.render.frame++;
      renderer.info.render.calls++;
      
      // Count triangles from scene meshes
      let triangles = 0;
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh && object.geometry) {
          const geometry = object.geometry;
          if (geometry.index) {
            triangles += geometry.index.count / 3;
          } else if (geometry.attributes.position) {
            triangles += geometry.attributes.position.count / 3;
          }
        }
      });
      renderer.info.render.triangles = triangles;
    }
  }
}

/**
 * Cache Manager test utilities
 */
export class CacheTestUtils {
  /**
   * Create a mock CacheManager instance
   */
  static createMockCacheManager() {
    const mockStorage = new Map<string, any>();
    
    return {
      isInitialized: true,
      
      async get(key: string) {
        return mockStorage.get(key);
      },
      
      async set(key: string, value: any) {
        mockStorage.set(key, value);
      },
      
      async delete(key: string) {
        return mockStorage.delete(key);
      },
      
      async clear() {
        mockStorage.clear();
      },
      
      async initialize() {
        // Mock initialization
        return Promise.resolve();
      },
      
      // Test utilities
      _getMockStorage() {
        return mockStorage;
      },
      
      _reset() {
        mockStorage.clear();
      },
    };
  }
  
  /**
   * Setup cache with test data
   */
  static async setupTestCache(cacheManager: any, testData: Record<string, any>) {
    for (const [key, value] of Object.entries(testData)) {
      await cacheManager.set(key, value);
    }
  }
}

/**
 * Deferred promise utility for testing
 */
export class DeferredPromiseUtils {
  /**
   * Create a deferred promise for testing
   */
  static createDeferred<T>() {
    let resolve: (value: T) => void;
    let reject: (reason?: any) => void;
    
    const promise = new Promise<T>((res, rej) => {
      resolve = res;
      reject = rej;
    });
    
    return {
      promise,
      resolve: resolve!,
      reject: reject!,
    };
  }
}

/**
 * Network mock utilities
 */
export class NetworkTestUtils {
  /**
   * Create a mock fetch response
   */
  static createMockResponse(data: any, options: Partial<Response> = {}): Response {
    return {
      ok: true,
      status: 200,
      statusText: 'OK',
      headers: new Headers(),
      json: () => Promise.resolve(data),
      text: () => Promise.resolve(JSON.stringify(data)),
      blob: () => Promise.resolve(new Blob([JSON.stringify(data)])),
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
      clone: () => NetworkTestUtils.createMockResponse(data, options),
      body: null,
      bodyUsed: false,
      redirected: false,
      type: 'basic',
      url: '',
      ...options,
    } as Response;
  }
  
  /**
   * Setup fetch mock with predefined responses
   */
  static setupFetchMock(responses: Record<string, any>) {
    const mockFetch = vi.fn((url: RequestInfo | URL, _init?: RequestInit) => {
      const urlString = typeof url === 'string' ? url : url instanceof URL ? url.toString() : (url as Request).url;
      
      for (const [pattern, response] of Object.entries(responses)) {
        if (urlString.includes(pattern)) {
          return Promise.resolve(this.createMockResponse(response));
        }
      }
      
      // Default response
      return Promise.resolve(this.createMockResponse({}));
    });
    
    if (typeof window !== 'undefined') {
      (window as any).fetch = mockFetch;
    }
    
    return mockFetch;
  }
}

/**
 * Error testing utilities
 */
export class ErrorTestUtils {
  /**
   * Test that a function throws an error
   */
  static async expectToThrow(
    fn: () => Promise<any> | any,
    expectedError?: string | RegExp | Error
  ): Promise<void> {
    let error: Error | null = null;
    
    try {
      await fn();
    } catch (e) {
      error = e as Error;
    }
    
    if (!error) {
      throw new Error('Expected function to throw an error, but it did not');
    }
    
    if (expectedError) {
      if (typeof expectedError === 'string') {
        if (!error.message.includes(expectedError)) {
          throw new Error(`Expected error message to contain "${expectedError}", but got "${error.message}"`);
        }
      } else if (expectedError instanceof RegExp) {
        if (!expectedError.test(error.message)) {
          throw new Error(`Expected error message to match ${expectedError}, but got "${error.message}"`);
        }
      } else if (expectedError instanceof Error) {
        if (error.constructor !== expectedError.constructor) {
          throw new Error(`Expected error type ${expectedError.constructor.name}, but got ${error.constructor.name}`);
        }
      }
    }
  }
}

/**
 * Performance testing utilities
 */
export class PerformanceTestUtils {
  /**
   * Measure execution time of a function
   */
  static async measureTime<T>(fn: () => Promise<T> | T): Promise<{ result: T; duration: number }> {
    const startTime = performance.now();
    const result = await fn();
    const endTime = performance.now();
    
    return {
      result,
      duration: endTime - startTime,
    };
  }
  
  /**
   * Assert that a function executes within a time limit
   */
  static async expectWithinTime<T>(
    fn: () => Promise<T> | T,
    maxDuration: number
  ): Promise<T> {
    const { result, duration } = await this.measureTime(fn);
    
    if (duration > maxDuration) {
      throw new Error(`Function took ${duration}ms, expected less than ${maxDuration}ms`);
    }
    
    return result;
  }
}