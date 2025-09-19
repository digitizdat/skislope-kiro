/**
 * Agent Client Service - JSON-RPC and MCP communication with agent servers
 * Requirements: 8.1, 8.2, 8.5 - Agent communication, error handling, health checks
 */

import {
  AgentType,
  AgentClientInterface,
  JSONRPCRequest,
  JSONRPCResponse,
  JSONRPCErrorCode,
  MCPRequest,
  MCPResponse,
  HillMetricsRequest,
  HillMetricsResponse,
  WeatherRequest,
  WeatherResponse,
  EquipmentRequest,
  EquipmentResponse,
  HealthCheckRequest,
  HealthCheckResponse,
  AgentInfo,
  BatchRequest,
  BatchResponse,
  RetryConfiguration,
  DEFAULT_RETRY_CONFIG,
  AgentConfiguration
} from '../models/AgentTypes';

/**
 * Agent communication error class
 */
export class AgentError extends Error {
  constructor(
    public agentType: AgentType,
    public endpoint: string,
    public originalError: any,
    public code?: number
  ) {
    super(`Agent ${agentType} at ${endpoint} failed: ${originalError.message || originalError}`);
    this.name = 'AgentError';
  }
}

/**
 * Agent Client implementation with JSON-RPC and MCP support
 */
export class AgentClient implements AgentClientInterface {
  private config: AgentConfiguration;
  private retryConfig: RetryConfiguration;
  private requestId: number = 1;

  constructor(config: AgentConfiguration, retryConfig: RetryConfiguration = DEFAULT_RETRY_CONFIG) {
    this.config = config;
    this.retryConfig = retryConfig;
  }

  /**
   * Call Hill Metrics Agent
   * Requirements: 8.1 - JSON-RPC communication for hill metrics
   */
  async callHillMetricsAgent(request: HillMetricsRequest): Promise<HillMetricsResponse> {
    const endpoint = this.config.hillMetrics.endpoint;
    const protocol = this.config.hillMetrics.protocol;
    const timeout = this.config.hillMetrics.timeout;

    try {
      if (protocol === 'mcp') {
        return await this.callMCPAgent<HillMetricsRequest, HillMetricsResponse>(
          endpoint,
          'getHillMetrics',
          request,
          timeout
        );
      } else {
        return await this.callJSONRPCAgent<HillMetricsRequest, HillMetricsResponse>(
          endpoint,
          'getHillMetrics',
          request,
          timeout
        );
      }
    } catch (error) {
      throw new AgentError(AgentType.HILL_METRICS, endpoint, error);
    }
  }

  /**
   * Call Weather Agent
   * Requirements: 8.1 - JSON-RPC communication for weather data
   */
  async callWeatherAgent(request: WeatherRequest): Promise<WeatherResponse> {
    const endpoint = this.config.weather.endpoint;
    const protocol = this.config.weather.protocol;
    const timeout = this.config.weather.cacheDuration;

    try {
      if (protocol === 'mcp') {
        return await this.callMCPAgent<WeatherRequest, WeatherResponse>(
          endpoint,
          'getWeatherData',
          request,
          timeout
        );
      } else {
        return await this.callJSONRPCAgent<WeatherRequest, WeatherResponse>(
          endpoint,
          'getWeatherData',
          request,
          timeout
        );
      }
    } catch (error) {
      // Try fallback data if available
      if (this.config.weather.fallbackData) {
        console.warn('Weather agent failed, using fallback data:', error);
        return {
          current: this.config.weather.fallbackData,
          metadata: {
            source: 'fallback',
            lastUpdated: new Date(),
            accuracy: 0.5
          }
        };
      }
      throw new AgentError(AgentType.WEATHER, endpoint, error);
    }
  }

  /**
   * Call Equipment Agent
   * Requirements: 8.1 - JSON-RPC communication for equipment data
   */
  async callEquipmentAgent(request: EquipmentRequest): Promise<EquipmentResponse> {
    const endpoint = this.config.equipment.endpoint;
    const protocol = this.config.equipment.protocol;
    const timeout = 10000; // Default timeout

    try {
      if (protocol === 'mcp') {
        return await this.callMCPAgent<EquipmentRequest, EquipmentResponse>(
          endpoint,
          'getEquipmentData',
          request,
          timeout
        );
      } else {
        return await this.callJSONRPCAgent<EquipmentRequest, EquipmentResponse>(
          endpoint,
          'getEquipmentData',
          request,
          timeout
        );
      }
    } catch (error) {
      throw new AgentError(AgentType.EQUIPMENT, endpoint, error);
    }
  }

