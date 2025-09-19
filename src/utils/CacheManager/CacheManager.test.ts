import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { CacheManager } from './CacheManager';
import { TerrainData, GridSize } from '../../models/TerrainData';
import { SkiRun } from '../../models/SkiRun';
import { HillMetrics, WeatherData, EquipmentData } from '../../models/TerrainData';

// Mock IndexedDB
const mockIDBDatabase = {
  transaction: vi.fn(),
  close: vi.fn(),
  onerror: null,
  objectStoreNames: {
    contains: vi.fn(() => false)
  },
  createObjectStore: vi.fn(() => ({
    createIndex: vi.fn()
  }))
};

const mockIDBRequest = {
  result: mockIDBDatabase,
  error: null,
  onsuccess: null as ((event: Event) => void) | null,
  onerror: null as ((event: Event) => void) | null,
  onupgradeneeded: null as ((event: IDBVersionChangeEvent) => void) | null
};

const mockIDBTransaction = {
  objectStore: vi.fn(() => mockIDBObjectStore)
};

const mockIDBObjectStore = {
  put: vi.fn(() => ({ onsuccess: null, onerror: null })),
  get: vi.fn(() => ({ onsuccess: null, onerror: null })),
  delete: vi.fn(() => ({ onsuccess: null, onerror: null })),
  clear: vi.fn(() => ({ onsuccess: null, onerror: null })),
  getAll: vi.fn(() => ({ onsuccess: null, onerror: null })),
  index: vi.fn(() => ({
    getAll: vi.fn(() => ({ onsuccess: null, onerror: null }))
  }))
};

// Mock global IndexedDB
Object.defineProperty(global, 'indexedDB', {
  value: {
    open: vi.fn(() => mockIDBRequest)
  },
  writable: true
});

