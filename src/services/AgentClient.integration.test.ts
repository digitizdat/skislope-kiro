/**
 * Integration tests for AgentClient to verify API contracts with backend agents
 * These tests would have caught the method name mismatches
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { AgentClient, createAgentClient } from './AgentClient';
import { HillMetricsRequest, WeatherRequest, EquipmentRequest } from '../models/AgentTypes';
import { SkiArea } from '../models/SkiArea';
import { GridSize } from '../models/TerrainData';

// Mock ski area for testing
const mockSkiArea: SkiArea = {
  id: 'test-area',
  name: 'Test Area',
  location: 'Test Location',
  country: 'Test Country',
  bounds: {
    northEast: { lat: 46.0, lng: 7.1 },
    southWest: { lat: 45.9, lng: 7.0 }
  },
  elevation: { min: 1000, max: 3000 },
  previewImage: 'test.jpg',
  agentEndpoints: {
    hillMetrics: 'http://localhost:8001',
    weather: 'http://localhost:8002',
    equipment: 'http://localhost:8003'
  },
  fisCompatible: true
};

describe('AgentClient Integration Tests', () => {
  let agentClient: AgentClient;
  let agentsAvailable = false;

  beforeAll(async () => {
    agentClient = createAgentClient();
    
    // Initialize cache manager for tests
    try {
      const { cacheManager } = await import('../utils/CacheManager');
      await cacheManager.initialize();
    } catch (error) {
      console.warn('Could not initialize cache manager:', error);
    }
    
    // Check if agents are running
    try {
      const healthChecks = await Promise.allSettled([
        fetch('http://localhost:8001/health'),
        fetch('http://localhost:8002/health'),
        fetch('http://localhost:8003/health')
      ]);
      
      agentsAvailable = healthChecks.every(result => 
        result.status === 'fulfilled' && result.value.ok
      );
      
      if (!agentsAvailable) {
        console.warn('⚠️  Agent servers not running - integration tests will be skipped');
        console.warn('   Start agents with: uv run python scripts/start_agents.py');
      }
    } catch (error) {
      console.warn('⚠️  Could not connect to agent servers:', error);
    }
  });

  describe('Hill Metrics Agent Contract', () => {
    it('should successfully call getHillMetrics method', async () => {
      if (!agentsAvailable) {
        console.log('⏭️  Skipping - agents not available');
        return;
      }

      const request: HillMetricsRequest = {
        area: mockSkiArea,
        gridSize: GridSize.MEDIUM,
        includeAnalysis: true
      };

      const response = await agentClient.callHillMetricsAgent(request);
      
      expect(response).toBeDefined();
      expect(response.data).toBeDefined();
      expect(response.metadata).toBeDefined();
      expect(response.metadata.processingTime).toBeGreaterThan(0);
      
      console.log('✅ Hill Metrics API contract verified');
    });

    it('should handle hill metrics errors gracefully', async () => {
      if (!agentsAvailable) {
        console.log('⏭️  Skipping - agents not available');
        return;
      }

      const invalidRequest: HillMetricsRequest = {
        area: {
          ...mockSkiArea,
          bounds: {
            // Invalid bounds (north < south)
            northEast: { lat: 45.0, lng: 7.1 },
            southWest: { lat: 46.0, lng: 7.0 }
          }
        },
        gridSize: GridSize.MEDIUM,
        includeAnalysis: true
      };

      await expect(agentClient.callHillMetricsAgent(invalidRequest))
        .rejects.toThrow();
      
      console.log('✅ Hill Metrics error handling verified');
    });
  });

  describe('Weather Agent Contract', () => {
    it('should successfully call getWeatherData method', async () => {
      if (!agentsAvailable) {
        console.log('⏭️  Skipping - agents not available');
        return;
      }

      const request: WeatherRequest = {
        area: mockSkiArea,
        timestamp: new Date(),
        includeForecast: true,
        forecastHours: 24
      };

      const response = await agentClient.callWeatherAgent(request);
      
      expect(response).toBeDefined();
      expect(response.current).toBeDefined();
      expect(response.metadata).toBeDefined();
      
      console.log('✅ Weather API contract verified');
    });
  });

  describe('Equipment Agent Contract', () => {
    it('should successfully call getEquipmentData method', async () => {
      if (!agentsAvailable) {
        console.log('⏭️  Skipping - agents not available');
        return;
      }

      const request: EquipmentRequest = {
        area: mockSkiArea,
        includeStatus: true,
        equipmentTypes: ['lifts', 'trails']
      };

      const response = await agentClient.callEquipmentAgent(request);
      
      expect(response).toBeDefined();
      expect(response.data).toBeDefined();
      expect(response.metadata).toBeDefined();
      
      console.log('✅ Equipment API contract verified');
    });
  });

  describe('Method Name Contract Verification', () => {
    it('should verify all expected methods exist', async () => {
      if (!agentsAvailable) {
        console.log('⏭️  Skipping - agents not available');
        return;
      }

      const expectedMethods = {
        'http://localhost:8001': ['getHillMetrics', 'getElevationProfile'],
        'http://localhost:8002': ['getWeatherData', 'getSkiConditions', 'getWeatherAlerts'],
        'http://localhost:8003': ['getEquipmentData', 'getLiftStatus', 'getTrailConditions', 'getFacilities']
      };

      for (const [endpoint, methods] of Object.entries(expectedMethods)) {
        for (const method of methods) {
          const response = await fetch(`${endpoint}/jsonrpc`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              jsonrpc: '2.0',
              method,
              params: {},
              id: 'contract-test'
            })
          });

          expect(response.ok).toBe(true);
          
          const data = await response.json();
          
          // Should not be "method not found" error
          if (data.error) {
            expect(data.error.code).not.toBe(-32601); // Method not found
          }
          
          console.log(`✅ Method '${method}' exists at ${endpoint}`);
        }
      }
    });

    it('should fail for non-existent methods', async () => {
      if (!agentsAvailable) {
        console.log('⏭️  Skipping - agents not available');
        return;
      }

      const response = await fetch('http://localhost:8001/jsonrpc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'nonExistentMethod',
          params: {},
          id: 'negative-test'
        })
      });

      expect(response.ok).toBe(true);
      
      const data = await response.json();
      expect(data.error).toBeDefined();
      expect(data.error.code).toBe(-32601); // Method not found
      
      console.log('✅ Non-existent method properly rejected');
    });
  });

  describe('CORS Configuration', () => {
    it('should allow cross-origin requests', async () => {
      if (!agentsAvailable) {
        console.log('⏭️  Skipping - agents not available');
        return;
      }

      // Test preflight request
      const preflightResponse = await fetch('http://localhost:8001/jsonrpc', {
        method: 'OPTIONS',
        headers: {
          'Origin': 'http://localhost:5173',
          'Access-Control-Request-Method': 'POST',
          'Access-Control-Request-Headers': 'Content-Type'
        }
      });

      expect(preflightResponse.ok).toBe(true);
      expect(preflightResponse.headers.get('access-control-allow-origin')).toBeTruthy();
      
      console.log('✅ CORS preflight verified');

      // Test actual request with Origin
      const actualResponse = await fetch('http://localhost:8001/jsonrpc', {
        method: 'POST',
        headers: {
          'Origin': 'http://localhost:5173',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'getHillMetrics',
          params: {
            bounds: {
              north: 46.0,
              south: 45.9,
              east: 7.1,
              west: 7.0
            }
          },
          id: 'cors-test'
        })
      });

      expect(actualResponse.ok).toBe(true);
      expect(actualResponse.headers.get('access-control-allow-origin')).toBeTruthy();
      
      console.log('✅ CORS actual request verified');
    });
  });

  describe('End-to-End Terrain Loading', () => {
    it('should complete full terrain loading workflow', async () => {
      if (!agentsAvailable) {
        console.log('⏭️  Skipping - agents not available');
        return;
      }

      // Simulate the exact workflow from TerrainService
      console.log('🔄 Testing end-to-end terrain loading workflow...');

      // 1. Hill Metrics (primary data)
      const hillMetricsRequest: HillMetricsRequest = {
        area: mockSkiArea,
        gridSize: GridSize.MEDIUM,
        includeAnalysis: true
      };

      const hillMetricsResponse = await agentClient.callHillMetricsAgent(hillMetricsRequest);
      expect(hillMetricsResponse.data).toBeDefined();
      console.log('  ✅ Hill metrics data retrieved');

      // 2. Weather (supplementary)
      const weatherRequest: WeatherRequest = {
        area: mockSkiArea,
        timestamp: new Date(),
        includeForecast: true
      };

      const weatherResponse = await agentClient.callWeatherAgent(weatherRequest);
      expect(weatherResponse.current).toBeDefined();
      console.log('  ✅ Weather data retrieved');

      // 3. Equipment (supplementary)
      const equipmentRequest: EquipmentRequest = {
        area: mockSkiArea,
        includeStatus: true
      };

      const equipmentResponse = await agentClient.callEquipmentAgent(equipmentRequest);
      expect(equipmentResponse.data).toBeDefined();
      console.log('  ✅ Equipment data retrieved');

      console.log('✅ End-to-end terrain loading workflow completed successfully');
    });
  });
});

// Helper function to check if agents are running
export async function checkAgentsHealth(): Promise<boolean> {
  try {
    const healthChecks = await Promise.allSettled([
      fetch('http://localhost:8001/health'),
      fetch('http://localhost:8002/health'),
      fetch('http://localhost:8003/health')
    ]);
    
    return healthChecks.every(result => 
      result.status === 'fulfilled' && result.value.ok
    );
  } catch {
    return false;
  }
}