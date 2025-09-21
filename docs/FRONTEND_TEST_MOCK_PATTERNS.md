# Frontend Test Mock Usage Patterns and Best Practices

## Overview

This guide provides comprehensive patterns and best practices for using mocks in the Alpine Ski Simulator frontend test environment. It covers when to use different types of mocks, how to implement them effectively, and common patterns for testing various scenarios.

## Table of Contents

1. [Mock Types and When to Use Them](#mock-types-and-when-to-use-them)
2. [WebGL and Three.js Mocking Patterns](#webgl-and-threejs-mocking-patterns)
3. [CacheManager Mocking Patterns](#cachemanager-mocking-patterns)
4. [Browser API Mocking Patterns](#browser-api-mocking-patterns)
5. [Network Request Mocking Patterns](#network-request-mocking-patterns)
6. [Async Operation Mocking Patterns](#async-operation-mocking-patterns)
7. [Service and Component Mocking Patterns](#service-and-component-mocking-patterns)
8. [Error Simulation Patterns](#error-simulation-patterns)
9. [Performance Testing Patterns](#performance-testing-patterns)
10. [Integration Testing Patterns](#integration-testing-patterns)

## Mock Types and When to Use Them

### Unit Test Mocks
Use for testing individual functions or classes in isolation.

```typescript
import { vi } from 'vitest';
import { TerrainService } from './TerrainService';

describe('TerrainService Unit Tests', () => {
  it('should process elevation data', () => {
    const terrainService = new TerrainService();
    
    // Mock external dependencies
    const mockCacheManager = {
      getCachedTerrainData: vi.fn().mockResolvedValue(null),
      cacheTerrainData: vi.fn().mockResolvedValue(undefined)
    };
    
    // Inject mock
    terrainService.setCacheManager(mockCacheManager);
    
    // Test the unit
    const result = terrainService.processElevationData([100, 200, 300]);
    expect(result).toHaveLength(3);
  });
});
```

### Integration Test Mocks
Use for testing interactions between components with minimal mocking.

```typescript
import { initializeTestEnvironment } from '../test/testSetup';
import { TerrainService } from './TerrainService';
import { CacheManager } from '../utils/CacheManager';

describe('TerrainService Integration Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment(); // Real CacheManager, mocked browser APIs
  });

  it('should integrate with CacheManager', async () => {
    const terrainService = new TerrainService();
    
    // Use real CacheManager with mocked IndexedDB
    const result = await terrainService.loadTerrainData('test-run');
    expect(result).toBeDefined();
  });
});
```

### End-to-End Test Mocks
Use for testing complete user workflows with minimal mocking.

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { initializeTestEnvironment } from '../test/testSetup';
import App from './App';

describe('E2E Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should complete terrain loading workflow', async () => {
    render(<App />);
    
    // Mock only external APIs, use real components
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ elevation: [1, 2, 3] })
    });
    
    fireEvent.click(screen.getByText('Load Terrain'));
    
    await waitFor(() => {
      expect(screen.getByText('Terrain Loaded')).toBeInTheDocument();
    });
  });
});
```

## WebGL and Three.js Mocking Patterns

### Basic WebGL Context Mocking

```typescript
import { initializeTestEnvironment } from '../test/testSetup';
import * as THREE from 'three';

describe('WebGL Mocking Patterns', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should create Three.js renderer', () => {
    const canvas = document.createElement('canvas');
    const renderer = new THREE.WebGLRenderer({ canvas });
    
    expect(renderer).toBeInstanceOf(THREE.WebGLRenderer);
    expect(renderer.domElement).toBe(canvas);
  });

  it('should create and use WebGL context', () => {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl');
    
    // All WebGL operations are mocked
    const shader = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(shader, 'vertex shader source');
    gl.compileShader(shader);
    
    expect(gl.getShaderParameter(shader, gl.COMPILE_STATUS)).toBe(true);
  });
});
```

### Three.js Scene Testing

```typescript
describe('Three.js Scene Tests', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should create and manipulate 3D scene', () => {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, 800/600, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer();
    
    // Add objects to scene
    const geometry = new THREE.BoxGeometry();
    const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
    const cube = new THREE.Mesh(geometry, material);
    scene.add(cube);
    
    expect(scene.children).toHaveLength(1);
    expect(scene.children[0]).toBe(cube);
    
    // Test rendering (mocked)
    renderer.render(scene, camera);
    expect(renderer.domElement).toBeDefined();
  });
});
```

### Custom WebGL Mock Extensions

```typescript
import { createWebGLContextMock } from '../test/testSetup';