  /**
   * Health check for agent servers
   * Requirements: 8.5 - Health check functionality
   */
  async healthCheck(agentType: AgentType): Promise<HealthCheckResponse> {
    const endpoint = this.getEndpointForAgent(agentType);
    const startTime = Date.now();

    try {
      const request: HealthCheckRequest = {
        agentType,
        includeMetrics: true
      };

      const response = await this.callJSONRPCAgent<HealthCheckRequest, HealthCheckResponse>(
        endpoint,
        'healthCheck',
        request,
        5000 // Short timeout for health checks
      );

      response.responseTime = Date.now() - startTime;
      return response;
    } catch (error) {
      return {
        status: 'unhealthy',
        timestamp: new Date(),
        responseTime: Date.now() - startTime,
        version: 'unknown'
      };
    }
  }

  /**
   * Discover agent capabilities (MCP support)
   * Requirements: 8.4 - MCP protocol support
   */
  async discoverCapabilities(agentType: AgentType): Promise<AgentInfo> {
    const endpoint = this.getEndpointForAgent(agentType);

    try {
      return await this.callMCPAgent<{}, AgentInfo>(
        endpoint,
        'getCapabilities',
        {},
        5000
      );
    } catch (error) {
      throw new AgentError(agentType, endpoint, error);
    }
  }

  /**
   * Set protocol for specific agent
   */
  setProtocol(agentType: AgentType, protocol: 'jsonrpc' | 'mcp'): void {
    switch (agentType) {
      case AgentType.HILL_METRICS:
        this.config.hillMetrics.protocol = protocol;
        break;
      case AgentType.WEATHER:
        this.config.weather.protocol = protocol;
        break;
      case AgentType.EQUIPMENT:
        this.config.equipment.protocol = protocol;
        break;
    }
  }

  /**
   * Enable MCP mode for all agents
   */
  enableMCPMode(): void {
    this.config.hillMetrics.protocol = 'mcp';
    this.config.weather.protocol = 'mcp';
    this.config.equipment.protocol = 'mcp';
  }

  /**
   * Batch request support
   */
  async batchRequest(request: BatchRequest): Promise<BatchResponse> {
    const startTime = Date.now();
    const responses: any[] = [];
    const errors: any[] = [];

    if (request.parallel) {
      // Execute requests in parallel
      const promises = request.requests.map(async (req) => {
        try {
          const response = await this.executeRequest(req);
          responses.push(response);
        } catch (error) {
          errors.push(error);
        }
      });

      await Promise.allSettled(promises);
    } else {
      // Execute requests sequentially
      for (const req of request.requests) {
        try {
          const response = await this.executeRequest(req);
          responses.push(response);
        } catch (error) {
          errors.push(error);
        }
      }
    }

    return {
      responses,
      errors,
      metadata: {
        totalTime: Date.now() - startTime,
        successCount: responses.length,
        errorCount: errors.length
      }
    };
  }

  /**
   * Execute individual request based on type
   */
  private async executeRequest(request: any): Promise<any> {
    if ('area' in request && 'gridSize' in request) {
      return await this.callHillMetricsAgent(request as HillMetricsRequest);
    } else if ('area' in request && 'timestamp' in request) {
      return await this.callWeatherAgent(request as WeatherRequest);
    } else if ('area' in request && 'includeStatus' in request) {
      return await this.callEquipmentAgent(request as EquipmentRequest);
    }
    throw new Error('Unknown request type');
  }