describe('CacheManager', () => {
  let cacheManager: CacheManager;
  let mockTerrainData: TerrainData;
  let mockSkiRun: SkiRun;
  let mockHillMetrics: HillMetrics;

  beforeEach(() => {
    vi.clearAllMocks();
    
    cacheManager = new CacheManager({
      terrainCacheDuration: 1000,
      agentCacheDuration: 500,
      runCacheDuration: 2000,
      maxCacheSize: 100,
      version: '1.0.0'
    });

    mockTerrainData = {
      elevationGrid: [[100, 110], [105, 115]],
      resolution: 32,
      bounds: {
        northEast: { lat: 45.9, lng: 6.9 },
        southWest: { lat: 45.8, lng: 6.8 }
      },
      metadata: {
        name: 'Test Run',
        difficulty: 'intermediate',
        estimatedLength: 1000,
        verticalDrop: 200,
        averageSlope: 15
      },
      surfaceTypes: [['powder', 'powder'], ['packed', 'packed']],
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
        satelliteImageUrl: 'chamonix-satellite.jpg',
        agentEndpoints: {
          hillMetrics: 'http://localhost:8001',
          weather: 'http://localhost:8002',
          equipment: 'http://localhost:8003'
        },
        fisCompatible: true
      },
      hillMetrics: {
        elevationData: [[100, 110], [105, 115]],
        slopeAngles: [[10, 15], [12, 18]],
        aspectAngles: [[180, 190], [185, 195]],
        surfaceTypes: [['powder', 'powder'], ['packed', 'packed']]
      }
    };

    mockSkiRun = {
      id: 'test-run-1',
      name: 'Test Run',
      skiAreaId: 'chamonix',
      boundary: [
        { lat: 45.85, lng: 6.85 },
        { lat: 45.86, lng: 6.86 },
        { lat: 45.87, lng: 6.87 }
      ],
      metadata: {
        difficulty: 'intermediate',
        estimatedLength: 1000,
        verticalDrop: 200,
        averageSlope: 15,
        surfaceType: 'powder',
        tags: ['scenic', 'beginner-friendly']
      },
      createdBy: 'user-1',
      createdAt: new Date(),
      lastModified: new Date(),
      isPublic: true
    };

    mockHillMetrics = {
      elevationData: [[100, 110], [105, 115]],
      slopeAngles: [[10, 15], [12, 18]],
      aspectAngles: [[180, 190], [185, 195]],
      surfaceTypes: [['powder', 'powder'], ['packed', 'packed']]
    };

    // Setup mock transaction
    mockIDBDatabase.transaction.mockReturnValue(mockIDBTransaction);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initialization', () => {
    it('should initialize with default config', () => {
      const defaultCacheManager = new CacheManager();
      expect(defaultCacheManager).toBeDefined();
    });

    it('should initialize with custom config', () => {
      const customConfig = {
        terrainCacheDuration: 5000,
        agentCacheDuration: 1000
      };
      const customCacheManager = new CacheManager(customConfig);
      expect(customCacheManager).toBeDefined();
    });

    it('should initialize IndexedDB connection', async () => {
      // Simulate successful DB opening
      setTimeout(() => {
        if (mockIDBRequest.onsuccess) {
          mockIDBRequest.onsuccess(new Event('success'));
        }
      }, 0);

      await expect(cacheManager.initialize()).resolves.toBeUndefined();
      expect(global.indexedDB.open).toHaveBeenCalledWith('alpine-ski-cache', 1);
    });
  });

  describe('terrain data caching', () => {
    beforeEach(async () => {
      // Mock successful initialization
      setTimeout(() => {
        if (mockIDBRequest.onsuccess) {
          mockIDBRequest.onsuccess(new Event('success'));
        }
      }, 0);
      await cacheManager.initialize();
    });

    it('should cache terrain data successfully', async () => {
      const mockPutRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.put.mockReturnValue(mockPutRequest);

      const cachePromise = cacheManager.cacheTerrainData(
        mockTerrainData,
        mockSkiRun,
        GridSize.SMALL
      );

      // Simulate successful put operation
      setTimeout(() => {
        if (mockPutRequest.onsuccess) {
          mockPutRequest.onsuccess(new Event('success'));
        }
      }, 0);

      await expect(cachePromise).resolves.toBeUndefined();
      expect(mockIDBObjectStore.put).toHaveBeenCalled();
    });

    it('should retrieve cached terrain data', async () => {
      const mockGetRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.get.mockReturnValue(mockGetRequest);

      const retrievePromise = cacheManager.getCachedTerrainData('test-run-1', GridSize.SMALL);

      // Simulate successful get operation with valid data
      setTimeout(() => {
        mockGetRequest.result = {
          data: mockTerrainData,
          timestamp: Date.now(),
          expiresAt: Date.now() + 10000, // Not expired
          version: '1.0.0',
          key: 'terrain:test-run-1:32x32'
        };
        if (mockGetRequest.onsuccess) {
          mockGetRequest.onsuccess(new Event('success'));
        }
      }, 0);

      const result = await retrievePromise;
      expect(result).toEqual(mockTerrainData);
      expect(mockIDBObjectStore.get).toHaveBeenCalledWith('terrain:test-run-1:32x32');
    });

    it('should return null for expired terrain data', async () => {
      const mockGetRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.get.mockReturnValue(mockGetRequest);

      const mockDeleteRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.delete.mockReturnValue(mockDeleteRequest);

      const retrievePromise = cacheManager.getCachedTerrainData('test-run-1', GridSize.SMALL);

      // Simulate successful get operation with expired data
      setTimeout(() => {
        mockGetRequest.result = {
          data: mockTerrainData,
          timestamp: Date.now() - 10000,
          expiresAt: Date.now() - 5000, // Expired
          version: '1.0.0',
          key: 'terrain:test-run-1:32x32'
        };
        if (mockGetRequest.onsuccess) {
          mockGetRequest.onsuccess(new Event('success'));
        }
      }, 0);

      // Simulate successful delete operation
      setTimeout(() => {
        if (mockDeleteRequest.onsuccess) {
          mockDeleteRequest.onsuccess(new Event('success'));
        }
      }, 10);

      const result = await retrievePromise;
      expect(result).toBeNull();
      expect(mockIDBObjectStore.delete).toHaveBeenCalled();
    });
  });

  describe('run definition caching', () => {
    beforeEach(async () => {
      setTimeout(() => {
        if (mockIDBRequest.onsuccess) {
          mockIDBRequest.onsuccess(new Event('success'));
        }
      }, 0);
      await cacheManager.initialize();
    });

    it('should cache run definition successfully', async () => {
      const mockPutRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.put.mockReturnValue(mockPutRequest);

      const cachePromise = cacheManager.cacheRunDefinition(mockSkiRun);

      setTimeout(() => {
        if (mockPutRequest.onsuccess) {
          mockPutRequest.onsuccess(new Event('success'));
        }
      }, 0);

      await expect(cachePromise).resolves.toBeUndefined();
      expect(mockIDBObjectStore.put).toHaveBeenCalled();
    });

    it('should retrieve cached run definition', async () => {
      const mockGetRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.get.mockReturnValue(mockGetRequest);

      const retrievePromise = cacheManager.getCachedRunDefinition('test-run-1');

      setTimeout(() => {
        mockGetRequest.result = {
          data: mockSkiRun,
          timestamp: Date.now(),
          expiresAt: Date.now() + 10000,
          version: '1.0.0',
          key: 'run:test-run-1'
        };
        if (mockGetRequest.onsuccess) {
          mockGetRequest.onsuccess(new Event('success'));
        }
      }, 0);

      const result = await retrievePromise;
      expect(result).toEqual(mockSkiRun);
    });
  });

  describe('agent response caching', () => {
    beforeEach(async () => {
      setTimeout(() => {
        if (mockIDBRequest.onsuccess) {
          mockIDBRequest.onsuccess(new Event('success'));
        }
      }, 0);
      await cacheManager.initialize();
    });

    it('should cache agent response successfully', async () => {
      const mockPutRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.put.mockReturnValue(mockPutRequest);

      const cachePromise = cacheManager.cacheAgentResponse(
        'hill-metrics',
        'chamonix',
        mockHillMetrics
      );

      setTimeout(() => {
        if (mockPutRequest.onsuccess) {
          mockPutRequest.onsuccess(new Event('success'));
        }
      }, 0);

      await expect(cachePromise).resolves.toBeUndefined();
      expect(mockIDBObjectStore.put).toHaveBeenCalled();
    });

    it('should retrieve cached agent response', async () => {
      const mockGetRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.get.mockReturnValue(mockGetRequest);

      const retrievePromise = cacheManager.getCachedAgentResponse<HillMetrics>(
        'hill-metrics',
        'chamonix'
      );

      setTimeout(() => {
        mockGetRequest.result = {
          data: mockHillMetrics,
          timestamp: Date.now(),
          expiresAt: Date.now() + 10000,
          version: '1.0.0',
          key: 'agent:hill-metrics:chamonix'
        };
        if (mockGetRequest.onsuccess) {
          mockGetRequest.onsuccess(new Event('success'));
        }
      }, 0);

      const result = await retrievePromise;
      expect(result).toEqual(mockHillMetrics);
    });
  });

  describe('offline mode support', () => {
    beforeEach(async () => {
      setTimeout(() => {
        if (mockIDBRequest.onsuccess) {
          mockIDBRequest.onsuccess(new Event('success'));
        }
      }, 0);
      await cacheManager.initialize();
    });

    it('should check offline mode availability', async () => {
      // Mock terrain data exists
      const mockTerrainGetRequest = { onsuccess: null, onerror: null };
      const mockRunGetRequest = { onsuccess: null, onerror: null };
      
      mockIDBObjectStore.get
        .mockReturnValueOnce(mockTerrainGetRequest)
        .mockReturnValueOnce(mockRunGetRequest);

      const availabilityPromise = cacheManager.isOfflineModeAvailable('test-run-1', GridSize.SMALL);

      // Simulate successful gets
      setTimeout(() => {
        mockTerrainGetRequest.result = {
          data: mockTerrainData,
          timestamp: Date.now(),
          expiresAt: Date.now() + 10000,
          version: '1.0.0',
          key: 'terrain:test-run-1:32x32'
        };
        if (mockTerrainGetRequest.onsuccess) {
          mockTerrainGetRequest.onsuccess(new Event('success'));
        }
      }, 0);

      setTimeout(() => {
        mockRunGetRequest.result = {
          data: mockSkiRun,
          timestamp: Date.now(),
          expiresAt: Date.now() + 10000,
          version: '1.0.0',
          key: 'run:test-run-1'
        };
        if (mockRunGetRequest.onsuccess) {
          mockRunGetRequest.onsuccess(new Event('success'));
        }
      }, 10);

      const result = await availabilityPromise;
      expect(result).toBe(true);
    });

    it('should return offline data when available', async () => {
      const mockTerrainGetRequest = { onsuccess: null, onerror: null };
      const mockRunGetRequest = { onsuccess: null, onerror: null };
      const mockAgentGetRequest = { onsuccess: null, onerror: null };
      
      mockIDBObjectStore.get
        .mockReturnValueOnce(mockTerrainGetRequest)
        .mockReturnValueOnce(mockRunGetRequest)
        .mockReturnValueOnce(mockAgentGetRequest)
        .mockReturnValueOnce(mockAgentGetRequest)
        .mockReturnValueOnce(mockAgentGetRequest);

      const offlineDataPromise = cacheManager.getOfflineData('test-run-1', GridSize.SMALL);

      // Simulate successful gets
      setTimeout(() => {
        mockTerrainGetRequest.result = {
          data: mockTerrainData,
          timestamp: Date.now(),
          expiresAt: Date.now() + 10000,
          version: '1.0.0',
          key: 'terrain:test-run-1:32x32'
        };
        if (mockTerrainGetRequest.onsuccess) {
          mockTerrainGetRequest.onsuccess(new Event('success'));
        }
      }, 0);

      setTimeout(() => {
        mockRunGetRequest.result = {
          data: mockSkiRun,
          timestamp: Date.now(),
          expiresAt: Date.now() + 10000,
          version: '1.0.0',
          key: 'run:test-run-1'
        };
        if (mockRunGetRequest.onsuccess) {
          mockRunGetRequest.onsuccess(new Event('success'));
        }
      }, 10);

      setTimeout(() => {
        mockAgentGetRequest.result = null; // No cached agent data
        if (mockAgentGetRequest.onsuccess) {
          mockAgentGetRequest.onsuccess(new Event('success'));
        }
      }, 20);

      const result = await offlineDataPromise;
      expect(result).toEqual({
        terrain: mockTerrainData,
        run: mockSkiRun,
        agents: {
          hillMetrics: undefined,
          weather: undefined,
          equipment: undefined
        }
      });
    });
  });

  describe('cache cleanup', () => {
    beforeEach(async () => {
      setTimeout(() => {
        if (mockIDBRequest.onsuccess) {
          mockIDBRequest.onsuccess(new Event('success'));
        }
      }, 0);
      await cacheManager.initialize();
    });

    it('should clear entire cache', async () => {
      const mockClearRequest = { onsuccess: null, onerror: null };
      mockIDBObjectStore.clear.mockReturnValue(mockClearRequest);

      const clearPromise = cacheManager.clearCache();

      setTimeout(() => {
        if (mockClearRequest.onsuccess) {
          mockClearRequest.onsuccess(new Event('success'));
        }
      }, 0);

      await expect(clearPromise).resolves.toBeUndefined();
      expect(mockIDBObjectStore.clear).toHaveBeenCalledTimes(3); // terrain, runs, agents
    });
  });
});