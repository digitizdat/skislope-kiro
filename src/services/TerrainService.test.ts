/**
 * Unit tests for TerrainService
 * Requirements: 1.1, 1.2, 1.5, 7.5 - Test terrain data processing and mesh generation
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as THREE from 'three';
import { TerrainService } from './TerrainService';
import { GridSize, SurfaceType } from '../models/TerrainData';
import { SkiRun } from '../models/SkiRun';
import { agentClient } from './AgentClient';

// Mock the agent client
vi.mock('./AgentClient', () => ({
  agentClient: {
    callHillMetricsAgent: vi.fn()
  }
}));

describe('TerrainService', () => {
  let terrainService: TerrainService;
  let mockSkiRun: SkiRun;
  let mockHillMetricsResponse: any;

  beforeEach(() => {
    terrainService = new TerrainService();
    
    // Mock ski run data
    mockSkiRun = {
      id: 'test-run-1',
      name: 'Test Run',
      skiAreaId: 'chamonix',
      boundary: [
        { lat: 45.9, lng: 6.9 },
        { lat: 45.91, lng: 6.9 },
        { lat: 45.91, lng: 6.91 },
        { lat: 45.9, lng: 6.91 }
      ],
      metadata: {
        difficulty: 'intermediate',
        estimatedLength: 1000,
        verticalDrop: 200,
        averageSlope: 15,
        surfaceType: SurfaceType.PACKED,
        notes: 'Test run',
        tags: ['test']
      },
      statistics: {
        estimatedLength: 1000,
        verticalDrop: 200,
        averageSlope: 15,
        boundingBox: {
          northEast: { lat: 45.91, lng: 6.91 },
          southWest: { lat: 45.9, lng: 6.9 }
        },
        area: 100000
      },
      createdBy: 'test-user',
      createdAt: new Date(),
      lastModified: new Date(),
      isPublic: false
    };

    // Mock hill metrics response
    mockHillMetricsResponse = {
      data: {
        elevationData: [
          [1000, 1010, 1020, 1030],
          [1050, 1060, 1070, 1080],
          [1100, 1110, 1120, 1130],
          [1150, 1160, 1170, 1180]
        ],
        slopeAngles: [
          [10, 12, 14, 16],
          [15, 17, 19, 21],
          [20, 22, 24, 26],
          [25, 27, 29, 31]
        ],
        aspectAngles: [
          [0, 45, 90, 135],
          [180, 225, 270, 315],
          [0, 45, 90, 135],
          [180, 225, 270, 315]
        ],
        surfaceTypes: [
          [SurfaceType.PACKED, SurfaceType.PACKED, SurfaceType.POWDER, SurfaceType.POWDER],
          [SurfaceType.PACKED, SurfaceType.MOGULS, SurfaceType.POWDER, SurfaceType.ICE],
          [SurfaceType.MOGULS, SurfaceType.MOGULS, SurfaceType.ROCKS, SurfaceType.ICE],
          [SurfaceType.ROCKS, SurfaceType.ROCKS, SurfaceType.ROCKS, SurfaceType.TREES]
        ]
      },
      metadata: {
        processingTime: 1000,
        dataSource: 'test',
        lastUpdated: new Date(),
        gridResolution: GridSize.SMALL
      }
    };

    // Setup mock for agent client
    vi.mocked(agentClient.callHillMetricsAgent).mockResolvedValue(mockHillMetricsResponse);
  });

  describe('extractTerrainData', () => {
    it('should extract terrain data for a ski run', async () => {
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL);

      expect(terrainData).toBeDefined();
      expect(terrainData.gridSize).toBe(GridSize.SMALL);
      expect(terrainData.elevationGrid).toBeDefined();
      expect(terrainData.surfaceTypes).toBeDefined();
      expect(terrainData.bounds).toBeDefined();
      expect(terrainData.metadata.name).toBe('Test Run');
    });

    it('should handle different grid sizes', async () => {
      const gridSizes = [GridSize.SMALL, GridSize.MEDIUM, GridSize.LARGE, GridSize.EXTRA_LARGE];

      for (const gridSize of gridSizes) {
        const terrainData = await terrainService.extractTerrainData(mockSkiRun, gridSize);
        expect(terrainData.gridSize).toBe(gridSize);
      }
    });

    it('should throw error when agent call fails', async () => {
      vi.mocked(agentClient.callHillMetricsAgent).mockRejectedValue(new Error('Agent failed'));

      await expect(terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL))
        .rejects.toThrow('Terrain data extraction failed');
    });
  });

  describe('generateMesh', () => {
    it('should generate a valid Three.js mesh from terrain data', async () => {
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL);
      const terrainMesh = terrainService.generateMesh(terrainData);

      expect(terrainMesh).toBeDefined();
      expect(terrainMesh.geometry).toBeInstanceOf(THREE.BufferGeometry);
      expect(terrainMesh.materials).toBeDefined();
      expect(terrainMesh.materials.length).toBeGreaterThan(0);
      expect(terrainMesh.boundingBox).toBeInstanceOf(THREE.Box3);
      expect(terrainMesh.gridSize).toBe(GridSize.SMALL);
    });

    it('should generate geometry with correct attributes', async () => {
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL);
      const terrainMesh = terrainService.generateMesh(terrainData);

      const geometry = terrainMesh.geometry;
      expect(geometry.getAttribute('position')).toBeDefined();
      expect(geometry.getAttribute('normal')).toBeDefined();
      expect(geometry.getAttribute('uv')).toBeDefined();
      expect(geometry.getIndex()).toBeDefined();
    });

    it('should generate LOD levels when enabled', async () => {
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.LARGE);
      const terrainMesh = terrainService.generateMesh(terrainData);

      expect(terrainMesh.lodLevels).toBeDefined();
      expect(terrainMesh.lodLevels.length).toBeGreaterThan(0);
      
      for (const lodLevel of terrainMesh.lodLevels) {
        expect(lodLevel.distance).toBeGreaterThan(0);
        expect(lodLevel.vertexReduction).toBeGreaterThan(0);
        expect(lodLevel.vertexReduction).toBeLessThanOrEqual(1);
        expect(lodLevel.geometry).toBeInstanceOf(THREE.BufferGeometry);
      }
    });

    it('should cache generated meshes', async () => {
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL);
      
      // Generate mesh twice
      const mesh1 = terrainService.generateMesh(terrainData);
      const mesh2 = terrainService.generateMesh(terrainData);

      // Should return the same cached instance
      expect(mesh1).toBe(mesh2);
      
      const cacheStats = terrainService.getCacheStats();
      expect(cacheStats.size).toBe(1);
    });
  });

  describe('generateLODMesh', () => {
    it('should generate reduced resolution mesh for LOD', async () => {
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.LARGE);
      const lodGeometry = terrainService.generateLODMesh(terrainData, 1);

      expect(lodGeometry).toBeInstanceOf(THREE.BufferGeometry);
      expect(lodGeometry.getAttribute('position')).toBeDefined();
      expect(lodGeometry.getAttribute('normal')).toBeDefined();
      expect(lodGeometry.getAttribute('uv')).toBeDefined();

      // LOD mesh should have fewer vertices than original
      const originalMesh = terrainService.generateMesh(terrainData);
      const originalVertexCount = originalMesh.geometry.getAttribute('position').count;
      const lodVertexCount = lodGeometry.getAttribute('position').count;
      
      expect(lodVertexCount).toBeLessThanOrEqual(originalVertexCount);
    });

    it('should handle different LOD levels', async () => {
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.LARGE);
      
      const lod0 = terrainService.generateLODMesh(terrainData, 0);
      const lod1 = terrainService.generateLODMesh(terrainData, 1);
      const lod2 = terrainService.generateLODMesh(terrainData, 2);

      const lod0Count = lod0.getAttribute('position').count;
      const lod1Count = lod1.getAttribute('position').count;
      const lod2Count = lod2.getAttribute('position').count;

      // Higher LOD levels should have fewer vertices
      expect(lod1Count).toBeLessThanOrEqual(lod0Count);
      expect(lod2Count).toBeLessThanOrEqual(lod1Count);
    });
  });

  describe('classifySurfaceTypes', () => {
    it('should use hill metrics surface types when available', async () => {
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL);
      const surfaceTypes = terrainService.classifySurfaceTypes(terrainData);

      expect(surfaceTypes).toBeDefined();
      expect(surfaceTypes.length).toBeGreaterThan(0);
      expect(surfaceTypes[0].length).toBeGreaterThan(0);
      
      // Should contain various surface types from mock data
      const flatSurfaceTypes = surfaceTypes.flat();
      expect(flatSurfaceTypes).toContain(SurfaceType.PACKED);
      expect(flatSurfaceTypes).toContain(SurfaceType.POWDER);
      expect(flatSurfaceTypes).toContain(SurfaceType.MOGULS);
    });

    it('should fallback to slope-based classification when no surface types provided', async () => {
      // Mock response without surface types
      const responseWithoutSurfaceTypes = {
        ...mockHillMetricsResponse,
        data: {
          ...mockHillMetricsResponse.data,
          surfaceTypes: []
        }
      };
      
      vi.mocked(agentClient.callHillMetricsAgent).mockResolvedValue(responseWithoutSurfaceTypes);

      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL);
      const surfaceTypes = terrainService.classifySurfaceTypes(terrainData);

      expect(surfaceTypes).toBeDefined();
      expect(surfaceTypes.length).toBeGreaterThan(0);
      expect(surfaceTypes[0].length).toBeGreaterThan(0);
      
      // Should contain at least packed snow as default
      const flatSurfaceTypes = surfaceTypes.flat();
      expect(flatSurfaceTypes).toContain(SurfaceType.PACKED);
    });
  });

  describe('createMaterials', () => {
    it('should create materials for different surface types', async () => {
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL);
      const surfaceTypes = terrainService.classifySurfaceTypes(terrainData);
      const materials = terrainService.createMaterials(surfaceTypes);

      expect(materials).toBeDefined();
      expect(materials.length).toBeGreaterThan(0);
      
      for (const material of materials) {
        expect(material).toBeInstanceOf(THREE.Material);
      }
    });

    it('should create default material when no surface types provided', () => {
      const emptySurfaceTypes: SurfaceType[][] = [[]];
      const materials = terrainService.createMaterials(emptySurfaceTypes);

      expect(materials).toBeDefined();
      expect(materials.length).toBe(1);
      expect(materials[0]).toBeInstanceOf(THREE.Material);
    });
  });

  describe('cache management', () => {
    it('should clear cache when requested', async () => {
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL);
      terrainService.generateMesh(terrainData);

      let cacheStats = terrainService.getCacheStats();
      expect(cacheStats.size).toBe(1);

      terrainService.clearCache();

      cacheStats = terrainService.getCacheStats();
      expect(cacheStats.size).toBe(0);
    });

    it('should provide cache statistics', async () => {
      const terrainData1 = await terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL);
      const terrainData2 = await terrainService.extractTerrainData(mockSkiRun, GridSize.MEDIUM);
      
      terrainService.generateMesh(terrainData1);
      terrainService.generateMesh(terrainData2);

      const cacheStats = terrainService.getCacheStats();
      expect(cacheStats.size).toBe(2);
      expect(cacheStats.keys).toBeDefined();
      expect(cacheStats.keys.length).toBe(2);
    });
  });

  describe('error handling', () => {
    it('should handle invalid elevation data gracefully', async () => {
      const invalidResponse = {
        ...mockHillMetricsResponse,
        data: {
          ...mockHillMetricsResponse.data,
          elevationData: null
        }
      };
      
      vi.mocked(agentClient.callHillMetricsAgent).mockResolvedValue(invalidResponse);

      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL);
      const terrainMesh = terrainService.generateMesh(terrainData);

      expect(terrainMesh).toBeDefined();
      expect(terrainMesh.geometry).toBeInstanceOf(THREE.BufferGeometry);
    });

    it('should handle empty boundary gracefully', async () => {
      const runWithEmptyBoundary = {
        ...mockSkiRun,
        boundary: []
      };

      await expect(terrainService.extractTerrainData(runWithEmptyBoundary, GridSize.SMALL))
        .rejects.toThrow();
    });

    it('should handle network errors from agent', async () => {
      vi.mocked(agentClient.callHillMetricsAgent).mockRejectedValue(new Error('Network error'));

      await expect(terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL))
        .rejects.toThrow('Terrain data extraction failed');
    });
  });

  describe('performance considerations', () => {
    it('should handle large grid sizes efficiently', async () => {
      const startTime = Date.now();
      
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.EXTRA_LARGE);
      const terrainMesh = terrainService.generateMesh(terrainData);

      const endTime = Date.now();
      const processingTime = endTime - startTime;

      expect(terrainMesh).toBeDefined();
      expect(processingTime).toBeLessThan(5000); // Should complete within 5 seconds
    });

    it('should generate appropriate LOD levels for performance', async () => {
      const terrainData = await terrainService.extractTerrainData(mockSkiRun, GridSize.EXTRA_LARGE);
      const terrainMesh = terrainService.generateMesh(terrainData);

      expect(terrainMesh.lodLevels.length).toBeGreaterThan(0);
      
      // Verify LOD distances are increasing
      for (let i = 1; i < terrainMesh.lodLevels.length; i++) {
        expect(terrainMesh.lodLevels[i].distance).toBeGreaterThan(terrainMesh.lodLevels[i - 1].distance);
      }
    });
  });
});