describe('Custom WebGL Extensions', () => {
  it('should extend WebGL mock for specific needs', () => {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl');
    
    // Add custom mock behavior
    gl.getExtension = vi.fn((name) => {
      if (name === 'OES_vertex_array_object') {
        return {
          createVertexArrayOES: vi.fn(() => ({})),
          bindVertexArrayOES: vi.fn(),
          deleteVertexArrayOES: vi.fn()
        };
      }
      return null;
    });
    
    const ext = gl.getExtension('OES_vertex_array_object');
    expect(ext).toBeDefined();
    expect(ext.createVertexArrayOES).toBeDefined();
  });
});
```

## CacheManager Mocking Patterns

### Mock CacheManager for Unit Tests

```typescript
import { createMockCacheManager } from '../test/cacheManagerMocks';

describe('CacheManager Unit Test Patterns', () => {
  let mockCacheManager;

  beforeEach(async () => {
    mockCacheManager = createMockCacheManager();
    await mockCacheManager.initialize();
  });

  it('should test cache hit scenario', async () => {
    const testData = { elevation: [100, 200, 300] };
    const mockRun = { id: 'test-run', skiAreaId: 'test-area' };
    
    // Simulate cache hit
    mockCacheManager.simulateCacheHit('test-run', 'medium', testData);
    
    const cached = await mockCacheManager.getCachedTerrainData('test-run', 'medium');
    expect(cached).toEqual(testData);
  });

  it('should test cache miss scenario', async () => {
    // Simulate cache miss
    mockCacheManager.simulateCacheMiss('test-run', 'medium');
    
    const cached = await mockCacheManager.getCachedTerrainData('test-run', 'medium');
    expect(cached).toBeNull();
  });

  it('should test cache expiration', async () => {
    const testData = { elevation: [100, 200, 300] };
    
    // Simulate expired cache
    mockCacheManager.simulateExpiredCache('test-run', 'medium', testData);
    
    const cached = await mockCacheManager.getCachedTerrainData('test-run', 'medium');
    expect(cached).toBeNull(); // Should return null for expired data
  });
});
```

### Real CacheManager with Mocked IndexedDB

```typescript
import { initializeTestEnvironment } from '../test/testSetup';

describe('CacheManager Integration Patterns', () => {
  beforeEach(async () => {
    await initializeTestEnvironment(); // Sets up fake-indexeddb
  });

  it('should use real CacheManager with mocked storage', async () => {
    const { cacheManager } = await import('../utils/CacheManager');
    
    // Real CacheManager, mocked IndexedDB
    await cacheManager.initialize();
    
    const testData = { elevation: [1, 2, 3] };
    const mockRun = { id: 'integration-test', skiAreaId: 'test-area' };
    
    await cacheManager.cacheTerrainData(testData, mockRun, 'medium');
    const cached = await cacheManager.getCachedTerrainData('integration-test', 'medium');
    
    expect(cached).toEqual(testData);
  });
});
```

### CacheManager Error Scenarios

```typescript
describe('CacheManager Error Patterns', () => {
  it('should handle initialization failure', async () => {
    const mockCacheManager = createMockCacheManager();
    
    // Mock initialization failure
    mockCacheManager.initialize = vi.fn().mockRejectedValue(
      new Error('IndexedDB not available')
    );
    
    await expect(mockCacheManager.initialize()).rejects.toThrow('IndexedDB not available');
  });

  it('should handle storage quota exceeded', async () => {
    const mockCacheManager = createMockCacheManager();
    await mockCacheManager.initialize();
    
    // Mock quota exceeded error
    mockCacheManager.cacheTerrainData = vi.fn().mockRejectedValue(
      new DOMException('Quota exceeded', 'QuotaExceededError')
    );
    
    const testData = { elevation: [1, 2, 3] };
    const mockRun = { id: 'test-run', skiAreaId: 'test-area' };
    
    await expect(
      mockCacheManager.cacheTerrainData(testData, mockRun, 'medium')
    ).rejects.toThrow('Quota exceeded');
  });
});
```

## Browser API Mocking Patterns

### Storage API Patterns

```typescript
import { createStorageMock } from '../test/browserAPIMocks';

