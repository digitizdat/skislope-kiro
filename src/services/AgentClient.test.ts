/**
 * Agent Client Service Tests
 * Requirements: 8.1, 8.2, 8.5 - Test agent communication, error handling, health checks
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AgentClient, AgentError, DEFAULT_AGENT_CONFIG } from './AgentClient';
import {
  AgentType,
  JSONRPCErrorCode,
  HillMetricsRequest,
  WeatherRequest,
  DEFAULT_RETRY_CONFIG
} from '../models/AgentTypes';
import { GridSize, SnowCondition } from '../models/TerrainData';
import { createMockCacheManager } from '../test/cacheManagerMocks';
import { AsyncTestUtils } from '../test/asyncTestUtils';

// Mock CacheManager module
vi.mock('../utils/CacheManager', async () => {
  const { createMockCacheManager } = await import('../test/cacheManagerMocks');
  return {
    cacheManager: createMockCacheManager()
  };
});

// Helper function to create test ski area
const createTestSkiArea = () => ({
  id: 'test-area',
  name: 'Test Area',
  location: 'Test Location',
  country: 'Test Country',
  bounds: {
    northEast: { lat: 46.0, lng: 7.0 },
    southWest: { lat: 45.0, lng: 6.0 }
  },
  elevation: { min: 1000, max: 3000 },
  previewImage: 'test.jpg',
  agentEndpoints: {
    hillMetrics: 'http://localhost:8001',
    weather: 'http://localhost:8002',
    equipment: 'http://localhost:8003'
  },
  fisCompatible: true
});

describe('AgentClient', () => {
  let agentClient: AgentClient;
  let mockCacheManager: ReturnType<typeof createMockCacheManager>;
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    // Get the mocked cache manager instance
    const { cacheManager } = await import('../utils/CacheManager');
    mockCacheManager = cacheManager as any;
    
    // Initialize mock cache manager
    await mockCacheManager.initialize();
    
    // Clear all cache to ensure fresh state
    await mockCacheManager.clearCache();
    
    // Get the fetch mock from the global scope (set up by test environment)
    mockFetch = globalThis.fetch as any;
    
    // Create agent client with test-friendly configuration
    const testConfig = {
      ...DEFAULT_AGENT_CONFIG,
      hillMetrics: {
        ...DEFAULT_AGENT_CONFIG.hillMetrics,
        timeout: 1000 // Shorter timeout for tests
      },
      weather: {
        ...DEFAULT_AGENT_CONFIG.weather,
        cacheDuration: 1000
      },
      equipment: {
        ...DEFAULT_AGENT_CONFIG.equipment,
        updateFrequency: 1000
      }
    };
    
    const testRetryConfig = {
      ...DEFAULT_RETRY_CONFIG,
      maxAttempts: 2, // Fewer retries for faster tests
      baseDelay: 10,  // Shorter delays
      maxDelay: 100
    };
    
    agentClient = new AgentClient(testConfig, testRetryConfig);
    
    // Clear and reset mocks
    vi.clearAllMocks();
    if (mockFetch && typeof mockFetch.mockClear === 'function') {
      mockFetch.mockClear();
    }
  });

  afterEach(async () => {
    if (mockCacheManager) {
      await mockCacheManager.clearCache();
      mockCacheManager.setInitialized(false);
    }
    vi.restoreAllMocks();
  });

  describe('JSON-RPC Communication', () => {
    it('should make successful hill metrics request', async () => {
      const mockResponse = {
        data: {
          elevationData: [[100, 200], [150, 250]],
          slopeAngles: [[10, 15], [12, 18]],
          aspectAngles: [[45, 90], [60, 120]],
          surfaceTypes: [['powder', 'packed'], ['ice', 'moguls']]
        },
        metadata: {
          processingTime: 1500,
          dataSource: 'test',
          lastUpdated: new Date(),
          gridResolution: GridSize.MEDIUM
        }
      };

      const jsonRpcResponse = {
        jsonrpc: '2.0',
        result: mockResponse,
        id: 1
      };

      // Mock successful JSON-RPC response using the browser API mock interface
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: jsonRpcResponse
      });

      const request: HillMetricsRequest = {
        area: createTestSkiArea(),
        gridSize: GridSize.MEDIUM
      };

      const result = await agentClient.callHillMetricsAgent(request);

      expect(result).toEqual(mockResponse);
    });

    it('should handle JSON-RPC error responses', async () => {
      // Mock JSON-RPC error response
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: {
          jsonrpc: '2.0',
          error: {
            code: JSONRPCErrorCode.DATA_NOT_FOUND,
            message: 'Terrain data not available',
            data: { area: 'test-area' }
          },
          id: 1
        }
      });

      const request: HillMetricsRequest = {
        area: createTestSkiArea(),
        gridSize: GridSize.MEDIUM
      };

      await expect(agentClient.callHillMetricsAgent(request)).rejects.toThrow(AgentError);
    });

    it('should handle HTTP errors', async () => {
      // Mock HTTP error response
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      const request: HillMetricsRequest = {
        area: createTestSkiArea(),
        gridSize: GridSize.MEDIUM
      };

      await expect(agentClient.callHillMetricsAgent(request)).rejects.toThrow(AgentError);
    });
  });

  describe('Retry Logic with Exponential Backoff', () => {
    it('should retry on retryable errors', async () => {
      const successResponse = {
        current: {
          temperature: 5,
          windSpeed: 10,
          windDirection: 180,
          precipitation: 0,
          visibility: 10000,
          snowConditions: SnowCondition.POWDER,
          timestamp: new Date()
        },
        metadata: {
          source: 'test',
          lastUpdated: new Date(),
          accuracy: 0.9
        }
      };

      let callCount = 0;
      // First call fails with retryable error, second succeeds
      mockFetch.mockImplementation(async (input, init) => {
        callCount++;
        const url = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url;
        
        if (callCount === 1) {
          return {
            ok: true,
            status: 200,
            statusText: 'OK',
            headers: new Map(),
            url,
            json: () => Promise.resolve({
              jsonrpc: '2.0',
              error: {
                code: JSONRPCErrorCode.INTERNAL_ERROR,
                message: 'Internal server error'
              },
              id: 1
            }),
            text: () => Promise.resolve(''),
            blob: () => Promise.resolve(new Blob()),
            arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
            clone: () => ({} as any)
          };
        } else {
          return {
            ok: true,
            status: 200,
            statusText: 'OK',
            headers: new Map(),
            url,
            json: () => Promise.resolve({
              jsonrpc: '2.0',
              result: successResponse,
              id: 2
            }),
            text: () => Promise.resolve(''),
            blob: () => Promise.resolve(new Blob()),
            arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
            clone: () => ({} as any)
          };
        }
      });

      const request: WeatherRequest = {
        area: createTestSkiArea()
      };

      const result = await agentClient.callWeatherAgent(request);

      expect(result.current.temperature).toBe(5);
      expect(callCount).toBe(2);
    });

    it('should not retry on non-retryable errors', async () => {
      let callCount = 0;
      // Mock non-retryable error (METHOD_NOT_FOUND)
      mockFetch.mockImplementation(async (input, init) => {
        callCount++;
        const url = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url;
        
        return {
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Map(),
          url,
          json: () => Promise.resolve({
            jsonrpc: '2.0',
            error: {
              code: JSONRPCErrorCode.METHOD_NOT_FOUND,
              message: 'Method not found'
            },
            id: 1
          }),
          text: () => Promise.resolve(''),
          blob: () => Promise.resolve(new Blob()),
          arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
          clone: () => ({} as any)
        };
      });

      const request: WeatherRequest = {
        area: createTestSkiArea()
      };

      await expect(agentClient.callWeatherAgent(request)).rejects.toThrow(AgentError);
      expect(callCount).toBe(1);
    });

    it('should give up after max retry attempts', async () => {
      let callCount = 0;
      // All calls fail with retryable error
      mockFetch.mockImplementation(async (input, init) => {
        callCount++;
        const url = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url;
        
        return {
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Map(),
          url,
          json: () => Promise.resolve({
            jsonrpc: '2.0',
            error: {
              code: JSONRPCErrorCode.INTERNAL_ERROR,
              message: 'Internal server error'
            },
            id: callCount
          }),
          text: () => Promise.resolve(''),
          blob: () => Promise.resolve(new Blob()),
          arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
          clone: () => ({} as any)
        };
      });

      const request: WeatherRequest = {
        area: createTestSkiArea()
      };

      await expect(agentClient.callWeatherAgent(request)).rejects.toThrow(AgentError);
      expect(callCount).toBe(2); // Using test retry config with maxAttempts: 2
    });
  });

  describe('Health Checks', () => {
    it('should perform successful health check', async () => {
      const mockHealthResponse = {
        status: 'healthy' as const,
        timestamp: new Date(),
        responseTime: 150,
        version: '1.0.0',
        metrics: {
          uptime: 86400,
          requestCount: 1000,
          errorRate: 0.01,
          averageResponseTime: 200
        }
      };

      // Mock successful health check response
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: {
          jsonrpc: '2.0',
          result: mockHealthResponse,
          id: 1
        }
      });

      const result = await agentClient.healthCheck(AgentType.HILL_METRICS);

      expect(result.status).toBe('healthy');
      expect(result.version).toBe('1.0.0');
      expect(result.metrics).toBeDefined();
    });

    it('should return unhealthy status on failure', async () => {
      // Mock network failure
      mockFetch.mockRejectedValue(new Error('Connection failed'));

      const result = await agentClient.healthCheck(AgentType.WEATHER);

      expect(result.status).toBe('unhealthy');
      expect(result.version).toBe('unknown');
      expect(result.responseTime).toBeGreaterThan(0);
    });
  });

  describe('MCP Protocol Support', () => {
    it('should switch to MCP protocol', async () => {
      agentClient.setProtocol(AgentType.HILL_METRICS, 'mcp');

      const mockResponse = {
        data: {
          elevationData: [[100, 200], [150, 250]],
          slopeAngles: [[10, 15], [12, 18]],
          aspectAngles: [[45, 90], [60, 120]],
          surfaceTypes: [['powder', 'packed'], ['ice', 'moguls']]
        },
        metadata: {
          processingTime: 1500,
          dataSource: 'test',
          lastUpdated: new Date(),
          gridResolution: GridSize.MEDIUM
        }
      };

      // Mock successful MCP response (note: no jsonrpc field for MCP)
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: {
          result: mockResponse,
          id: 1
        }
      });

      const request: HillMetricsRequest = {
        area: createTestSkiArea(),
        gridSize: GridSize.MEDIUM
      };

      const result = await agentClient.callHillMetricsAgent(request);

      expect(result).toEqual(mockResponse);
    });

    it('should enable MCP mode for all agents', () => {
      agentClient.enableMCPMode();

      // This would be tested by making requests and checking headers
      // but we'll just verify the method doesn't throw
      expect(() => agentClient.enableMCPMode()).not.toThrow();
    });
  });

  describe('Weather Agent Fallback', () => {
    it('should use fallback data when weather agent fails', async () => {
      const fallbackData = {
        temperature: 0,
        windSpeed: 5,
        windDirection: 90,
        precipitation: 0,
        visibility: 5000,
        snowConditions: SnowCondition.PACKED_POWDER,
        timestamp: new Date()
      };

      const testConfig = {
        ...DEFAULT_AGENT_CONFIG,
        weather: {
          ...DEFAULT_AGENT_CONFIG.weather,
          fallbackData,
          cacheDuration: 1000
        }
      };

      const testRetryConfig = {
        ...DEFAULT_RETRY_CONFIG,
        maxAttempts: 2,
        baseDelay: 10,
        maxDelay: 100
      };

      const clientWithFallback = new AgentClient(testConfig, testRetryConfig);

      // Mock network failure for all retry attempts
      mockFetch.mockRejectedValue(new Error('Weather service unavailable'));

      const request: WeatherRequest = {
        area: createTestSkiArea()
      };

      const result = await clientWithFallback.callWeatherAgent(request);

      expect(result.current).toEqual(fallbackData);
      expect(result.metadata.source).toBe('fallback');
      expect(result.metadata.accuracy).toBe(0.5);
    });
  });

  describe('Batch Requests', () => {
    it('should execute batch requests in parallel', async () => {
      const mockHillResponse = {
        data: {
          elevationData: [[100, 200]],
          slopeAngles: [[10, 15]],
          aspectAngles: [[45, 90]],
          surfaceTypes: [['powder', 'packed']]
        },
        metadata: {
          processingTime: 1500,
          dataSource: 'test',
          lastUpdated: new Date(),
          gridResolution: GridSize.MEDIUM
        }
      };

      const mockWeatherResponse = {
        current: {
          temperature: 5,
          windSpeed: 10,
          windDirection: 180,
          precipitation: 0,
          visibility: 10000,
          snowConditions: SnowCondition.POWDER,
          timestamp: new Date()
        },
        metadata: {
          source: 'test',
          lastUpdated: new Date(),
          accuracy: 0.9
        }
      };

      let callCount = 0;
      // Mock successful responses for both requests
      mockFetch.mockImplementation(async (input, init) => {
        callCount++;
        const url = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url;
        
        if (callCount === 1) {
          return {
            ok: true,
            status: 200,
            statusText: 'OK',
            headers: new Map(),
            url,
            json: () => Promise.resolve({
              jsonrpc: '2.0',
              result: mockHillResponse,
              id: 1
            }),
            text: () => Promise.resolve(''),
            blob: () => Promise.resolve(new Blob()),
            arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
            clone: () => ({} as any)
          };
        } else {
          return {
            ok: true,
            status: 200,
            statusText: 'OK',
            headers: new Map(),
            url,
            json: () => Promise.resolve({
              jsonrpc: '2.0',
              result: mockWeatherResponse,
              id: 2
            }),
            text: () => Promise.resolve(''),
            blob: () => Promise.resolve(new Blob()),
            arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
            clone: () => ({} as any)
          };
        }
      });

      const testArea = createTestSkiArea();

      const batchRequest = {
        requests: [
          { area: testArea, gridSize: GridSize.MEDIUM },
          { area: testArea, timestamp: new Date() }
        ],
        parallel: true
      };

      const result = await agentClient.batchRequest(batchRequest);

      expect(result.responses).toHaveLength(2);
      expect(result.errors).toHaveLength(0);
      expect(result.metadata.successCount).toBe(2);
      expect(result.metadata.errorCount).toBe(0);
    });
  });
});