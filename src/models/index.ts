/**
 * Core data models and TypeScript interfaces
 * Central export point for all model types
 */

// Ski Area models
export * from './SkiArea';

// Ski Run models
export type { 
  SkiRun, 
  RunMetadata, 
  RunStatistics, 
  ValidationResult, 
  TopographicalData, 
  ContourLine, 
  ElevationPoint
} from './SkiRun';
export {
  calculateDistance,
  calculatePolygonArea,
  calculateBoundingBox
} from './SkiRun';

// Terrain data models
export { GridSize } from './TerrainData';
export type { TerrainData } from './TerrainData';

// Camera state models
export * from './CameraState';

// Agent communication models
export * from './AgentTypes';

// Error handling models
export * from './ErrorTypes';