describe('Storage API Patterns', () => {
  let mockStorage;

  beforeEach(() => {
    mockStorage = createStorageMock();
    Object.defineProperty(global, 'localStorage', {
      value: mockStorage,
      writable: true
    });
  });

  it('should test localStorage operations', () => {
    localStorage.setItem('user-preference', 'dark-mode');
    localStorage.setItem('grid-size', '64');
    
    expect(localStorage.getItem('user-preference')).toBe('dark-mode');
    expect(localStorage.length).toBe(2);
    
    localStorage.removeItem('user-preference');
    expect(localStorage.getItem('user-preference')).toBeNull();
    expect(localStorage.length).toBe(1);
  });

  it('should test storage events', () => {
    const eventHandler = vi.fn();
    window.addEventListener('storage', eventHandler);
    
    localStorage.setItem('test-key', 'test-value');
    
    // Manually trigger storage event for testing
    const storageEvent = new StorageEvent('storage', {
      key: 'test-key',
      newValue: 'test-value',
      oldValue: null,
      storageArea: localStorage
    });
    window.dispatchEvent(storageEvent);
    
    expect(eventHandler).toHaveBeenCalledWith(storageEvent);
  });
});
```

### File API Patterns

```typescript
import { createFileBlobMocks } from '../test/browserAPIMocks';

describe('File API Patterns', () => {
  beforeEach(() => {
    const { Blob, File } = createFileBlobMocks();
    global.Blob = Blob;
    global.File = File;
  });

  it('should create and read files', async () => {
    const fileContent = 'terrain data content';
    const file = new File([fileContent], 'terrain.txt', { type: 'text/plain' });
    
    expect(file.name).toBe('terrain.txt');
    expect(file.type).toBe('text/plain');
    expect(file.size).toBe(fileContent.length);
    
    const text = await file.text();
    expect(text).toBe(fileContent);
  });

  it('should create blobs from array buffer', async () => {
    const buffer = new ArrayBuffer(8);
    const view = new Uint8Array(buffer);
    view[0] = 1;
    view[1] = 2;
    
    const blob = new Blob([buffer], { type: 'application/octet-stream' });
    
    expect(blob.size).toBe(8);
    expect(blob.type).toBe('application/octet-stream');
    
    const arrayBuffer = await blob.arrayBuffer();
    const resultView = new Uint8Array(arrayBuffer);
    expect(resultView[0]).toBe(1);
    expect(resultView[1]).toBe(2);
  });
});
```

### Web Audio API Patterns

```typescript
describe('Web Audio API Patterns', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should create audio context and nodes', () => {
    const audioContext = new AudioContext();
    
    expect(audioContext.state).toBe('suspended');
    expect(audioContext.sampleRate).toBe(44100);
    
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    expect(oscillator.frequency.value).toBe(440);
    expect(gainNode.gain.value).toBe(1);
  });

  it('should handle audio context state changes', async () => {
    const audioContext = new AudioContext();
    
    expect(audioContext.state).toBe('suspended');
    
    await audioContext.resume();
    expect(audioContext.state).toBe('running');
    
    await audioContext.suspend();
    expect(audioContext.state).toBe('suspended');
  });
});
```

## Network Request Mocking Patterns

### Fetch API Patterns

```typescript
import { createFetchMock } from '../test/browserAPIMocks';

