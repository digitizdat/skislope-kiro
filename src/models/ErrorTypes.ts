/**
 * Error handling types and response models
 * Requirements: 1.4, 5.4, 8.5 - Comprehensive error handling and graceful degradation
 */

import { GridSize } from './TerrainData';
import { AgentType } from './AgentTypes';

/**
 * Environment Viewer specific error types
 */
export enum EnvironmentViewerError {
  // Terrain related errors
  TERRAIN_DATA_UNAVAILABLE = 'terrain-data-unavailable',
  TERRAIN_PROCESSING_FAILED = 'terrain-processing-failed',
  INVALID_GRID_SIZE = 'invalid-grid-size',
  
  // Agent communication errors
  AGENT_CONNECTION_FAILED = 'agent-connection-failed',
  AGENT_TIMEOUT = 'agent-timeout',
  AGENT_UNAVAILABLE = 'agent-unavailable',
  
  // Rendering errors
  RENDERING_FAILED = 'rendering-failed',
  WEBGL_NOT_SUPPORTED = 'webgl-not-supported',
  INSUFFICIENT_MEMORY = 'insufficient-memory',
  
  // Camera and navigation errors
  CAMERA_NAVIGATION_ERROR = 'camera-navigation-error',
  CAMERA_INITIALIZATION_FAILED = 'camera-initialization-failed',
  
  // Protocol errors
  MCP_PROTOCOL_ERROR = 'mcp-protocol-error',
  JSONRPC_PROTOCOL_ERROR = 'jsonrpc-protocol-error',
  
  // Performance errors
  PERFORMANCE_DEGRADED = 'performance-degraded',
  FRAME_RATE_TOO_LOW = 'frame-rate-too-low',
  
  // Data errors
  DATA_CORRUPTION = 'data-corruption',
  CACHE_ERROR = 'cache-error',
  NETWORK_ERROR = 'network-error'
}

/**
 * Error severity levels
 */
export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

/**
 * Error recovery strategies
 */
export enum RecoveryStrategy {
  RETRY = 'retry',
  FALLBACK = 'fallback',
  DEGRADE = 'degrade',
  RESTART = 'restart',
  MANUAL = 'manual'
}

/**
 * Base error response interface
 */
export interface ErrorResponse {
  error: EnvironmentViewerError;
  message: string;
  details?: Record<string, any>;
  timestamp: Date;
  severity: ErrorSeverity;
  recoveryStrategy: RecoveryStrategy;
  context?: ErrorContext;
}

/**
 * Error context for debugging and recovery
 */
export interface ErrorContext {
  area?: string;
  gridSize?: GridSize;
  agentType?: AgentType;
  userAgent?: string;
  url?: string;
  stackTrace?: string;
  performanceMetrics?: {
    fps: number;
    memoryUsage: number;
    loadTime: number;
  };
}

/**
 * Agent-specific error class
 */
export class AgentError extends Error {
  public readonly agentType: AgentType;
  public readonly endpoint: string;
  public readonly originalError: any;
  public readonly timestamp: Date;

  constructor(
    agentType: AgentType,
    endpoint: string,
    originalError: any,
    message?: string
  ) {
    super(message || `Agent ${agentType} at ${endpoint} failed: ${originalError.message}`);
    this.name = 'AgentError';
    this.agentType = agentType;
    this.endpoint = endpoint;
    this.originalError = originalError;
    this.timestamp = new Date();
  }
}

/**
 * Terrain processing error class
 */
export class TerrainError extends Error {
  public readonly gridSize: GridSize;
  public readonly area: string;
  public readonly processingStage: string;
  public readonly timestamp: Date;

  constructor(
    gridSize: GridSize,
    area: string,
    processingStage: string,
    message: string
  ) {
    super(`Terrain processing failed for ${area} (${gridSize}) at ${processingStage}: ${message}`);
    this.name = 'TerrainError';
    this.gridSize = gridSize;
    this.area = area;
    this.processingStage = processingStage;
    this.timestamp = new Date();
  }
}

/**
 * Rendering error class
 */
export class RenderingError extends Error {
  public readonly renderingStage: string;
  public readonly webglError?: number;
  public readonly timestamp: Date;

  constructor(
    renderingStage: string,
    message: string,
    webglError?: number
  ) {
    super(`Rendering failed at ${renderingStage}: ${message}`);
    this.name = 'RenderingError';
    this.renderingStage = renderingStage;
    this.webglError = webglError;
    this.timestamp = new Date();
  }
}