  /**
   * JSON-RPC client implementation with retry logic
   * Requirements: 8.2 - Error handling and retry logic with exponential backoff
   */
  private async callJSONRPCAgent<TRequest, TResponse>(
    endpoint: string,
    method: string,
    params: TRequest,
    timeout: number
  ): Promise<TResponse> {
    const request: JSONRPCRequest = {
      jsonrpc: '2.0',
      method,
      params: params as Record<string, any>,
      id: this.requestId++
    };

    return await this.executeWithRetry(async () => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const jsonResponse: JSONRPCResponse<TResponse> = await response.json();

        if (jsonResponse.error) {
          const error = new Error(jsonResponse.error.message);
          (error as any).code = jsonResponse.error.code;
          (error as any).data = jsonResponse.error.data;
          throw error;
        }

        if (!jsonResponse.result) {
          throw new Error('No result in JSON-RPC response');
        }

        return jsonResponse.result;
      } catch (error) {
        clearTimeout(timeoutId);
        if ((error as any).name === 'AbortError') {
          const timeoutError = new Error('Request timeout');
          (timeoutError as any).code = JSONRPCErrorCode.TIMEOUT_ERROR;
          throw timeoutError;
        }
        throw error;
      }
    });
  }

  /**
   * MCP client implementation
   * Requirements: 8.4 - MCP protocol support
   */
  private async callMCPAgent<TRequest, TResponse>(
    endpoint: string,
    method: string,
    params: TRequest,
    timeout: number
  ): Promise<TResponse> {
    const request: MCPRequest = {
      method,
      params: params as Record<string, any>,
      id: this.requestId++
    };

    return await this.executeWithRetry(async () => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Protocol': 'MCP'
          },
          body: JSON.stringify(request),
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const mcpResponse: MCPResponse<TResponse> = await response.json();

        if (mcpResponse.error) {
          const error = new Error(mcpResponse.error.message);
          (error as any).code = mcpResponse.error.code;
          (error as any).data = mcpResponse.error.data;
          throw error;
        }

        if (!mcpResponse.result) {
          throw new Error('No result in MCP response');
        }

        return mcpResponse.result;
      } catch (error) {
        clearTimeout(timeoutId);
        if ((error as any).name === 'AbortError') {
          const timeoutError = new Error('Request timeout');
          (timeoutError as any).code = JSONRPCErrorCode.TIMEOUT_ERROR;
          throw timeoutError;
        }
        throw error;
      }
    });
  }

  /**
   * Execute request with exponential backoff retry logic
   * Requirements: 8.2 - Exponential backoff retry logic
   */
  private async executeWithRetry<T>(operation: () => Promise<T>): Promise<T> {
    let lastError: any;
    let delay = this.retryConfig.baseDelay;

    for (let attempt = 1; attempt <= this.retryConfig.maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;

        // Check if error is retryable
        const errorCode = (error as any).code;
        if (!this.retryConfig.retryableErrors.includes(errorCode) && errorCode !== undefined) {
          throw error;
        }

        // Don't retry on last attempt
        if (attempt === this.retryConfig.maxAttempts) {
          break;
        }

        // Wait before retry with exponential backoff
        await this.sleep(Math.min(delay, this.retryConfig.maxDelay));
        delay *= this.retryConfig.backoffMultiplier;

        console.warn(`Agent request failed (attempt ${attempt}/${this.retryConfig.maxAttempts}), retrying in ${delay}ms:`, error);
      }
    }

    throw lastError;
  }

  /**
   * Get endpoint for specific agent type
   */
  private getEndpointForAgent(agentType: AgentType): string {
    switch (agentType) {
      case AgentType.HILL_METRICS:
        return this.config.hillMetrics.endpoint;
      case AgentType.WEATHER:
        return this.config.weather.endpoint;
      case AgentType.EQUIPMENT:
        return this.config.equipment.endpoint;
      default:
        throw new Error(`Unknown agent type: ${agentType}`);
    }
  }

  /**
   * Sleep utility for retry delays
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Default agent configuration
 */
export const DEFAULT_AGENT_CONFIG: AgentConfiguration = {
  hillMetrics: {
    endpoint: 'http://localhost:8001/jsonrpc',
    timeout: 30000,
    retryAttempts: 3,
    protocol: 'jsonrpc'
  },
  weather: {
    endpoint: 'http://localhost:8002/jsonrpc',
    cacheDuration: 300000, // 5 minutes
    protocol: 'jsonrpc'
  },
  equipment: {
    endpoint: 'http://localhost:8003/jsonrpc',
    updateFrequency: 600000, // 10 minutes
    protocol: 'jsonrpc'
  }
};

/**
 * Create and export agent client instance
 */
export const agentClient = new AgentClient(DEFAULT_AGENT_CONFIG);

/**
 * Agent client factory for custom configurations
 */
export function createAgentClient(
  config: Partial<AgentConfiguration>,
  retryConfig?: Partial<RetryConfiguration>
): AgentClient {
  const fullConfig = {
    ...DEFAULT_AGENT_CONFIG,
    ...config,
    hillMetrics: { ...DEFAULT_AGENT_CONFIG.hillMetrics, ...config.hillMetrics },
    weather: { ...DEFAULT_AGENT_CONFIG.weather, ...config.weather },
    equipment: { ...DEFAULT_AGENT_CONFIG.equipment, ...config.equipment }
  };

  const fullRetryConfig = { ...DEFAULT_RETRY_CONFIG, ...retryConfig };

  return new AgentClient(fullConfig, fullRetryConfig);
}