describe('Fetch API Patterns', () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = createFetchMock();
    global.fetch = fetchMock;
  });

  it('should mock successful API responses', async () => {
    const mockData = { elevation: [100, 200, 300] };
    
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockData)
    });
    
    const response = await fetch('/api/terrain/test-run');
    const data = await response.json();
    
    expect(response.ok).toBe(true);
    expect(data).toEqual(mockData);
  });

  it('should mock API error responses', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: () => Promise.resolve({ error: 'Run not found' })
    });
    
    const response = await fetch('/api/terrain/nonexistent-run');
    const error = await response.json();
    
    expect(response.ok).toBe(false);
    expect(response.status).toBe(404);
    expect(error.error).toBe('Run not found');
  });

  it('should mock network failures', async () => {
    fetchMock.mockRejectedValue(new Error('Network error'));
    
    await expect(fetch('/api/terrain/test-run')).rejects.toThrow('Network error');
  });
});
```

### Dynamic Response Patterns

```typescript
describe('Dynamic Response Patterns', () => {
  beforeEach(() => {
    const fetchMock = createFetchMock();
    
    fetchMock.mockImplementation(async (url, options) => {
      const urlStr = url.toString();
      
      if (urlStr.includes('/api/terrain/')) {
        const runId = urlStr.split('/').pop();
        return {
          ok: true,
          status: 200,
          json: () => Promise.resolve({
            runId,
            elevation: [100, 200, 300],
            timestamp: Date.now()
          })
        };
      }
      
      if (urlStr.includes('/api/weather/')) {
        return {
          ok: true,
          status: 200,
          json: () => Promise.resolve({
            temperature: 25,
            windSpeed: 10,
            conditions: 'sunny'
          })
        };
      }
      
      return {
        ok: false,
        status: 404,
        json: () => Promise.resolve({ error: 'Not found' })
      };
    });
    
    global.fetch = fetchMock;
  });

  it('should handle different API endpoints', async () => {
    const terrainResponse = await fetch('/api/terrain/whistler-peak');
    const terrainData = await terrainResponse.json();
    
    expect(terrainData.runId).toBe('whistler-peak');
    expect(terrainData.elevation).toEqual([100, 200, 300]);
    
    const weatherResponse = await fetch('/api/weather/whistler');
    const weatherData = await weatherResponse.json();
    
    expect(weatherData.temperature).toBe(25);
    expect(weatherData.conditions).toBe('sunny');
  });
});
```

### Request Verification Patterns

```typescript
describe('Request Verification Patterns', () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ success: true })
    });
    global.fetch = fetchMock;
  });

  it('should verify request parameters', async () => {
    await fetch('/api/terrain/test-run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer token123'
      },
      body: JSON.stringify({ gridSize: 'medium' })
    });
    
    expect(fetchMock).toHaveBeenCalledWith('/api/terrain/test-run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer token123'
      },
      body: JSON.stringify({ gridSize: 'medium' })
    });
  });

  it('should verify multiple requests', async () => {
    await fetch('/api/terrain/run1');
    await fetch('/api/terrain/run2');
    await fetch('/api/weather/area1');
    
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/terrain/run1');
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/terrain/run2');
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/weather/area1');
  });
});
```

## Async Operation Mocking Patterns

### Promise-based Operations

```typescript
import { delay, waitFor, withTimeout } from '../test/asyncTestUtils';

