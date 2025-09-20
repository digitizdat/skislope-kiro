/**
 * Tests for the test setup infrastructure
 * Verifies that WebGL mocking, IndexedDB mocking, and environment setup work correctly
 */

import { describe, it, expect, beforeEach } from 'vitest';
import * as THREE from 'three';
import {
  createWebGLContextMock,
  isWebGLAvailable,
  isIndexedDBAvailable,
  getTestEnvironmentState,
  ThreeJSTestUtils,
  CacheTestUtils,
  AsyncTestUtils,
  NetworkTestUtils,
  WebGLTestEnvironment,
  WebGLContextMock,
  ThreeJSTerrainMocks,
} from './index';

describe('Test Setup Infrastructure', () => {
  describe('WebGL Context Mock', () => {
    it('should create a valid WebGL context mock', () => {
      const context = createWebGLContextMock();
      
      expect(context).toBeDefined();
      expect(context.canvas).toBeDefined();
      expect(context.drawingBufferWidth).toBe(800);
      expect(context.drawingBufferHeight).toBe(600);
      expect(typeof context.clear).toBe('function');
      expect(typeof context.createShader).toBe('function');
      expect(typeof context.createProgram).toBe('function');
    });
    
    it('should be available in test environment', () => {
      expect(isWebGLAvailable()).toBe(true);
    });
    
    it('should support WebGL constants', () => {
      const context = createWebGLContextMock();
      
      expect(context.VERTEX_SHADER).toBe(35633);
      expect(context.FRAGMENT_SHADER).toBe(35632);
      expect(context.ARRAY_BUFFER).toBe(34962);
      expect(context.TRIANGLES).toBe(4);
    });
  });
  
  describe('IndexedDB Mock', () => {
    it('should be available in test environment', () => {
      expect(isIndexedDBAvailable()).toBe(true);
    });
    
    it('should provide IndexedDB interface', () => {
      expect(window.indexedDB).toBeDefined();
      expect(typeof window.indexedDB.open).toBe('function');
      expect(window.IDBKeyRange).toBeDefined();
    });
  });
  
  describe('Browser API Mocks', () => {
    it('should mock localStorage', () => {
      expect(window.localStorage).toBeDefined();
      expect(typeof window.localStorage.getItem).toBe('function');
      expect(typeof window.localStorage.setItem).toBe('function');
      
      // Test localStorage functionality
      window.localStorage.setItem('test', 'value');
      expect(window.localStorage.getItem('test')).toBe('value');
    });
    
    it('should mock sessionStorage', () => {
      expect(window.sessionStorage).toBeDefined();
      expect(typeof window.sessionStorage.getItem).toBe('function');
      expect(typeof window.sessionStorage.setItem).toBe('function');
    });
    
    it('should mock fetch', () => {
      expect(window.fetch).toBeDefined();
      expect(typeof window.fetch).toBe('function');
    });
  });
  
  describe('Test Environment State', () => {
    it('should provide environment state information', () => {
      const state = getTestEnvironmentState();
      
      expect(state).toBeDefined();
      expect(typeof state.isInitialized).toBe('boolean');
      expect(state.isInitialized).toBe(true);
    });
  });
});

describe('Three.js Test Utils', () => {
  describe('Mock Renderer', () => {
    it('should create a mock WebGL renderer', () => {
      const renderer = ThreeJSTestUtils.createMockRenderer();
      
      expect(renderer).toBeDefined();
      expect(renderer.domElement).toBeDefined();
      expect(renderer.context).toBeDefined();
      expect(typeof renderer.render).toBe('function');
      expect(typeof renderer.setSize).toBe('function');
    });
  });
  
  describe('Mock Scene', () => {
    it('should create a Three.js scene', () => {
      const scene = ThreeJSTestUtils.createMockScene();
      
      expect(scene).toBeDefined();
      expect(scene.type).toBe('Scene');
      expect(Array.isArray(scene.children)).toBe(true);
    });
  });
  
  describe('Mock Camera', () => {
    it('should create a Three.js camera', () => {
      const camera = ThreeJSTestUtils.createMockCamera();
      
      expect(camera).toBeDefined();
      expect(camera.type).toBe('PerspectiveCamera');
      expect(camera.fov).toBe(75);
      expect(camera.position.z).toBe(5);
    });
  });
  
  describe('Complete Test Setup', () => {
    it('should create complete Three.js test setup', () => {
      const setup = ThreeJSTestUtils.createTestSetup();
      
      expect(setup.renderer).toBeDefined();
      expect(setup.scene).toBeDefined();
      expect(setup.camera).toBeDefined();
    });
  });
});

