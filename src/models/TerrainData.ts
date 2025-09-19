/**
 * Terrain data structures and grid size definitions
 * Requirements: 7.2, 7.3 - Grid size options and terrain detail levels
 */

import { SkiArea, GeographicBounds } from './SkiArea';

/**
 * Grid size enumeration for terrain detail levels
 * Requirements: 7.2 - Grid size selector from 32x32 to 128x128
 */
export enum GridSize {
  SMALL = '32x32',
  MEDIUM = '64x64', 
  LARGE = '96x96',
  EXTRA_LARGE = '128x128'
}

/**
 * Surface type classification for terrain rendering
 */
export enum SurfaceType {
  POWDER = 'powder',
  PACKED = 'packed',
  ICE = 'ice',
  MOGULS = 'moguls',
  TREES = 'trees',
  ROCKS = 'rocks'
}

/**
 * Snow condition types for weather integration
 */
export enum SnowCondition {
  POWDER = 'powder',
  PACKED_POWDER = 'packed-powder',
  HARD_PACK = 'hard-pack',
  ICE = 'ice',
  SLUSH = 'slush',
  ARTIFICIAL = 'artificial'
}

/**
 * Time of day enumeration for lighting
 */
export enum TimeOfDay {
  DAWN = 'dawn',
  MORNING = 'morning',
  NOON = 'noon', 
  AFTERNOON = 'afternoon',
  DUSK = 'dusk',
  NIGHT = 'night'
}

/**
 * Hill metrics data from agent servers
 */
export interface HillMetrics {
  elevationData: number[][];
  slopeAngles: number[][];
  aspectAngles: number[][];
  surfaceTypes: SurfaceType[][];
  safetyZones?: SafetyZone[]; // For FIS compatibility
  courseMarkers?: CourseMarker[]; // For FIS compatibility
}

/**
 * Weather data from weather agent
 */
export interface WeatherData {
  temperature: number;
  windSpeed: number;
  windDirection: number;
  precipitation: number;
  visibility: number;
  snowConditions: SnowCondition;
  timestamp: Date;
}

/**
 * Equipment data from equipment agent
 */
export interface EquipmentData {
  lifts: LiftInfo[];
  trails: TrailInfo[];
  facilities: FacilityInfo[];
  safetyEquipment: SafetyEquipment[];
}

/**
 * Core terrain data structure
 */
export interface TerrainData {
  elevationGrid: number[][];
  resolution: number;
  bounds: GeographicBounds;
  metadata: AreaMetadata;
  surfaceTypes: SurfaceType[][];
  gridSize: GridSize;
  area: SkiArea;
  hillMetrics: HillMetrics;
}

/**
 * Area metadata for terrain information
 */
export interface AreaMetadata {
  name: string;
  country: string;
  verticalDrop: number;
  totalLength: number;
  difficulty: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  lastUpdated: Date;
}

/**
 * Level of Detail configuration
 */
export interface LODLevel {
  distance: number;
  vertexReduction: number;
  textureResolution: number;
}

/**
 * Surface visual properties for rendering
 */
export interface SurfaceVisuals {
  color: string;
  roughness: number;
  metallic: number;
  normalMap?: string;
  displacementMap?: string;
}

/**
 * Lighting configuration for different times of day
 */
export interface LightingConfiguration {
  sunPosition: [number, number, number]; // Vector3 as array
  sunIntensity: number;
  sunColor: string;
  ambientColor: string;
  ambientIntensity: number;
  fogColor: string;
  fogDensity: number;
}

// FIS World Cup Compatibility Models
export interface SafetyZone {
  id: string;
  type: 'barrier' | 'net' | 'padding';
  coordinates: [number, number, number][]; // Vector3 array
  height: number;
}

export interface CourseMarker {
  id: string;
  type: 'gate' | 'start' | 'finish' | 'timing';
  position: [number, number, number]; // Vector3 as array
  orientation: number;
}

// Equipment data structures
export interface LiftInfo {
  id: string;
  name: string;
  type: 'chairlift' | 'gondola' | 'surface' | 'funicular';
  capacity: number;
  status: 'operational' | 'maintenance' | 'closed';
  startPosition: [number, number, number];
  endPosition: [number, number, number];
}

export interface TrailInfo {
  id: string;
  name: string;
  difficulty: 'green' | 'blue' | 'black' | 'double-black';
  length: number;
  status: 'open' | 'closed' | 'groomed';
  conditions: SnowCondition;
  path: [number, number, number][];
}

export interface FacilityInfo {
  id: string;
  name: string;
  type: 'lodge' | 'restaurant' | 'shop' | 'rental' | 'medical';
  position: [number, number, number];
  status: 'open' | 'closed';
  amenities: string[];
}

export interface SafetyEquipment {
  id: string;
  type: 'patrol-station' | 'first-aid' | 'emergency-phone' | 'avalanche-beacon';
  position: [number, number, number];
  status: 'active' | 'inactive';
}

/**
 * Surface properties mapping for rendering
 */
export const SURFACE_PROPERTIES: Record<SurfaceType, SurfaceVisuals> = {
  [SurfaceType.POWDER]: { color: '#ffffff', roughness: 0.8, metallic: 0.0 },
  [SurfaceType.PACKED]: { color: '#f0f0f0', roughness: 0.3, metallic: 0.0 },
  [SurfaceType.ICE]: { color: '#e0f7ff', roughness: 0.1, metallic: 0.2 },
  [SurfaceType.MOGULS]: { color: '#ffffff', roughness: 0.9, metallic: 0.0 },
  [SurfaceType.TREES]: { color: '#228b22', roughness: 1.0, metallic: 0.0 },
  [SurfaceType.ROCKS]: { color: '#8b4513', roughness: 0.7, metallic: 0.1 }
};

/**
 * Helper functions for grid size operations
 */
export function getGridDimensions(gridSize: GridSize): { width: number; height: number } {
  const [width, height] = gridSize.split('x').map(Number);
  return { width, height };
}

export function getGridCellCount(gridSize: GridSize): number {
  const { width, height } = getGridDimensions(gridSize);
  return width * height;
}

export function isHighDetailGrid(gridSize: GridSize): boolean {
  return gridSize === GridSize.LARGE || gridSize === GridSize.EXTRA_LARGE;
}