/**
 * Performance error class
 */
export class PerformanceError extends Error {
  public readonly metric: string;
  public readonly currentValue: number;
  public readonly threshold: number;
  public readonly timestamp: Date;

  constructor(
    metric: string,
    currentValue: number,
    threshold: number,
    message?: string
  ) {
    super(message || `Performance threshold exceeded for ${metric}: ${currentValue} (threshold: ${threshold})`);
    this.name = 'PerformanceError';
    this.metric = metric;
    this.currentValue = currentValue;
    this.threshold = threshold;
    this.timestamp = new Date();
  }
}

/**
 * Error recovery options for user interaction
 */
export interface RecoveryOption {
  id: string;
  label: string;
  description: string;
  action: () => Promise<void>;
  severity: ErrorSeverity;
}

/**
 * Error handler configuration
 */
export interface ErrorHandlerConfig {
  enableRetry: boolean;
  maxRetryAttempts: number;
  retryDelay: number;
  enableFallback: boolean;
  enableDegradation: boolean;
  logErrors: boolean;
  showUserNotifications: boolean;
}

/**
 * Default error handler configuration
 */
export const DEFAULT_ERROR_CONFIG: ErrorHandlerConfig = {
  enableRetry: true,
  maxRetryAttempts: 3,
  retryDelay: 1000,
  enableFallback: true,
  enableDegradation: true,
  logErrors: true,
  showUserNotifications: true
};

/**
 * Error mapping for user-friendly messages
 */
export const ERROR_MESSAGES: Record<EnvironmentViewerError, string> = {
  [EnvironmentViewerError.TERRAIN_DATA_UNAVAILABLE]: 'Terrain data is currently unavailable. Please try again later.',
  [EnvironmentViewerError.TERRAIN_PROCESSING_FAILED]: 'Failed to process terrain data. The system will attempt to use cached data.',
  [EnvironmentViewerError.INVALID_GRID_SIZE]: 'The selected grid size is not supported on your device. Please choose a smaller size.',
  [EnvironmentViewerError.AGENT_CONNECTION_FAILED]: 'Unable to connect to data servers. Some features may be limited.',
  [EnvironmentViewerError.AGENT_TIMEOUT]: 'Data server is taking too long to respond. Please check your connection.',
  [EnvironmentViewerError.AGENT_UNAVAILABLE]: 'Data server is temporarily unavailable. Using cached data.',
  [EnvironmentViewerError.RENDERING_FAILED]: 'Graphics rendering failed. Please refresh the page or try a different browser.',
  [EnvironmentViewerError.WEBGL_NOT_SUPPORTED]: 'Your browser does not support WebGL. Please use a modern browser.',
  [EnvironmentViewerError.INSUFFICIENT_MEMORY]: 'Insufficient memory for the selected detail level. Please choose a smaller grid size.',
  [EnvironmentViewerError.CAMERA_NAVIGATION_ERROR]: 'Camera navigation error occurred. Resetting to default view.',
  [EnvironmentViewerError.CAMERA_INITIALIZATION_FAILED]: 'Failed to initialize camera system. Please refresh the page.',
  [EnvironmentViewerError.MCP_PROTOCOL_ERROR]: 'Communication protocol error. Switching to backup protocol.',
  [EnvironmentViewerError.JSONRPC_PROTOCOL_ERROR]: 'Data communication error. Please check your connection.',
  [EnvironmentViewerError.PERFORMANCE_DEGRADED]: 'Performance has degraded. Reducing visual quality to maintain smooth operation.',
  [EnvironmentViewerError.FRAME_RATE_TOO_LOW]: 'Frame rate is too low. Consider reducing the grid size for better performance.',
  [EnvironmentViewerError.DATA_CORRUPTION]: 'Data corruption detected. Clearing cache and reloading.',
  [EnvironmentViewerError.CACHE_ERROR]: 'Cache system error. Some data may need to be reloaded.',
  [EnvironmentViewerError.NETWORK_ERROR]: 'Network connection error. Please check your internet connection.'
};

/**
 * Error recovery strategies mapping
 */