describe('Cache Test Utils', () => {
  let mockCache: any;
  
  beforeEach(() => {
    mockCache = CacheTestUtils.createMockCacheManager();
  });
  
  it('should create a mock cache manager', () => {
    expect(mockCache).toBeDefined();
    expect(mockCache.isInitialized).toBe(true);
    expect(typeof mockCache.get).toBe('function');
    expect(typeof mockCache.set).toBe('function');
  });
  
  it('should support cache operations', async () => {
    await mockCache.set('test-key', 'test-value');
    const value = await mockCache.get('test-key');
    expect(value).toBe('test-value');
  });
  
  it('should support test data setup', async () => {
    const testData = {
      'key1': 'value1',
      'key2': { nested: 'value2' },
    };
    
    await CacheTestUtils.setupTestCache(mockCache, testData);
    
    expect(await mockCache.get('key1')).toBe('value1');
    expect(await mockCache.get('key2')).toEqual({ nested: 'value2' });
  });
});

describe('Async Test Utils', () => {
  it('should wait for conditions', async () => {
    let condition = false;
    
    // Set condition to true after 100ms
    setTimeout(() => {
      condition = true;
    }, 100);
    
    await AsyncTestUtils.waitFor(() => condition, 1000);
    expect(condition).toBe(true);
  });
  
  it('should timeout when condition is not met', async () => {
    await expect(
      AsyncTestUtils.waitFor(() => false, 100)
    ).rejects.toThrow('Condition not met within 100ms');
  });
  
  it('should create deferred promises', () => {
    const deferred = AsyncTestUtils.createDeferred<string>();
    
    expect(deferred.promise).toBeInstanceOf(Promise);
    expect(typeof deferred.resolve).toBe('function');
    expect(typeof deferred.reject).toBe('function');
  });
});

describe('Network Test Utils', () => {
  it('should create mock responses', async () => {
    const mockData = { test: 'data' };
    const response = NetworkTestUtils.createMockResponse(mockData);
    
    expect(response.ok).toBe(true);
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual(mockData);
  });
  
  it('should setup fetch mock with responses', () => {
    const responses = {
      '/api/test': { result: 'success' },
      '/api/error': { error: 'failed' },
    };
    
    const mockFetch = NetworkTestUtils.setupFetchMock(responses);
    
    expect(window.fetch).toBe(mockFetch);
    expect(typeof window.fetch).toBe('function');
  });
});

