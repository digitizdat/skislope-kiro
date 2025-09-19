/**
 * Agent utility functions for configuration and testing
 * Requirements: 8.1, 8.2, 8.5 - Agent communication utilities
 */

import { AgentType, AgentConfiguration, RetryConfiguration } from '../models/AgentTypes';
import { SnowCondition } from '../models/TerrainData';
import { createAgentClient, AgentClient } from '../services/AgentClient';

/**
 * Create agent configuration from environment variables (Node.js) or defaults (browser)
 */
export function createAgentConfigFromEnv(): AgentConfiguration {
  // Check if we're in a Node.js environment
  const isNode = typeof globalThis !== 'undefined' && 
                 typeof (globalThis as any).process !== 'undefined' && 
                 (globalThis as any).process.env;
  
  return {
    hillMetrics: {
      endpoint: (isNode ? (globalThis as any).process.env.HILL_METRICS_ENDPOINT : undefined) || 'http://localhost:8001/jsonrpc',
      timeout: parseInt((isNode ? (globalThis as any).process.env.HILL_METRICS_TIMEOUT : undefined) || '30000'),
      retryAttempts: parseInt((isNode ? (globalThis as any).process.env.HILL_METRICS_RETRY_ATTEMPTS : undefined) || '3'),
      protocol: ((isNode ? (globalThis as any).process.env.HILL_METRICS_PROTOCOL : undefined) as 'jsonrpc' | 'mcp') || 'jsonrpc'
    },
    weather: {
      endpoint: (isNode ? (globalThis as any).process.env.WEATHER_ENDPOINT : undefined) || 'http://localhost:8002/jsonrpc',
      cacheDuration: parseInt((isNode ? (globalThis as any).process.env.WEATHER_CACHE_DURATION : undefined) || '300000'),
      protocol: ((isNode ? (globalThis as any).process.env.WEATHER_PROTOCOL : undefined) as 'jsonrpc' | 'mcp') || 'jsonrpc'
    },
    equipment: {
      endpoint: (isNode ? (globalThis as any).process.env.EQUIPMENT_ENDPOINT : undefined) || 'http://localhost:8003/jsonrpc',
      updateFrequency: parseInt((isNode ? (globalThis as any).process.env.EQUIPMENT_UPDATE_FREQUENCY : undefined) || '600000'),
      protocol: ((isNode ? (globalThis as any).process.env.EQUIPMENT_PROTOCOL : undefined) as 'jsonrpc' | 'mcp') || 'jsonrpc'
    }
  };
}

/**
 * Create retry configuration from environment variables (Node.js) or defaults (browser)
 */
export function createRetryConfigFromEnv(): RetryConfiguration {
  // Check if we're in a Node.js environment
  const isNode = typeof globalThis !== 'undefined' && 
                 typeof (globalThis as any).process !== 'undefined' && 
                 (globalThis as any).process.env;
  
  return {
    maxAttempts: parseInt((isNode ? (globalThis as any).process.env.AGENT_MAX_RETRY_ATTEMPTS : undefined) || '3'),
    baseDelay: parseInt((isNode ? (globalThis as any).process.env.AGENT_BASE_DELAY : undefined) || '1000'),
    maxDelay: parseInt((isNode ? (globalThis as any).process.env.AGENT_MAX_DELAY : undefined) || '10000'),
    backoffMultiplier: parseFloat((isNode ? (globalThis as any).process.env.AGENT_BACKOFF_MULTIPLIER : undefined) || '2'),
    retryableErrors: [
      -32603, // INTERNAL_ERROR
      -32001, // AGENT_UNAVAILABLE
      -32004  // TIMEOUT_ERROR
    ]
  };
}

/**
 * Test agent connectivity
 */
export async function testAgentConnectivity(client: AgentClient): Promise<{
  hillMetrics: boolean;
  weather: boolean;
  equipment: boolean;
}> {
  const results = {
    hillMetrics: false,
    weather: false,
    equipment: false
  };

  try {
    const hillHealth = await client.healthCheck(AgentType.HILL_METRICS);
    results.hillMetrics = hillHealth.status === 'healthy';
  } catch (error) {
    console.warn('Hill metrics agent health check failed:', error);
  }

  try {
    const weatherHealth = await client.healthCheck(AgentType.WEATHER);
    results.weather = weatherHealth.status === 'healthy';
  } catch (error) {
    console.warn('Weather agent health check failed:', error);
  }

  try {
    const equipmentHealth = await client.healthCheck(AgentType.EQUIPMENT);
    results.equipment = equipmentHealth.status === 'healthy';
  } catch (error) {
    console.warn('Equipment agent health check failed:', error);
  }

  return results;
}

/**
 * Create development agent client with mock endpoints
 */
