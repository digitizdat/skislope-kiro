/**
 * Terrain Service for processing elevation data and generating 3D meshes
 * Requirements: 1.1, 1.2, 1.5, 7.5 - Terrain data processing and mesh generation for run boundaries
 */

import * as THREE from 'three';
import { SkiArea } from '../models/SkiArea';
import { SkiRun, GeographicCoordinate } from '../models/SkiRun';
import { 
  TerrainData, 
  GridSize, 
  SurfaceType, 
  LODLevel,
  SURFACE_PROPERTIES,
  getGridDimensions
} from '../models/TerrainData';
import { agentClient } from './AgentClient';
import { HillMetricsRequest } from '../models/AgentTypes';
import { cacheManager } from '../utils/CacheManager';

/**
 * Terrain mesh data structure for Three.js rendering
 */
export interface TerrainMesh {
  geometry: THREE.BufferGeometry;
  materials: THREE.Material[];
  surfaceTypes: SurfaceType[];
  lodLevels: LODLevel[];
  boundingBox: THREE.Box3;
  gridSize: GridSize;
  area: SkiArea;
}

/**
 * Terrain processing configuration
 */
export interface TerrainProcessingConfig {
  enableLOD: boolean;
  maxLODLevels: number;
  lodDistances: number[];
  vertexReductionFactors: number[];
  textureResolutions: number[];
  smoothingIterations: number;
  heightScale: number;
}

/**
 * Default terrain processing configuration
 */
const DEFAULT_TERRAIN_CONFIG: TerrainProcessingConfig = {
  enableLOD: true,
  maxLODLevels: 4,
  lodDistances: [100, 500, 1000, 2000],
  vertexReductionFactors: [1.0, 0.5, 0.25, 0.125],
  textureResolutions: [1024, 512, 256, 128],
  smoothingIterations: 2,
  heightScale: 1.0
};

/**
 * Terrain service interface
 */
export interface TerrainServiceInterface {
  extractTerrainData(run: SkiRun, gridSize: GridSize): Promise<TerrainData>;
  generateMesh(data: TerrainData): TerrainMesh;
  generateLODMesh(data: TerrainData, lodLevel: number): THREE.BufferGeometry;
  classifySurfaceTypes(data: TerrainData): SurfaceType[][];
  createMaterials(surfaceTypes: SurfaceType[][]): THREE.Material[];
}

/**
 * Terrain Service implementation
 */
export class TerrainService implements TerrainServiceInterface {
  private config: TerrainProcessingConfig;
  private meshCache: Map<string, TerrainMesh> = new Map();

  constructor(config: TerrainProcessingConfig = DEFAULT_TERRAIN_CONFIG) {
    this.config = config;
  }

