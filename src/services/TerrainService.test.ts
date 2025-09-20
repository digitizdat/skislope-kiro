/**
 * Unit tests for TerrainService
 * Requirements: 1.1, 1.2, 1.5, 7.5 - Test terrain data processing and mesh generation
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as THREE from 'three';
import { TerrainService } from './TerrainService';
import { GridSize, SurfaceType } from '../models/TerrainData';
import { SkiRun } from '../models/SkiRun';
import { agentClient } from './AgentClient';
import { createMockCacheManager, MockCacheManager } from '../test/cacheManagerMocks';
import { AsyncTestUtils } from '../test/asyncTestUtils';

// Mock the agent client
vi.mock('./AgentClient', () => ({
  agentClient: {
    callHillMetricsAgent: vi.fn()
  }
}));

// Mock the CacheManager
vi.mock('../utils/CacheManager', () => {
  return {
    CacheManager: vi.fn(),
    cacheManager: {
      initialize: vi.fn().mockResolvedValue(undefined),
      getCachedTerrainData: vi.fn().mockResolvedValue(null),
      cacheTerrainData: vi.fn().mockResolvedValue(undefined),
      invalidateTerrainData: vi.fn().mockResolvedValue(undefined),
      cacheRunDefinition: vi.fn().mockResolvedValue(undefined),
      getCachedRunDefinition: vi.fn().mockResolvedValue(null),
      getCachedRunsByArea: vi.fn().mockResolvedValue([]),
      invalidateRunDefinition: vi.fn().mockResolvedValue(undefined),
      cacheAgentResponse: vi.fn().mockResolvedValue(undefined),
      getCachedAgentResponse: vi.fn().mockResolvedValue(null),
      invalidateAgentResponse: vi.fn().mockResolvedValue(undefined),
      isOfflineModeAvailable: vi.fn().mockResolvedValue(false),
      getOfflineData: vi.fn().mockResolvedValue(null),
      cleanup: vi.fn().mockResolvedValue(undefined),
      clearCache: vi.fn().mockResolvedValue(undefined),
      getCacheStats: vi.fn().mockResolvedValue({
        totalSize: 0,
        entryCount: 0,
        hitRate: 0,
        lastCleanup: Date.now()
      }),
      close: vi.fn().mockResolvedValue(undefined)
    }
  };
});

describe('TerrainService', () => {
  let terrainService: TerrainService;
  let mockSkiRun: SkiRun;
  let mockHillMetricsResponse: any;
  let mockCacheManager: any;

  beforeEach(async () => {
    // Clear all mocks
    vi.clearAllMocks();
    
    // Get the mock cache manager instance
    const { cacheManager } = await import('../utils/CacheManager');
    mockCacheManager = cacheManager;
    
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

  afterEach(() => {
    // Clear all mocks
    vi.clearAllMocks();
  });

  describe('extractTerrainData', () => {
    it('should extract terrain data for a ski run', async () => {
      // Mock cache miss scenario
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);

      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
        5000
      );

      expect(terrainData).toBeDefined();
      expect(terrainData.gridSize).toBe(GridSize.SMALL);
      expect(terrainData.elevationGrid).toBeDefined();
      expect(terrainData.surfaceTypes).toBeDefined();
      expect(terrainData.bounds).toBeDefined();
      expect(terrainData.metadata.name).toBe('Test Run');
      
      // Verify cache operations were called
      expect(mockCacheManager.getCachedTerrainData).toHaveBeenCalledWith(mockSkiRun.id, GridSize.SMALL);
      expect(mockCacheManager.cacheTerrainData).toHaveBeenCalled();
    });

    it('should handle different grid sizes', async () => {
      const gridSizes = [GridSize.SMALL, GridSize.MEDIUM, GridSize.LARGE, GridSize.EXTRA_LARGE];

      for (const gridSize of gridSizes) {
        // Mock cache miss for each grid size
        mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
        
        const terrainData = await AsyncTestUtils.withTimeout(
          terrainService.extractTerrainData(mockSkiRun, gridSize),
          5000
        );
        expect(terrainData.gridSize).toBe(gridSize);
      }
    });

    it('should throw error when agent call fails', async () => {
      // Mock cache miss so agent is called
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      vi.mocked(agentClient.callHillMetricsAgent).mockRejectedValue(new Error('Agent failed'));

      await expect(
        AsyncTestUtils.withTimeout(
          terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
          5000
        )
      ).rejects.toThrow('Terrain data extraction failed');
    });

    it('should use cached terrain data when available', async () => {
      // Create mock terrain data for cache hit
      const cachedTerrainData = {
        elevationGrid: [[100, 110], [105, 115]],
        resolution: 32,
        bounds: {
          northEast: { lat: 45.9, lng: 6.9 },
          southWest: { lat: 45.8, lng: 6.8 }
        },
        metadata: {
          name: 'Cached Test Run',
          difficulty: 'intermediate' as const,
          estimatedLength: 1000,
          verticalDrop: 200,
          averageSlope: 15
        },
        surfaceTypes: [[SurfaceType.PACKED, SurfaceType.PACKED], [SurfaceType.POWDER, SurfaceType.POWDER]],
        gridSize: GridSize.SMALL,
        area: {
          id: 'chamonix',
          name: 'Chamonix',
          location: 'Chamonix-Mont-Blanc',
          country: 'France',
          bounds: {
            northEast: { lat: 46.0, lng: 7.0 },
            southWest: { lat: 45.7, lng: 6.7 }
          },
          elevation: { min: 1000, max: 4000 },
          previewImage: 'chamonix.jpg',
          agentEndpoints: {
            hillMetrics: 'http://localhost:8001',
            weather: 'http://localhost:8002',
            equipment: 'http://localhost:8003'
          },
          fisCompatible: true
        },
        hillMetrics: mockHillMetricsResponse.data
      };

      // Mock cache hit
      mockCacheManager.getCachedTerrainData.mockResolvedValue(cachedTerrainData);

      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
        5000
      );

      expect(terrainData).toEqual(cachedTerrainData);
      expect(terrainData.metadata.name).toBe('Cached Test Run');
      
      // Verify cache was checked but agent was not called
      expect(mockCacheManager.getCachedTerrainData).toHaveBeenCalledWith(mockSkiRun.id, GridSize.SMALL);
      expect(agentClient.callHillMetricsAgent).not.toHaveBeenCalled();
    });
  });

  describe('generateMesh', () => {
    it('should generate a valid Three.js mesh from terrain data', async () => {
      // Mock cache miss for fresh data
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
        5000
      );
      
      const terrainMesh = terrainService.generateMesh(terrainData);

      expect(terrainMesh).toBeDefined();
      expect(terrainMesh.geometry).toBeInstanceOf(THREE.BufferGeometry);
      expect(terrainMesh.materials).toBeDefined();
      expect(terrainMesh.materials.length).toBeGreaterThan(0);
      expect(terrainMesh.boundingBox).toBeInstanceOf(THREE.Box3);
      expect(terrainMesh.gridSize).toBe(GridSize.SMALL);
    });

    it('should generate geometry with correct attributes', async () => {
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
        5000
      );
      
      const terrainMesh = terrainService.generateMesh(terrainData);

      const geometry = terrainMesh.geometry;
      expect(geometry.getAttribute('position')).toBeDefined();
      expect(geometry.getAttribute('normal')).toBeDefined();
      expect(geometry.getAttribute('uv')).toBeDefined();
      expect(geometry.getIndex()).toBeDefined();
    });

    it('should generate LOD levels when enabled', async () => {
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.LARGE),
        5000
      );
      
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
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
        5000
      );
      
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
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.LARGE),
        5000
      );
      
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
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.LARGE),
        5000
      );
      
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
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
        5000
      );
      
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
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      // Mock response without surface types
      const responseWithoutSurfaceTypes = {
        ...mockHillMetricsResponse,
        data: {
          ...mockHillMetricsResponse.data,
          surfaceTypes: []
        }
      };
      
      vi.mocked(agentClient.callHillMetricsAgent).mockResolvedValue(responseWithoutSurfaceTypes);

      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
        5000
      );
      
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
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
        5000
      );
      
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
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
        5000
      );
      
      terrainService.generateMesh(terrainData);

      let cacheStats = terrainService.getCacheStats();
      expect(cacheStats.size).toBe(1);

      terrainService.clearCache();

      cacheStats = terrainService.getCacheStats();
      expect(cacheStats.size).toBe(0);
    });

    it('should provide cache statistics', async () => {
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const terrainData1 = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
        5000
      );
      const terrainData2 = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.MEDIUM),
        5000
      );
      
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
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const invalidResponse = {
        ...mockHillMetricsResponse,
        data: {
          ...mockHillMetricsResponse.data,
          elevationData: null
        }
      };
      
      vi.mocked(agentClient.callHillMetricsAgent).mockResolvedValue(invalidResponse);

      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
        5000
      );
      
      const terrainMesh = terrainService.generateMesh(terrainData);

      expect(terrainMesh).toBeDefined();
      expect(terrainMesh.geometry).toBeInstanceOf(THREE.BufferGeometry);
    });

    it('should handle empty boundary gracefully', async () => {
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const runWithEmptyBoundary = {
        ...mockSkiRun,
        id: 'empty-boundary-run',
        boundary: []
      };

      await expect(
        AsyncTestUtils.withTimeout(
          terrainService.extractTerrainData(runWithEmptyBoundary, GridSize.SMALL),
          5000
        )
      ).rejects.toThrow();
    });

    it('should handle network errors from agent', async () => {
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      vi.mocked(agentClient.callHillMetricsAgent).mockRejectedValue(new Error('Network error'));

      await expect(
        AsyncTestUtils.withTimeout(
          terrainService.extractTerrainData(mockSkiRun, GridSize.SMALL),
          5000
        )
      ).rejects.toThrow('Terrain data extraction failed');
    });
  });

  describe('performance considerations', () => {
    it('should handle large grid sizes efficiently', async () => {
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const startTime = Date.now();
      
      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.EXTRA_LARGE),
        10000 // Longer timeout for large grid
      );
      
      const terrainMesh = terrainService.generateMesh(terrainData);

      const endTime = Date.now();
      const processingTime = endTime - startTime;

      expect(terrainMesh).toBeDefined();
      expect(processingTime).toBeLessThan(10000); // Should complete within 10 seconds for large grid
    });

    it('should generate appropriate LOD levels for performance', async () => {
      mockCacheManager.getCachedTerrainData.mockResolvedValue(null);
      
      const terrainData = await AsyncTestUtils.withTimeout(
        terrainService.extractTerrainData(mockSkiRun, GridSize.EXTRA_LARGE),
        10000
      );
      
      const terrainMesh = terrainService.generateMesh(terrainData);

      expect(terrainMesh.lodLevels.length).toBeGreaterThan(0);
      
      // Verify LOD distances are increasing
      for (let i = 1; i < terrainMesh.lodLevels.length; i++) {
        expect(terrainMesh.lodLevels[i].distance).toBeGreaterThan(terrainMesh.lodLevels[i - 1].distance);
      }
    });
  });
});