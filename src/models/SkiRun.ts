/**
 * Ski Run data models for user-defined run boundaries
 * Requirements: 3.3, 3.4, 3.5, 10.5, 10.6, 10.7, 10.8
 */

export interface GeographicCoordinate {
  lat: number;
  lng: number;
}

export interface GeographicBounds {
  northEast: GeographicCoordinate;
  southWest: GeographicCoordinate;
}

export interface RunStatistics {
  estimatedLength: number; // in meters
  verticalDrop: number; // in meters
  averageSlope: number; // in degrees
  boundingBox: GeographicBounds;
  area: number; // in square meters
}

export interface RunMetadata {
  difficulty: 'beginner' | 'intermediate' | 'advanced' | 'expert' | 'custom';
  estimatedLength: number;
  verticalDrop: number;
  averageSlope: number;
  surfaceType: SurfaceType;
  notes?: string;
  tags: string[];
}

export interface SkiRun {
  id: string;
  name: string;
  skiAreaId: string;
  boundary: GeographicCoordinate[];
  metadata: RunMetadata;
  statistics: RunStatistics;
  createdBy: string;
  createdAt: Date;
  lastModified: Date;
  isPublic: boolean;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export enum SurfaceType {
  POWDER = 'powder',
  PACKED = 'packed',
  ICE = 'ice',
  MOGULS = 'moguls',
  TREES = 'trees',
  ROCKS = 'rocks'
}

export interface TopographicalData {
  contourLines: ContourLine[];
  elevationPoints: ElevationPoint[];
  bounds: GeographicBounds;
}

export interface ContourLine {
  elevation: number;
  coordinates: GeographicCoordinate[];
}

export interface ElevationPoint {
  coordinate: GeographicCoordinate;
  elevation: number;
}

/**
 * Helper function to calculate distance between two geographic coordinates
 */
export function calculateDistance(coord1: GeographicCoordinate, coord2: GeographicCoordinate): number {
  const R = 6371000; // Earth's radius in meters
  const dLat = (coord2.lat - coord1.lat) * Math.PI / 180;
  const dLng = (coord2.lng - coord1.lng) * Math.PI / 180;
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(coord1.lat * Math.PI / 180) * Math.cos(coord2.lat * Math.PI / 180) * 
    Math.sin(dLng/2) * Math.sin(dLng/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

/**
 * Helper function to calculate polygon area in square meters
 */
export function calculatePolygonArea(coordinates: GeographicCoordinate[]): number {
  if (coordinates.length < 3) return 0;
  
  const R = 6371000; // Earth's radius in meters
  let area = 0;
  
  for (let i = 0; i < coordinates.length; i++) {
    const j = (i + 1) % coordinates.length;
    const xi = coordinates[i].lng * Math.PI / 180;
    const yi = coordinates[i].lat * Math.PI / 180;
    const xj = coordinates[j].lng * Math.PI / 180;
    const yj = coordinates[j].lat * Math.PI / 180;
    
    area += (xj - xi) * (2 + Math.sin(yi) + Math.sin(yj));
  }
  
  area = Math.abs(area) * R * R / 2;
  return area;
}

/**
 * Helper function to calculate bounding box for coordinates
 */
export function calculateBoundingBox(coordinates: GeographicCoordinate[]): GeographicBounds {
  if (coordinates.length === 0) {
    return {
      northEast: { lat: 0, lng: 0 },
      southWest: { lat: 0, lng: 0 }
    };
  }
  
  let minLat = coordinates[0].lat;
  let maxLat = coordinates[0].lat;
  let minLng = coordinates[0].lng;
  let maxLng = coordinates[0].lng;
  
  for (const coord of coordinates) {
    minLat = Math.min(minLat, coord.lat);
    maxLat = Math.max(maxLat, coord.lat);
    minLng = Math.min(minLng, coord.lng);
    maxLng = Math.max(maxLng, coord.lng);
  }
  
  return {
    northEast: { lat: maxLat, lng: maxLng },
    southWest: { lat: minLat, lng: minLng }
  };
}