export const RECOVERY_STRATEGIES: Record<EnvironmentViewerError, RecoveryStrategy> = {
  [EnvironmentViewerError.TERRAIN_DATA_UNAVAILABLE]: RecoveryStrategy.FALLBACK,
  [EnvironmentViewerError.TERRAIN_PROCESSING_FAILED]: RecoveryStrategy.FALLBACK,
  [EnvironmentViewerError.INVALID_GRID_SIZE]: RecoveryStrategy.DEGRADE,
  [EnvironmentViewerError.AGENT_CONNECTION_FAILED]: RecoveryStrategy.RETRY,
  [EnvironmentViewerError.AGENT_TIMEOUT]: RecoveryStrategy.RETRY,
  [EnvironmentViewerError.AGENT_UNAVAILABLE]: RecoveryStrategy.FALLBACK,
  [EnvironmentViewerError.RENDERING_FAILED]: RecoveryStrategy.RESTART,
  [EnvironmentViewerError.WEBGL_NOT_SUPPORTED]: RecoveryStrategy.MANUAL,
  [EnvironmentViewerError.INSUFFICIENT_MEMORY]: RecoveryStrategy.DEGRADE,
  [EnvironmentViewerError.CAMERA_NAVIGATION_ERROR]: RecoveryStrategy.RESTART,
  [EnvironmentViewerError.CAMERA_INITIALIZATION_FAILED]: RecoveryStrategy.RESTART,
  [EnvironmentViewerError.MCP_PROTOCOL_ERROR]: RecoveryStrategy.FALLBACK,
  [EnvironmentViewerError.JSONRPC_PROTOCOL_ERROR]: RecoveryStrategy.RETRY,
  [EnvironmentViewerError.PERFORMANCE_DEGRADED]: RecoveryStrategy.DEGRADE,
  [EnvironmentViewerError.FRAME_RATE_TOO_LOW]: RecoveryStrategy.DEGRADE,
  [EnvironmentViewerError.DATA_CORRUPTION]: RecoveryStrategy.RESTART,
  [EnvironmentViewerError.CACHE_ERROR]: RecoveryStrategy.RESTART,
  [EnvironmentViewerError.NETWORK_ERROR]: RecoveryStrategy.RETRY
};

/**
 * Error severity mapping
 */
export const ERROR_SEVERITY: Record<EnvironmentViewerError, ErrorSeverity> = {
  [EnvironmentViewerError.TERRAIN_DATA_UNAVAILABLE]: ErrorSeverity.MEDIUM,
  [EnvironmentViewerError.TERRAIN_PROCESSING_FAILED]: ErrorSeverity.MEDIUM,
  [EnvironmentViewerError.INVALID_GRID_SIZE]: ErrorSeverity.LOW,
  [EnvironmentViewerError.AGENT_CONNECTION_FAILED]: ErrorSeverity.MEDIUM,
  [EnvironmentViewerError.AGENT_TIMEOUT]: ErrorSeverity.LOW,
  [EnvironmentViewerError.AGENT_UNAVAILABLE]: ErrorSeverity.MEDIUM,
  [EnvironmentViewerError.RENDERING_FAILED]: ErrorSeverity.HIGH,
  [EnvironmentViewerError.WEBGL_NOT_SUPPORTED]: ErrorSeverity.CRITICAL,
  [EnvironmentViewerError.INSUFFICIENT_MEMORY]: ErrorSeverity.HIGH,
  [EnvironmentViewerError.CAMERA_NAVIGATION_ERROR]: ErrorSeverity.MEDIUM,
  [EnvironmentViewerError.CAMERA_INITIALIZATION_FAILED]: ErrorSeverity.HIGH,
  [EnvironmentViewerError.MCP_PROTOCOL_ERROR]: ErrorSeverity.LOW,
  [EnvironmentViewerError.JSONRPC_PROTOCOL_ERROR]: ErrorSeverity.MEDIUM,
  [EnvironmentViewerError.PERFORMANCE_DEGRADED]: ErrorSeverity.MEDIUM,
  [EnvironmentViewerError.FRAME_RATE_TOO_LOW]: ErrorSeverity.MEDIUM,
  [EnvironmentViewerError.DATA_CORRUPTION]: ErrorSeverity.HIGH,
  [EnvironmentViewerError.CACHE_ERROR]: ErrorSeverity.LOW,
  [EnvironmentViewerError.NETWORK_ERROR]: ErrorSeverity.MEDIUM
};