describe('Async Operation Patterns', () => {
  it('should mock async service operations', async () => {
    const mockService = {
      loadData: vi.fn().mockImplementation(async (id) => {
        await delay(100); // Simulate network delay
        return { id, data: 'loaded' };
      })
    };
    
    const result = await mockService.loadData('test-id');
    
    expect(result).toEqual({ id: 'test-id', data: 'loaded' });
    expect(mockService.loadData).toHaveBeenCalledWith('test-id');
  });

  it('should test timeout scenarios', async () => {
    const slowOperation = vi.fn().mockImplementation(async () => {
      await delay(10000); // Very slow operation
      return 'completed';
    });
    
    await expect(
      withTimeout(slowOperation(), 1000, 'Operation timeout')
    ).rejects.toThrow('Operation timeout');
  });

  it('should test retry patterns', async () => {
    let attempts = 0;
    const unreliableOperation = vi.fn().mockImplementation(async () => {
      attempts++;
      if (attempts < 3) {
        throw new Error('Temporary failure');
      }
      return 'success';
    });
    
    const result = await retry(unreliableOperation, {
      maxAttempts: 3,
      baseDelay: 10
    });
    
    expect(result).toBe('success');
    expect(unreliableOperation).toHaveBeenCalledTimes(3);
  });
});
```

### Event-based Async Patterns

```typescript
describe('Event-based Async Patterns', () => {
  it('should test event-driven operations', async () => {
    const eventEmitter = new EventTarget();
    let result = null;
    
    const operation = new Promise((resolve) => {
      eventEmitter.addEventListener('data-loaded', (event) => {
        resolve(event.detail);
      });
    });
    
    // Simulate async event
    setTimeout(() => {
      eventEmitter.dispatchEvent(new CustomEvent('data-loaded', {
        detail: { data: 'loaded' }
      }));
    }, 50);
    
    result = await withTimeout(operation, 1000);
    expect(result).toEqual({ data: 'loaded' });
  });

  it('should test condition-based waiting', async () => {
    let condition = false;
    
    // Simulate condition change
    setTimeout(() => {
      condition = true;
    }, 100);
    
    await waitFor(() => condition, {
      timeout: 1000,
      interval: 10
    });
    
    expect(condition).toBe(true);
  });
});
```

## Service and Component Mocking Patterns

### Service Dependency Injection

```typescript
describe('Service Mocking Patterns', () => {
  it('should inject mock dependencies', () => {
    const mockCacheManager = createMockCacheManager();
    const mockAgentClient = {
      getHillMetrics: vi.fn().mockResolvedValue({ slope: 30 }),
      getWeatherData: vi.fn().mockResolvedValue({ temp: 25 })
    };
    
    const terrainService = new TerrainService({
      cacheManager: mockCacheManager,
      agentClient: mockAgentClient
    });
    
    // Test service with mocked dependencies
    expect(terrainService.cacheManager).toBe(mockCacheManager);
    expect(terrainService.agentClient).toBe(mockAgentClient);
  });
});
```

### Component Props Mocking

```typescript
import { render, screen } from '@testing-library/react';

describe('Component Mocking Patterns', () => {
  it('should mock component props', () => {
    const mockProps = {
      terrainData: { elevation: [100, 200, 300] },
      onTerrainLoad: vi.fn(),
      loading: false,
      error: null
    };
    
    render(<TerrainViewer {...mockProps} />);
    
    expect(screen.getByText('Terrain Loaded')).toBeInTheDocument();
    expect(mockProps.onTerrainLoad).not.toHaveBeenCalled();
  });

  it('should mock component callbacks', async () => {
    const mockOnLoad = vi.fn();
    
    render(<TerrainViewer onTerrainLoad={mockOnLoad} />);
    
    fireEvent.click(screen.getByText('Load Terrain'));
    
    await waitFor(() => {
      expect(mockOnLoad).toHaveBeenCalledWith(expect.any(Object));
    });
  });
});
```

### Module Mocking Patterns

```typescript
// Mock entire module
vi.mock('../utils/CacheManager', () => ({
  cacheManager: createMockCacheManager()
}));

// Mock specific exports
vi.mock('../services/AgentClient', () => ({
  AgentClient: vi.fn().mockImplementation(() => ({
    getHillMetrics: vi.fn().mockResolvedValue({ slope: 30 }),
    getWeatherData: vi.fn().mockResolvedValue({ temp: 25 })
  }))
}));