export function createDevelopmentAgentClient(): AgentClient {
  const devConfig: AgentConfiguration = {
    hillMetrics: {
      endpoint: 'http://localhost:8001/jsonrpc',
      timeout: 10000,
      retryAttempts: 2,
      protocol: 'jsonrpc'
    },
    weather: {
      endpoint: 'http://localhost:8002/jsonrpc',
      cacheDuration: 60000, // 1 minute for development
      protocol: 'jsonrpc',
      fallbackData: {
        temperature: 0,
        windSpeed: 5,
        windDirection: 180,
        precipitation: 0,
        visibility: 10000,
        snowConditions: SnowCondition.PACKED_POWDER,
        timestamp: new Date()
      }
    },
    equipment: {
      endpoint: 'http://localhost:8003/jsonrpc',
      updateFrequency: 300000, // 5 minutes for development
      protocol: 'jsonrpc'
    }
  };

  const devRetryConfig: RetryConfiguration = {
    maxAttempts: 2,
    baseDelay: 500,
    maxDelay: 2000,
    backoffMultiplier: 1.5,
    retryableErrors: [-32603, -32001, -32004]
  };

  return createAgentClient(devConfig, devRetryConfig);
}

/**
 * Create production agent client with optimized settings
 */
export function createProductionAgentClient(): AgentClient {
  const prodConfig = createAgentConfigFromEnv();
  const prodRetryConfig = createRetryConfigFromEnv();
  
  return createAgentClient(prodConfig, prodRetryConfig);
}

/**
 * Agent status monitoring utility
 */
export class AgentMonitor {
  private client: AgentClient;
  private monitoringInterval: number | null = null;
  private statusCallbacks: Array<(status: AgentStatus) => void> = [];

  constructor(client: AgentClient) {
    this.client = client;
  }

  /**
   * Start monitoring agent health
   */
  startMonitoring(intervalMs: number = 30000): void {
    if (this.monitoringInterval) {
      this.stopMonitoring();
    }

    this.monitoringInterval = setInterval(async () => {
      const status = await this.checkAllAgents();
      this.notifyStatusCallbacks(status);
    }, intervalMs);
  }

  /**
   * Stop monitoring
   */
  stopMonitoring(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
  }

  /**
   * Add status change callback
   */
  onStatusChange(callback: (status: AgentStatus) => void): void {
    this.statusCallbacks.push(callback);
  }

  /**
   * Remove status change callback
   */
  removeStatusCallback(callback: (status: AgentStatus) => void): void {
    const index = this.statusCallbacks.indexOf(callback);
    if (index > -1) {
      this.statusCallbacks.splice(index, 1);
    }
  }

  /**
   * Check all agent statuses
   */
  private async checkAllAgents(): Promise<AgentStatus> {
    const connectivity = await testAgentConnectivity(this.client);
    
    return {
      hillMetrics: connectivity.hillMetrics ? 'healthy' : 'unhealthy',
      weather: connectivity.weather ? 'healthy' : 'unhealthy',
      equipment: connectivity.equipment ? 'healthy' : 'unhealthy',
      timestamp: new Date()
    };
  }

  /**
   * Notify all status callbacks
   */
  private notifyStatusCallbacks(status: AgentStatus): void {
    this.statusCallbacks.forEach(callback => {
      try {
        callback(status);
      } catch (error) {
        console.error('Error in agent status callback:', error);
      }
    });
  }
}

/**
 * Agent status interface
 */
export interface AgentStatus {
  hillMetrics: 'healthy' | 'unhealthy';
  weather: 'healthy' | 'unhealthy';
  equipment: 'healthy' | 'unhealthy';
  timestamp: Date;
}

/**
 * Validate agent configuration
 */
export function validateAgentConfig(config: AgentConfiguration): string[] {
  const errors: string[] = [];

  // Validate endpoints
  if (!config.hillMetrics.endpoint) {
    errors.push('Hill metrics endpoint is required');
  }
  if (!config.weather.endpoint) {
    errors.push('Weather endpoint is required');
  }
  if (!config.equipment.endpoint) {
    errors.push('Equipment endpoint is required');
  }

  // Validate timeouts
  if (config.hillMetrics.timeout <= 0) {
    errors.push('Hill metrics timeout must be positive');
  }
  if (config.weather.cacheDuration <= 0) {
    errors.push('Weather cache duration must be positive');
  }
  if (config.equipment.updateFrequency <= 0) {
    errors.push('Equipment update frequency must be positive');
  }

  // Validate protocols
  const validProtocols = ['jsonrpc', 'mcp'];
  if (!validProtocols.includes(config.hillMetrics.protocol)) {
    errors.push('Hill metrics protocol must be jsonrpc or mcp');
  }
  if (!validProtocols.includes(config.weather.protocol)) {
    errors.push('Weather protocol must be jsonrpc or mcp');
  }
  if (!validProtocols.includes(config.equipment.protocol)) {
    errors.push('Equipment protocol must be jsonrpc or mcp');
  }

  return errors;
}