describe('Enhanced WebGL Mocking Infrastructure', () => {
  describe('WebGLContextMock', () => {
    let webglMock: WebGLContextMock;

    beforeEach(() => {
      webglMock = new WebGLContextMock();
    });

    it('should create a comprehensive WebGL context mock', () => {
      const context = webglMock.getContext();
      const canvas = webglMock.getCanvas();

      expect(context).toBeDefined();
      expect(canvas).toBeDefined();
      expect(canvas.width).toBe(800);
      expect(canvas.height).toBe(600);
      expect(context.drawingBufferWidth).toBe(800);
      expect(context.drawingBufferHeight).toBe(600);
    });

    it('should support shader operations', () => {
      const context = webglMock.getContext();

      const vertexShader = context.createShader(context.VERTEX_SHADER);
      const fragmentShader = context.createShader(context.FRAGMENT_SHADER);

      expect(vertexShader).toBeDefined();
      expect(fragmentShader).toBeDefined();
      expect(typeof context.shaderSource).toBe('function');
      expect(typeof context.compileShader).toBe('function');
    });

    it('should support buffer operations', () => {
      const context = webglMock.getContext();

      const buffer = context.createBuffer();
      expect(buffer).toBeDefined();

      context.bindBuffer(context.ARRAY_BUFFER, buffer);
      const testData = new Float32Array([1, 2, 3, 4]);
      context.bufferData(context.ARRAY_BUFFER, testData, context.STATIC_DRAW);

      expect(context.bindBuffer).toHaveBeenCalledWith(context.ARRAY_BUFFER, buffer);
      expect(context.bufferData).toHaveBeenCalledWith(context.ARRAY_BUFFER, testData, context.STATIC_DRAW);
    });

    it('should support texture operations', () => {
      const context = webglMock.getContext();

      const texture = context.createTexture();
      expect(texture).toBeDefined();

      context.bindTexture(context.TEXTURE_2D, texture);
      expect(context.bindTexture).toHaveBeenCalledWith(context.TEXTURE_2D, texture);
    });

    it('should track WebGL state', () => {
      const context = webglMock.getContext();

      context.enable(context.DEPTH_TEST);
      context.disable(context.BLEND);

      const state = webglMock.getState();
      expect(state).toBeDefined();
      expect(typeof state.programs).toBe('number');
      expect(typeof state.buffers).toBe('number');
      expect(typeof state.textures).toBe('number');
    });

    it('should reset properly', () => {
      const context = webglMock.getContext();

      // Create some resources
      context.createBuffer();
      context.createTexture();
      context.createShader(context.VERTEX_SHADER);

      const stateBefore = webglMock.getState();
      expect(stateBefore.buffers).toBeGreaterThan(0);
      expect(stateBefore.textures).toBeGreaterThan(0);
      expect(stateBefore.shaders).toBeGreaterThan(0);

      webglMock.reset();

      const stateAfter = webglMock.getState();
      expect(stateAfter.buffers).toBe(0);
      expect(stateAfter.textures).toBe(0);
      expect(stateAfter.shaders).toBe(0);
    });
  });

  describe('ThreeJSTerrainMocks', () => {
    let webglMock: WebGLContextMock;
    let terrainMocks: ThreeJSTerrainMocks;

    beforeEach(() => {
      webglMock = new WebGLContextMock();
      terrainMocks = new ThreeJSTerrainMocks(webglMock);
    });

    it('should create terrain renderer with WebGL context', () => {
      const renderer = terrainMocks.createTerrainRenderer();

      expect(renderer).toBeDefined();
      expect(renderer.domElement).toBeDefined();
      expect(renderer.context).toBeDefined();
      expect(typeof renderer.render).toBe('function');
      expect(typeof renderer.setSize).toBe('function');
    });

    it('should create mock terrain geometry', () => {
      const geometry = terrainMocks.createMockTerrainGeometry(16, 16);

      expect(geometry).toBeDefined();
      expect(geometry.attributes.position).toBeDefined();
      expect(geometry.attributes.normal).toBeDefined();
      expect(geometry.attributes.uv).toBeDefined();
      expect(geometry.index).toBeDefined();

      // Validate terrain geometry structure
      expect(ThreeJSTestUtils.validateTerrainGeometry(geometry)).toBe(true);
    });

    it('should create mock terrain materials', () => {
      const materials = terrainMocks.createMockTerrainMaterials();

      expect(materials).toBeDefined();
      expect(Array.isArray(materials)).toBe(true);
      expect(materials.length).toBeGreaterThan(0);

      materials.forEach(material => {
        expect(material).toBeDefined();
        expect(material.type).toBeDefined();
      });
    });
  });

  describe('WebGLTestEnvironment', () => {
    it('should be a singleton', () => {
      const env1 = WebGLTestEnvironment.getInstance();
      const env2 = WebGLTestEnvironment.getInstance();

      expect(env1).toBe(env2);
    });

    it('should provide WebGL and terrain mocks', () => {
      const env = WebGLTestEnvironment.getInstance();

      const webglMock = env.getWebGLMock();
      const terrainMocks = env.getTerrainMocks();

      expect(webglMock).toBeDefined();
      expect(terrainMocks).toBeDefined();
      expect(webglMock).toBeInstanceOf(WebGLContextMock);
      expect(terrainMocks).toBeInstanceOf(ThreeJSTerrainMocks);
    });

    it('should setup and teardown properly', () => {
      const env = WebGLTestEnvironment.getInstance();

      // Setup should not throw
      expect(() => env.setup()).not.toThrow();

      // Teardown should not throw
      expect(() => env.teardown()).not.toThrow();
    });
  });
});

describe('Enhanced Three.js Test Utils', () => {
  describe('Terrain-specific utilities', () => {
    it('should create terrain test setup', () => {
      const setup = ThreeJSTestUtils.createTerrainTestSetup(32, 32);

      expect(setup.renderer).toBeDefined();
      expect(setup.scene).toBeDefined();
      expect(setup.camera).toBeDefined();
      expect(setup.terrainGeometry).toBeDefined();
      expect(setup.terrainMaterials).toBeDefined();
      expect(setup.terrainMesh).toBeDefined();

      // Validate terrain geometry
      expect(ThreeJSTestUtils.validateTerrainGeometry(setup.terrainGeometry)).toBe(true);
    });

    it('should validate terrain geometry correctly', () => {
      const validGeometry = ThreeJSTestUtils.createMockTerrainGeometry(16, 16);
      const invalidGeometry = new THREE.BufferGeometry();

      expect(ThreeJSTestUtils.validateTerrainGeometry(validGeometry)).toBe(true);
      expect(ThreeJSTestUtils.validateTerrainGeometry(invalidGeometry)).toBe(false);
    });

    it('should mock terrain rendering operations', () => {
      const setup = ThreeJSTestUtils.createTerrainTestSetup();
      
      // Add terrain mesh to scene
      setup.scene.add(setup.terrainMesh);

      // Mock rendering should not throw
      expect(() => {
        ThreeJSTestUtils.mockTerrainRender(setup.renderer, setup.scene, setup.camera);
      }).not.toThrow();

      // Verify render was called
      expect(setup.renderer.render).toHaveBeenCalledWith(setup.scene, setup.camera);
    });
  });
});