describe('Module Mocking Patterns', () => {
  it('should use mocked modules', async () => {
    const { cacheManager } = await import('../utils/CacheManager');
    const { AgentClient } = await import('../services/AgentClient');
    
    expect(cacheManager.initialize).toBeDefined();
    
    const client = new AgentClient();
    const metrics = await client.getHillMetrics('test-area');
    expect(metrics.slope).toBe(30);
  });
});
```

## Error Simulation Patterns

### Network Error Simulation

```typescript
describe('Error Simulation Patterns', () => {
  it('should simulate network errors', async () => {
    global.fetch = vi.fn().mockRejectedValue(
      new Error('Failed to fetch')
    );
    
    const service = new TerrainService();
    
    await expect(
      service.loadTerrainData('test-run')
    ).rejects.toThrow('Failed to fetch');
  });

  it('should simulate HTTP error responses', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.resolve({
        error: 'Database connection failed'
      })
    });
    
    const service = new TerrainService();
    
    await expect(
      service.loadTerrainData('test-run')
    ).rejects.toThrow('Database connection failed');
  });
});
```

### Storage Error Simulation

```typescript
describe('Storage Error Patterns', () => {
  it('should simulate quota exceeded errors', async () => {
    const mockCacheManager = createMockCacheManager();
    
    mockCacheManager.cacheTerrainData = vi.fn().mockRejectedValue(
      new DOMException('Quota exceeded', 'QuotaExceededError')
    );
    
    const service = new TerrainService(mockCacheManager);
    
    await expect(
      service.cacheTerrainData({ elevation: [1, 2, 3] }, mockRun, 'large')
    ).rejects.toThrow('Quota exceeded');
  });

  it('should simulate storage unavailable', () => {
    // Mock localStorage as unavailable
    Object.defineProperty(global, 'localStorage', {
      get: () => {
        throw new Error('localStorage is not available');
      }
    });
    
    expect(() => {
      localStorage.setItem('test', 'value');
    }).toThrow('localStorage is not available');
  });
});
```

### WebGL Error Simulation

```typescript
describe('WebGL Error Patterns', () => {
  it('should simulate WebGL context loss', () => {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl');
    
    // Mock context loss
    gl.getError = vi.fn().mockReturnValue(gl.CONTEXT_LOST_WEBGL);
    gl.isContextLost = vi.fn().mockReturnValue(true);
    
    expect(gl.isContextLost()).toBe(true);
    expect(gl.getError()).toBe(gl.CONTEXT_LOST_WEBGL);
  });

  it('should simulate shader compilation errors', () => {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl');
    
    const shader = gl.createShader(gl.VERTEX_SHADER);
    
    // Mock compilation failure
    gl.getShaderParameter = vi.fn().mockReturnValue(false);
    gl.getShaderInfoLog = vi.fn().mockReturnValue('Syntax error in shader');
    
    gl.shaderSource(shader, 'invalid shader source');
    gl.compileShader(shader);
    
    expect(gl.getShaderParameter(shader, gl.COMPILE_STATUS)).toBe(false);
    expect(gl.getShaderInfoLog(shader)).toBe('Syntax error in shader');
  });
});
```

## Performance Testing Patterns

### Load Testing Patterns

```typescript
describe('Performance Testing Patterns', () => {
  it('should test performance under load', async () => {
    const mockCacheManager = createMockCacheManager();
    await mockCacheManager.initialize();
    
    const operations = [];
    const startTime = Date.now();
    
    // Simulate 100 concurrent cache operations
    for (let i = 0; i < 100; i++) {
      operations.push(
        mockCacheManager.cacheTerrainData(
          { elevation: [i, i+1, i+2] },
          { id: `run-${i}`, skiAreaId: 'test-area' },
          'medium'
        )
      );
    }
    
    await Promise.all(operations);
    
    const duration = Date.now() - startTime;
    expect(duration).toBeLessThan(1000); // Should complete within 1 second
    expect(mockCacheManager.getTerrainCacheSize()).toBe(100);
  });

  it('should test memory usage patterns', async () => {
    const mockCacheManager = createMockCacheManager();
    await mockCacheManager.initialize();
    
    // Create large data sets
    const largeData = {
      elevation: new Array(10000).fill(0).map((_, i) => i)
    };
    
    const initialStats = await mockCacheManager.getCacheStats();
    
    await mockCacheManager.cacheTerrainData(
      largeData,
      { id: 'large-run', skiAreaId: 'test-area' },
      'large'
    );
    
    const finalStats = await mockCacheManager.getCacheStats();
    
    expect(finalStats.totalSize).toBeGreaterThan(initialStats.totalSize);
    expect(finalStats.entryCount).toBe(initialStats.entryCount + 1);
  });
});
```

### Timing and Profiling Patterns

```typescript
describe('Timing Patterns', () => {
  it('should measure operation timing', async () => {
    const service = new TerrainService();
    
    const startTime = performance.now();
    await service.loadTerrainData('test-run');
    const endTime = performance.now();
    
    const duration = endTime - startTime;
    expect(duration).toBeLessThan(100); // Should complete within 100ms
  });

  it('should profile multiple operations', async () => {
    const service = new TerrainService();
    const timings = [];
    
    for (let i = 0; i < 10; i++) {
      const start = performance.now();
      await service.processElevationData([1, 2, 3]);
      const end = performance.now();
      timings.push(end - start);
    }
    
    const averageTime = timings.reduce((a, b) => a + b) / timings.length;
    const maxTime = Math.max(...timings);
    
    expect(averageTime).toBeLessThan(10); // Average under 10ms
    expect(maxTime).toBeLessThan(50); // Max under 50ms
  });
});
```

## Integration Testing Patterns

### Multi-Service Integration

```typescript
describe('Integration Testing Patterns', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should test service integration', async () => {
    // Use real services with mocked external dependencies
    const terrainService = new TerrainService();
    const agentClient = new AgentClient();
    
    // Mock external API calls
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ elevation: [100, 200, 300] })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ slope: 30, aspect: 180 })
      });
    
    // Test integrated workflow
    const terrainData = await terrainService.loadTerrainData('test-run');
    const hillMetrics = await agentClient.getHillMetrics('test-area');
    
    expect(terrainData.elevation).toEqual([100, 200, 300]);
    expect(hillMetrics.slope).toBe(30);
  });

  it('should test component integration', async () => {
    const mockProps = {
      runId: 'test-run',
      gridSize: 'medium',
      onDataLoaded: vi.fn()
    };
    
    render(<TerrainViewer {...mockProps} />);
    
    // Wait for component to load data
    await waitFor(() => {
      expect(screen.getByText('Terrain Loaded')).toBeInTheDocument();
    });
    
    expect(mockProps.onDataLoaded).toHaveBeenCalledWith(
      expect.objectContaining({
        elevation: expect.any(Array)
      })
    );
  });
});
```

### End-to-End Workflow Testing

```typescript
describe('E2E Workflow Patterns', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should test complete terrain loading workflow', async () => {
    // Mock all external dependencies
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          runs: [{ id: 'test-run', name: 'Test Run' }]
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          elevation: [100, 200, 300]
        })
      });
    
    render(<App />);
    
    // Select ski area
    fireEvent.click(screen.getByText('Whistler'));
    
    // Wait for runs to load
    await waitFor(() => {
      expect(screen.getByText('Test Run')).toBeInTheDocument();
    });
    
    // Select run
    fireEvent.click(screen.getByText('Test Run'));
    
    // Wait for terrain to load
    await waitFor(() => {
      expect(screen.getByText('Terrain Loaded')).toBeInTheDocument();
    });
    
    // Verify complete workflow
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });
});
```

## Best Practices Summary

### When to Use Each Mock Type

1. **Unit Tests**: Use comprehensive mocks for all dependencies
2. **Integration Tests**: Use real implementations with mocked external APIs
3. **E2E Tests**: Use minimal mocking, only for external services

### Mock Lifecycle Management

1. **Setup**: Initialize mocks in `beforeEach`
2. **Cleanup**: Reset mocks in `afterEach`
3. **Isolation**: Ensure tests don't affect each other

### Performance Considerations

1. **Use lightweight mocks** for unit tests
2. **Cache mock instances** when appropriate
3. **Profile test performance** regularly

### Debugging Mock Issues

1. **Log mock calls** to understand behavior
2. **Verify mock setup** before tests
3. **Use explicit assertions** for mock interactions

This comprehensive guide provides patterns for effectively using mocks in the Alpine Ski Simulator frontend test environment. Choose the appropriate patterns based on your testing needs and maintain consistency across your test suite.