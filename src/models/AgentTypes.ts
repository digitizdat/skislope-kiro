/**
 * Agent communication interfaces for JSON-RPC and MCP protocols
 * Requirements: 8.1, 8.4 - Agent server communication via JSON-RPC and MCP protocol support
 */

import { GridSize, HillMetrics, WeatherData, EquipmentData } from './TerrainData';
import { SkiArea } from './SkiArea';

/**
 * Agent types for different data sources
 */
export enum AgentType {
  HILL_METRICS = 'hill-metrics',
  WEATHER = 'weather',
  EQUIPMENT = 'equipment'
}

/**
 * JSON-RPC 2.0 Protocol Interfaces
 * Requirements: 8.1 - JSON-RPC over HTTP communication
 */
export interface JSONRPCRequest {
  jsonrpc: '2.0';
  method: string;
  params: Record<string, any>;
  id: string | number;
}

export interface JSONRPCResponse<T = any> {
  jsonrpc: '2.0';
  result?: T;
  error?: JSONRPCError;
  id: string | number;
}

export interface JSONRPCError {
  code: number;
  message: string;
  data?: any;
}

/**
 * JSON-RPC Error Codes (standard and custom)
 */
export enum JSONRPCErrorCode {
  PARSE_ERROR = -32700,
  INVALID_REQUEST = -32600,
  METHOD_NOT_FOUND = -32601,
  INVALID_PARAMS = -32602,
  INTERNAL_ERROR = -32603,
  // Custom error codes
  AGENT_UNAVAILABLE = -32001,
  DATA_NOT_FOUND = -32002,
  PROCESSING_ERROR = -32003,
  TIMEOUT_ERROR = -32004
}

/**
 * MCP (Model Context Protocol) Interfaces
 * Requirements: 8.4 - MCP protocol support for external tool integration
 */
export interface MCPRequest {
  method: string;
  params?: Record<string, any>;
  id?: string | number;
}

export interface MCPResponse<T = any> {
  result?: T;
  error?: MCPError;
  id?: string | number;
}

export interface MCPError {
  code: number;
  message: string;
  data?: any;
}

/**
 * Agent capability discovery for MCP
 */
export interface AgentCapability {
  name: string;
  description: string;
  inputSchema: Record<string, any>;
  outputSchema: Record<string, any>;
}

export interface AgentInfo {
  name: string;
  version: string;
  capabilities: AgentCapability[];
  protocols: ('jsonrpc' | 'mcp')[];
}

/**
 * Agent request/response interfaces for specific data types
 */

// Hill Metrics Agent
export interface HillMetricsRequest {
  area: SkiArea;
  gridSize: GridSize;
  includeAnalysis?: boolean;
}

export interface HillMetricsResponse {
  data: HillMetrics;
  metadata: {
    processingTime: number;
    dataSource: string;
    lastUpdated: Date;
    gridResolution: GridSize;
  };
}

// Weather Agent
export interface WeatherRequest {
  area: SkiArea;
  timestamp?: Date;
  includeForecast?: boolean;
  forecastHours?: number;
}

export interface WeatherResponse {
  current: WeatherData;
  forecast?: WeatherData[];
  metadata: {
    source: string;
    lastUpdated: Date;
    accuracy: number;
  };
}

// Equipment Agent
export interface EquipmentRequest {
  area: SkiArea;
  includeStatus?: boolean;
  equipmentTypes?: string[];
}

export interface EquipmentResponse {
  data: EquipmentData;
  metadata: {
    lastUpdated: Date;
    source: string;
    statusAccuracy: number;
  };
}

/**
 * Agent client configuration
 */
export interface AgentConfiguration {
  hillMetrics: {
    endpoint: string;
    timeout: number;
    retryAttempts: number;
    protocol: 'jsonrpc' | 'mcp';
  };
  weather: {
    endpoint: string;
    cacheDuration: number;
    fallbackData?: WeatherData;
    protocol: 'jsonrpc' | 'mcp';
  };
  equipment: {
    endpoint: string;
    updateFrequency: number;
    protocol: 'jsonrpc' | 'mcp';
  };
}

/**
 * Agent health check interfaces
 */
export interface HealthCheckRequest {
  agentType: AgentType;
  includeMetrics?: boolean;
}

export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: Date;
  responseTime: number;
  version: string;
  metrics?: {
    uptime: number;
    requestCount: number;
    errorRate: number;
    averageResponseTime: number;
  };
}

/**
 * Batch request support for multiple agent calls
 */
export interface BatchRequest {
  requests: (HillMetricsRequest | WeatherRequest | EquipmentRequest)[];
  parallel?: boolean;
  timeout?: number;
}

export interface BatchResponse {
  responses: (HillMetricsResponse | WeatherResponse | EquipmentResponse)[];
  errors: (JSONRPCError | MCPError)[];
  metadata: {
    totalTime: number;
    successCount: number;
    errorCount: number;
  };
}

/**
 * Agent client interface definition
 */
export interface AgentClientInterface {
  // Core agent methods
  callHillMetricsAgent(request: HillMetricsRequest): Promise<HillMetricsResponse>;
  callWeatherAgent(request: WeatherRequest): Promise<WeatherResponse>;
  callEquipmentAgent(request: EquipmentRequest): Promise<EquipmentResponse>;
  
  // Health and discovery
  healthCheck(agentType: AgentType): Promise<HealthCheckResponse>;
  discoverCapabilities(agentType: AgentType): Promise<AgentInfo>;
  
  // Protocol management
  setProtocol(agentType: AgentType, protocol: 'jsonrpc' | 'mcp'): void;
  enableMCPMode(): void;
  
  // Batch operations
  batchRequest(request: BatchRequest): Promise<BatchResponse>;
}

/**
 * Agent retry configuration
 */
export interface RetryConfiguration {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  backoffMultiplier: number;
  retryableErrors: number[];
}

/**
 * Default retry configuration with exponential backoff
 */
export const DEFAULT_RETRY_CONFIG: RetryConfiguration = {
  maxAttempts: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  backoffMultiplier: 2,
  retryableErrors: [
    JSONRPCErrorCode.INTERNAL_ERROR,
    JSONRPCErrorCode.AGENT_UNAVAILABLE,
    JSONRPCErrorCode.TIMEOUT_ERROR
  ]
};