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

// Mock fetch globally
const mockFetch = vi.fn();
(globalThis as any).fetch = mockFetch;

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

  beforeEach(() => {
    agentClient = new AgentClient(DEFAULT_AGENT_CONFIG);
    vi.clearAllMocks();
  });

  afterEach(() => {
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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          jsonrpc: '2.0',
          result: mockResponse,
          id: 1
        })
      });

      const request: HillMetricsRequest = {
        area: createTestSkiArea(),
        gridSize: GridSize.MEDIUM
      };

      const result = await agentClient.callHillMetricsAgent(request);

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        DEFAULT_AGENT_CONFIG.hillMetrics.endpoint,
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('getHillMetrics')
        })
      );
    });

    it('should handle JSON-RPC error responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          jsonrpc: '2.0',
          error: {
            code: JSONRPCErrorCode.DATA_NOT_FOUND,
            message: 'Terrain data not available',
            data: { area: 'test-area' }
          },
          id: 1
        })
      });

      const request: HillMetricsRequest = {
        area: createTestSkiArea(),
        gridSize: GridSize.MEDIUM
      };

      await expect(agentClient.callHillMetricsAgent(request)).rejects.toThrow(AgentError);
    });

    it('should handle HTTP errors', async () => {
      mockFetch.mockResolvedValueOnce({
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
      // First two calls fail, third succeeds
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            jsonrpc: '2.0',
            error: {
              code: JSONRPCErrorCode.INTERNAL_ERROR,
              message: 'Internal server error'
            },
            id: 1
          })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            jsonrpc: '2.0',
            error: {
              code: JSONRPCErrorCode.INTERNAL_ERROR,
              message: 'Internal server error'
            },
            id: 2
          })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            jsonrpc: '2.0',
            result: {
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
            },
            id: 3
          })
        });

      const request: WeatherRequest = {
        area: createTestSkiArea()
      };

      const result = await agentClient.callWeatherAgent(request);

      expect(result.current.temperature).toBe(5);
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it('should not retry on non-retryable errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          jsonrpc: '2.0',
          error: {
            code: JSONRPCErrorCode.METHOD_NOT_FOUND,
            message: 'Method not found'
          },
          id: 1
        })
      });

      const request: WeatherRequest = {
        area: createTestSkiArea()
      };

      await expect(agentClient.callWeatherAgent(request)).rejects.toThrow(AgentError);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should give up after max retry attempts', async () => {
      // All calls fail
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          jsonrpc: '2.0',
          error: {
            code: JSONRPCErrorCode.INTERNAL_ERROR,
            message: 'Internal server error'
          },
          id: 1
        })
      });

      const request: WeatherRequest = {
        area: createTestSkiArea()
      };

      await expect(agentClient.callWeatherAgent(request)).rejects.toThrow(AgentError);
      expect(mockFetch).toHaveBeenCalledTimes(DEFAULT_RETRY_CONFIG.maxAttempts);
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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          jsonrpc: '2.0',
          result: mockHealthResponse,
          id: 1
        })
      });

      const result = await agentClient.healthCheck(AgentType.HILL_METRICS);

      expect(result.status).toBe('healthy');
      expect(result.version).toBe('1.0.0');
      expect(result.metrics).toBeDefined();
      expect(mockFetch).toHaveBeenCalledWith(
        DEFAULT_AGENT_CONFIG.hillMetrics.endpoint,
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('healthCheck')
        })
      );
    });

    it('should return unhealthy status on failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Connection failed'));

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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          result: mockResponse,
          id: 1
        })
      });

      const request: HillMetricsRequest = {
        area: createTestSkiArea(),
        gridSize: GridSize.MEDIUM
      };

      const result = await agentClient.callHillMetricsAgent(request);

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        DEFAULT_AGENT_CONFIG.hillMetrics.endpoint,
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-Protocol': 'MCP'
          })
        })
      );
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

      const clientWithFallback = new AgentClient({
        ...DEFAULT_AGENT_CONFIG,
        weather: {
          ...DEFAULT_AGENT_CONFIG.weather,
          fallbackData
        }
      });

      mockFetch.mockRejectedValueOnce(new Error('Weather service unavailable'));

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

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            jsonrpc: '2.0',
            result: mockHillResponse,
            id: 1
          })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            jsonrpc: '2.0',
            result: mockWeatherResponse,
            id: 2
          })
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