  /**
   * Extract elevation data within user-defined run boundaries
   * Requirements: 1.1 - Load and render 3D terrain based on real topographical data within run boundaries
   */
  async extractTerrainData(run: SkiRun, gridSize: GridSize): Promise<TerrainData> {
    try {
      // Check cache first
      const cachedData = await cacheManager.getCachedTerrainData(run.id, gridSize);
      if (cachedData) {
        console.log(`Using cached terrain data for run ${run.id} with grid size ${gridSize}`);
        return cachedData;
      }

      // Get the ski area for this run
      const skiArea = await this.getSkiAreaById(run.skiAreaId);
      if (!skiArea) {
        throw new Error(`Ski area not found: ${run.skiAreaId}`);
      }

      // Request hill metrics data from agent server
      const hillMetricsRequest: HillMetricsRequest = {
        area: skiArea,
        gridSize,
        includeAnalysis: true
      };

      const hillMetricsResponse = await agentClient.callHillMetricsAgent(hillMetricsRequest);
      const hillMetrics = hillMetricsResponse.data;

      // Extract elevation data within run boundaries
      const elevationGrid = this.extractElevationWithinBoundary(
        hillMetrics.elevationData,
        run.boundary,
        skiArea,
        gridSize
      );

      // Extract surface types within run boundaries
      const surfaceTypes = this.extractSurfaceTypesWithinBoundary(
        hillMetrics.surfaceTypes,
        run.boundary,
        skiArea,
        gridSize
      );

      // Calculate terrain bounds based on run boundary
      const bounds = this.calculateTerrainBounds(run.boundary);

      // Create terrain data structure
      const terrainData: TerrainData = {
        elevationGrid,
        resolution: this.calculateResolution(bounds, gridSize),
        bounds,
        metadata: {
          name: run.name,
          country: skiArea.country,
          verticalDrop: run.metadata.verticalDrop,
          totalLength: run.metadata.estimatedLength,
          difficulty: run.metadata.difficulty === 'custom' ? 'expert' : run.metadata.difficulty,
          lastUpdated: new Date()
        },
        surfaceTypes,
        gridSize,
        area: skiArea,
        hillMetrics
      };

      // Cache the terrain data
      try {
        await cacheManager.cacheTerrainData(terrainData, run, gridSize);
        console.log(`Cached terrain data for run ${run.id} with grid size ${gridSize}`);
      } catch (cacheError) {
        console.warn('Failed to cache terrain data:', cacheError);
        // Continue without caching - don't fail the entire operation
      }

      return terrainData;
    } catch (error) {
      console.error('Failed to extract terrain data:', error);
      throw new Error(`Terrain data extraction failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Generate 3D mesh from elevation data using Three.js BufferGeometry
   * Requirements: 1.2 - Display accurate elevation changes, slope angles, and terrain features for run area
   */
  generateMesh(data: TerrainData): TerrainMesh {
    const cacheKey = this.generateCacheKey(data);
    
    // Check cache first
    if (this.meshCache.has(cacheKey)) {
      return this.meshCache.get(cacheKey)!;
    }

    const { width, height } = getGridDimensions(data.gridSize);
    const elevationGrid = data.elevationGrid;

    // Create vertices from elevation data
    const vertices: number[] = [];
    const normals: number[] = [];
    const uvs: number[] = [];
    const indices: number[] = [];

    // Generate vertices and UVs
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const elevation = elevationGrid[y] && elevationGrid[y][x] ? elevationGrid[y][x] : 0;
        
        // Convert grid coordinates to world coordinates
        const worldX = (x / (width - 1)) * this.getTerrainWidth(data.bounds);
        const worldZ = (y / (height - 1)) * this.getTerrainHeight(data.bounds);
        const worldY = elevation * this.config.heightScale;

        vertices.push(worldX, worldY, worldZ);
        uvs.push(x / (width - 1), y / (height - 1));
      }
    }

    // Generate indices for triangles
    for (let y = 0; y < height - 1; y++) {
      for (let x = 0; x < width - 1; x++) {
        const a = y * width + x;
        const b = y * width + x + 1;
        const c = (y + 1) * width + x;
        const d = (y + 1) * width + x + 1;

        // Two triangles per quad
        indices.push(a, b, c);
        indices.push(b, d, c);
      }
    }

    // Calculate normals
    this.calculateNormals(vertices, indices, normals);

    // Apply smoothing if configured
    if (this.config.smoothingIterations > 0) {
      this.smoothVertices(vertices, indices, width, height, this.config.smoothingIterations);
      this.calculateNormals(vertices, indices, normals); // Recalculate after smoothing
    }

    // Create BufferGeometry
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    geometry.setIndex(indices);

    // Calculate bounding box
    geometry.computeBoundingBox();
    const boundingBox = geometry.boundingBox!;

    // Generate surface type classification
    const surfaceTypes = this.classifySurfaceTypes(data);

    // Create materials for different surface types
    const materials = this.createMaterials(surfaceTypes);

    // Generate LOD levels if enabled
    const lodLevels: LODLevel[] = [];
    if (this.config.enableLOD) {
      for (let i = 0; i < this.config.maxLODLevels; i++) {
        lodLevels.push({
          distance: this.config.lodDistances[i] || 1000 * (i + 1),
          vertexReduction: this.config.vertexReductionFactors[i] || Math.pow(0.5, i),
          textureResolution: this.config.textureResolutions[i] || 512 / Math.pow(2, i),
          geometry: this.generateLODMesh(data, i)
        });
      }
    }

    const terrainMesh: TerrainMesh = {
      geometry,
      materials,
      surfaceTypes: this.flattenSurfaceTypes(surfaceTypes),
      lodLevels,
      boundingBox,
      gridSize: data.gridSize,
      area: data.area
    };

    // Cache the result
    this.meshCache.set(cacheKey, terrainMesh);

    return terrainMesh;
  }

  /**
   * Generate LOD mesh with reduced vertex count
   * Requirements: 7.5 - LOD system for different grid sizes applied to run boundaries
   */
  generateLODMesh(data: TerrainData, lodLevel: number): THREE.BufferGeometry {
    const reductionFactor = this.config.vertexReductionFactors[lodLevel] || 1.0;
    const { width, height } = getGridDimensions(data.gridSize);
    
    // Calculate reduced dimensions
    const lodWidth = Math.max(2, Math.floor(width * reductionFactor));
    const lodHeight = Math.max(2, Math.floor(height * reductionFactor));

    const vertices: number[] = [];
    const normals: number[] = [];
    const uvs: number[] = [];
    const indices: number[] = [];

    // Sample elevation data at reduced resolution
    for (let y = 0; y < lodHeight; y++) {
      for (let x = 0; x < lodWidth; x++) {
        // Map LOD coordinates back to original grid
        const origX = Math.floor((x / (lodWidth - 1)) * (width - 1));
        const origY = Math.floor((y / (lodHeight - 1)) * (height - 1));
        
        const elevation = data.elevationGrid[origY] && data.elevationGrid[origY][origX] 
          ? data.elevationGrid[origY][origX] : 0;
        
        const worldX = (x / (lodWidth - 1)) * this.getTerrainWidth(data.bounds);
        const worldZ = (y / (lodHeight - 1)) * this.getTerrainHeight(data.bounds);
        const worldY = elevation * this.config.heightScale;

        vertices.push(worldX, worldY, worldZ);
        uvs.push(x / (lodWidth - 1), y / (lodHeight - 1));
      }
    }

    // Generate indices for LOD mesh
    for (let y = 0; y < lodHeight - 1; y++) {
      for (let x = 0; x < lodWidth - 1; x++) {
        const a = y * lodWidth + x;
        const b = y * lodWidth + x + 1;
        const c = (y + 1) * lodWidth + x;
        const d = (y + 1) * lodWidth + x + 1;

        indices.push(a, b, c);
        indices.push(b, d, c);
      }
    }

    // Calculate normals for LOD mesh
    this.calculateNormals(vertices, indices, normals);

    const lodGeometry = new THREE.BufferGeometry();
    lodGeometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    lodGeometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
    lodGeometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    lodGeometry.setIndex(indices);

    return lodGeometry;
  }

  /**
   * Classify surface types based on terrain analysis
   * Requirements: 1.5 - Surface type classification and material assignment for run-specific terrain
   */
  classifySurfaceTypes(data: TerrainData): SurfaceType[][] {
    const { width, height } = getGridDimensions(data.gridSize);
    const surfaceTypes: SurfaceType[][] = [];

    // Use hill metrics surface types if available, otherwise classify based on elevation and slope
    if (data.hillMetrics.surfaceTypes && data.hillMetrics.surfaceTypes.length > 0) {
      return data.hillMetrics.surfaceTypes;
    }

    // Fallback classification based on elevation and slope analysis
    for (let y = 0; y < height; y++) {
      surfaceTypes[y] = [];
      for (let x = 0; x < width; x++) {
        const elevation = data.elevationGrid[y] && data.elevationGrid[y][x] ? data.elevationGrid[y][x] : 0;
        const slope = this.calculateSlope(data.elevationGrid, x, y, width, height);
        
        // Classify based on elevation and slope
        let surfaceType: SurfaceType;
        
        if (slope > 35) {
          surfaceType = SurfaceType.ROCKS; // Very steep areas
        } else if (slope > 25) {
          surfaceType = SurfaceType.MOGULS; // Steep areas with bumps
        } else if (elevation > data.area.elevation.max * 0.8) {
          surfaceType = SurfaceType.POWDER; // High elevation areas
        } else if (slope < 5) {
          surfaceType = SurfaceType.PACKED; // Flat areas, likely groomed
        } else {
          surfaceType = SurfaceType.PACKED; // Default to packed snow
        }

        surfaceTypes[y][x] = surfaceType;
      }
    }

    return surfaceTypes;
  }

  /**
   * Create materials for different surface types
   * Requirements: 1.5 - Material assignment for run-specific terrain
   */
  createMaterials(surfaceTypes: SurfaceType[][]): THREE.Material[] {
    const uniqueSurfaceTypes = new Set<SurfaceType>();
    
    // Find all unique surface types in the terrain
    for (const row of surfaceTypes) {
      for (const surfaceType of row) {
        uniqueSurfaceTypes.add(surfaceType);
      }
    }

    const materials: THREE.Material[] = [];

    // Create materials for each surface type
    for (const surfaceType of uniqueSurfaceTypes) {
      const properties = SURFACE_PROPERTIES[surfaceType];
      
      const material = new THREE.MeshLambertMaterial({
        color: properties.color,
        transparent: false
      });

      // Add surface-specific properties
      if (material instanceof THREE.MeshStandardMaterial) {
        material.roughness = properties.roughness;
        material.metalness = properties.metallic;
      }

      materials.push(material);
    }

    // If no materials created, add a default material
    if (materials.length === 0) {
      materials.push(new THREE.MeshLambertMaterial({ color: '#ffffff' }));
    }

    return materials;
  }

  /**
   * Extract elevation data within run boundary
   */
  private extractElevationWithinBoundary(
    fullElevationData: number[][],
    boundary: GeographicCoordinate[],
    area: SkiArea,
    gridSize: GridSize
  ): number[][] {
    const { width, height } = getGridDimensions(gridSize);
    const elevationGrid: number[][] = [];

    // Validate inputs
    if (!boundary || boundary.length === 0) {
      throw new Error('Invalid boundary: boundary cannot be empty');
    }

    if (!fullElevationData || fullElevationData.length === 0) {
      // Create default elevation grid if no data provided
      for (let y = 0; y < height; y++) {
        elevationGrid[y] = [];
        for (let x = 0; x < width; x++) {
          elevationGrid[y][x] = area.elevation.min + Math.random() * (area.elevation.max - area.elevation.min);
        }
      }
      return elevationGrid;
    }

    // Calculate the bounding box of the run
    const runBounds = this.calculateTerrainBounds(boundary);

    for (let y = 0; y < height; y++) {
      elevationGrid[y] = [];
      for (let x = 0; x < width; x++) {
        // Convert grid coordinates to geographic coordinates
        const lat = runBounds.southWest.lat + 
          (y / (height - 1)) * (runBounds.northEast.lat - runBounds.southWest.lat);
        const lng = runBounds.southWest.lng + 
          (x / (width - 1)) * (runBounds.northEast.lng - runBounds.southWest.lng);

        // Check if point is within run boundary
        if (this.isPointInPolygon({ lat, lng }, boundary)) {
          // Map to full elevation data coordinates
          const fullDataX = Math.floor(
            ((lng - area.bounds.southWest.lng) / 
             (area.bounds.northEast.lng - area.bounds.southWest.lng)) * 
            (fullElevationData[0]?.length || width)
          );
          const fullDataY = Math.floor(
            ((lat - area.bounds.southWest.lat) / 
             (area.bounds.northEast.lat - area.bounds.southWest.lat)) * 
            (fullElevationData.length || height)
          );

          // Get elevation from full data or interpolate
          elevationGrid[y][x] = this.getElevationAt(fullElevationData, fullDataX, fullDataY);
        } else {
          // Point outside boundary, use interpolated edge value
          elevationGrid[y][x] = this.interpolateElevationAtBoundary(
            fullElevationData, { lat, lng }, boundary, area
          );
        }
      }
    }

    return elevationGrid;
  }

  /**
   * Extract surface types within run boundary
   */
  private extractSurfaceTypesWithinBoundary(
    fullSurfaceTypes: SurfaceType[][],
    boundary: GeographicCoordinate[],
    area: SkiArea,
    gridSize: GridSize
  ): SurfaceType[][] {
    const { width, height } = getGridDimensions(gridSize);
    const surfaceTypes: SurfaceType[][] = [];

    if (!fullSurfaceTypes || fullSurfaceTypes.length === 0) {
      // Return default surface types if none provided
      for (let y = 0; y < height; y++) {
        surfaceTypes[y] = [];
        for (let x = 0; x < width; x++) {
          surfaceTypes[y][x] = SurfaceType.PACKED;
        }
      }
      return surfaceTypes;
    }

    const runBounds = this.calculateTerrainBounds(boundary);

    for (let y = 0; y < height; y++) {
      surfaceTypes[y] = [];
      for (let x = 0; x < width; x++) {
        const lat = runBounds.southWest.lat + 
          (y / (height - 1)) * (runBounds.northEast.lat - runBounds.southWest.lat);
        const lng = runBounds.southWest.lng + 
          (x / (width - 1)) * (runBounds.northEast.lng - runBounds.southWest.lng);

        // Map to full surface type data coordinates
        const fullDataX = Math.floor(
          ((lng - area.bounds.southWest.lng) / 
           (area.bounds.northEast.lng - area.bounds.southWest.lng)) * 
          (fullSurfaceTypes[0]?.length || width)
        );
        const fullDataY = Math.floor(
          ((lat - area.bounds.southWest.lat) / 
           (area.bounds.northEast.lat - area.bounds.southWest.lat)) * 
          (fullSurfaceTypes.length || height)
        );

        // Get surface type from full data
        surfaceTypes[y][x] = this.getSurfaceTypeAt(fullSurfaceTypes, fullDataX, fullDataY);
      }
    }

    return surfaceTypes;
  }

  /**
   * Helper methods for terrain processing
   */
  private async getSkiAreaById(skiAreaId: string): Promise<SkiArea | null> {
    // This would typically fetch from a ski area service
    // For now, return a mock ski area
    return {
      id: skiAreaId,
      name: 'Mock Ski Area',
      location: 'Mock Location',
      country: 'Mock Country',
      bounds: {
        northEast: { lat: 46.0, lng: 7.0 },
        southWest: { lat: 45.0, lng: 6.0 }
      },
      elevation: { min: 1000, max: 3000 },
      previewImage: '',

      agentEndpoints: {
        hillMetrics: 'http://localhost:8001/jsonrpc',
        weather: 'http://localhost:8002/jsonrpc',
        equipment: 'http://localhost:8003/jsonrpc'
      },
      fisCompatible: true
    };
  }

  private calculateTerrainBounds(boundary: GeographicCoordinate[]) {
    if (!boundary || boundary.length === 0) {
      throw new Error('Cannot calculate bounds for empty boundary');
    }

    let minLat = boundary[0].lat;
    let maxLat = boundary[0].lat;
    let minLng = boundary[0].lng;
    let maxLng = boundary[0].lng;

    for (const coord of boundary) {
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

  private calculateResolution(bounds: any, gridSize: GridSize): number {
    const { width } = getGridDimensions(gridSize);
    const terrainWidth = this.getTerrainWidth(bounds);
    return terrainWidth / width;
  }

  private getTerrainWidth(bounds: any): number {
    // Approximate width in meters using Haversine formula
    const R = 6371000; // Earth's radius in meters
    const dLng = (bounds.northEast.lng - bounds.southWest.lng) * Math.PI / 180;
    const avgLat = ((bounds.northEast.lat + bounds.southWest.lat) / 2) * Math.PI / 180;
    return R * dLng * Math.cos(avgLat);
  }

  private getTerrainHeight(bounds: any): number {
    // Approximate height in meters
    const R = 6371000; // Earth's radius in meters
    const dLat = (bounds.northEast.lat - bounds.southWest.lat) * Math.PI / 180;
    return R * dLat;
  }

  private isPointInPolygon(point: GeographicCoordinate, polygon: GeographicCoordinate[]): boolean {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      if (((polygon[i].lat > point.lat) !== (polygon[j].lat > point.lat)) &&
          (point.lng < (polygon[j].lng - polygon[i].lng) * (point.lat - polygon[i].lat) / 
           (polygon[j].lat - polygon[i].lat) + polygon[i].lng)) {
        inside = !inside;
      }
    }
    return inside;
  }

  private getElevationAt(elevationData: number[][], x: number, y: number): number {
    if (!elevationData || elevationData.length === 0) return 0;
    
    const clampedY = Math.max(0, Math.min(elevationData.length - 1, y));
    const clampedX = Math.max(0, Math.min((elevationData[clampedY]?.length || 1) - 1, x));
    
    return elevationData[clampedY]?.[clampedX] || 0;
  }

  private getSurfaceTypeAt(surfaceTypes: SurfaceType[][], x: number, y: number): SurfaceType {
    if (!surfaceTypes || surfaceTypes.length === 0) return SurfaceType.PACKED;
    
    const clampedY = Math.max(0, Math.min(surfaceTypes.length - 1, y));
    const clampedX = Math.max(0, Math.min((surfaceTypes[clampedY]?.length || 1) - 1, x));
    
    return surfaceTypes[clampedY]?.[clampedX] || SurfaceType.PACKED;
  }

  private interpolateElevationAtBoundary(
    elevationData: number[][],
    point: GeographicCoordinate,
    boundary: GeographicCoordinate[],
    area: SkiArea
  ): number {
    // Simple interpolation - find nearest boundary point and use its elevation
    let minDistance = Infinity;
    let nearestElevation = 0;

    for (const boundaryPoint of boundary) {
      const distance = Math.sqrt(
        Math.pow(point.lat - boundaryPoint.lat, 2) + 
        Math.pow(point.lng - boundaryPoint.lng, 2)
      );
      
      if (distance < minDistance) {
        minDistance = distance;
        // Map boundary point to elevation data
        const x = Math.floor(
          ((boundaryPoint.lng - area.bounds.southWest.lng) / 
           (area.bounds.northEast.lng - area.bounds.southWest.lng)) * 
          (elevationData[0]?.length || 1)
        );
        const y = Math.floor(
          ((boundaryPoint.lat - area.bounds.southWest.lat) / 
           (area.bounds.northEast.lat - area.bounds.southWest.lat)) * 
          (elevationData.length || 1)
        );
        nearestElevation = this.getElevationAt(elevationData, x, y);
      }
    }

    return nearestElevation;
  }

  private calculateSlope(elevationGrid: number[][], x: number, y: number, width: number, height: number): number {
    const elevation = elevationGrid[y]?.[x] || 0;
    
    // Calculate slope using neighboring points
    const neighbors = [
      { dx: 1, dy: 0 }, { dx: -1, dy: 0 },
      { dx: 0, dy: 1 }, { dx: 0, dy: -1 }
    ];

    let maxSlope = 0;
    for (const neighbor of neighbors) {
      const nx = x + neighbor.dx;
      const ny = y + neighbor.dy;
      
      if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
        const neighborElevation = elevationGrid[ny]?.[nx] || 0;
        const elevationDiff = Math.abs(elevation - neighborElevation);
        const distance = Math.sqrt(neighbor.dx * neighbor.dx + neighbor.dy * neighbor.dy);
        const slope = Math.atan(elevationDiff / (distance * this.config.heightScale)) * (180 / Math.PI);
        maxSlope = Math.max(maxSlope, slope);
      }
    }

    return maxSlope;
  }

  private calculateNormals(vertices: number[], indices: number[], normals: number[]): void {
    // Initialize normals array
    for (let i = 0; i < vertices.length; i++) {
      normals[i] = 0;
    }

    // Calculate face normals and accumulate vertex normals
    for (let i = 0; i < indices.length; i += 3) {
      const a = indices[i] * 3;
      const b = indices[i + 1] * 3;
      const c = indices[i + 2] * 3;

      const v1 = new THREE.Vector3(vertices[a], vertices[a + 1], vertices[a + 2]);
      const v2 = new THREE.Vector3(vertices[b], vertices[b + 1], vertices[b + 2]);
      const v3 = new THREE.Vector3(vertices[c], vertices[c + 1], vertices[c + 2]);

      const edge1 = v2.clone().sub(v1);
      const edge2 = v3.clone().sub(v1);
      const normal = edge1.cross(edge2).normalize();

      // Accumulate normals for each vertex
      normals[a] += normal.x; normals[a + 1] += normal.y; normals[a + 2] += normal.z;
      normals[b] += normal.x; normals[b + 1] += normal.y; normals[b + 2] += normal.z;
      normals[c] += normal.x; normals[c + 1] += normal.y; normals[c + 2] += normal.z;
    }

    // Normalize accumulated normals
    for (let i = 0; i < normals.length; i += 3) {
      const normal = new THREE.Vector3(normals[i], normals[i + 1], normals[i + 2]).normalize();
      normals[i] = normal.x;
      normals[i + 1] = normal.y;
      normals[i + 2] = normal.z;
    }
  }

  private smoothVertices(vertices: number[], _indices: number[], width: number, height: number, iterations: number): void {
    for (let iter = 0; iter < iterations; iter++) {
      const smoothedVertices = [...vertices];

      for (let y = 1; y < height - 1; y++) {
        for (let x = 1; x < width - 1; x++) {
          const index = (y * width + x) * 3;
          
          // Average with neighboring vertices
          let avgY = 0;
          let count = 0;

          const neighbors = [
            { dx: -1, dy: -1 }, { dx: 0, dy: -1 }, { dx: 1, dy: -1 },
            { dx: -1, dy: 0 },                    { dx: 1, dy: 0 },
            { dx: -1, dy: 1 },  { dx: 0, dy: 1 },  { dx: 1, dy: 1 }
          ];

          for (const neighbor of neighbors) {
            const nx = x + neighbor.dx;
            const ny = y + neighbor.dy;
            
            if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
              const neighborIndex = (ny * width + nx) * 3;
              avgY += vertices[neighborIndex + 1]; // Y coordinate (elevation)
              count++;
            }
          }

          if (count > 0) {
            smoothedVertices[index + 1] = (vertices[index + 1] + avgY / count) / 2;
          }
        }
      }

      // Copy smoothed vertices back
      for (let i = 0; i < vertices.length; i++) {
        vertices[i] = smoothedVertices[i];
      }
    }
  }

  private flattenSurfaceTypes(surfaceTypes: SurfaceType[][]): SurfaceType[] {
    const flattened: SurfaceType[] = [];
    for (const row of surfaceTypes) {
      flattened.push(...row);
    }
    return flattened;
  }

  private generateCacheKey(data: TerrainData): string {
    return `${data.area.id}_${data.gridSize}_${data.bounds.northEast.lat}_${data.bounds.northEast.lng}_${data.bounds.southWest.lat}_${data.bounds.southWest.lng}`;
  }

  /**
   * Clear mesh cache
   */
  clearCache(): void {
    this.meshCache.clear();
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): { size: number; keys: string[] } {
    return {
      size: this.meshCache.size,
      keys: Array.from(this.meshCache.keys())
    };
  }
}

/**
 * Export singleton instance
 */
export const terrainService = new TerrainService();